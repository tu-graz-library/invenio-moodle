# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for inserting moodle-data into invenio-style database."""

from __future__ import annotations

import copy
import hashlib
import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

import requests
from flask import current_app
from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_lom.proxies import current_records_lom
from invenio_records_lom.utils import LOMMetadata
from invenio_records_resources.services.uow import UnitOfWork
from sqlalchemy.orm.exc import NoResultFound

from .schemas import MoodleSchema


@dataclass(frozen=True)
class FileCacheInfo:
    """Holds a file-path and the file's md5-hash."""

    hash_md5: str
    path: Path


@dataclass(frozen=True)
class Key(ABC):
    """Common ancestor to all Key classes."""

    @property
    @abstractmethod
    def resource_type(self) -> str:
        """The resource_type associated to the key, one of `LOM_RESOURCE_TYPES`."""

    @abstractmethod
    def to_string_key(self) -> str:
        """Convert `self` to unique string representation."""


@dataclass(frozen=True)
class FileKey(Key):
    """Key for files as to disambiguate it from keys for units and courses."""

    url: str
    year: str
    semester: str
    hash_md5: str

    resource_type = "file"

    @classmethod
    def from_json_and_cache(
        cls,
        moodle_file_json: str,
        file_cache: dict[str, FileCacheInfo],
    ):
        """Create `cls` via info from moodle-json and file-cache."""
        url = moodle_file_json["fileurl"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        hash_md5 = file_cache[url].hash_md5
        return cls(url=url, year=year, semester=semester, hash_md5=hash_md5)

    def to_string_key(self):
        """Get string-representation."""
        return f"FileKey(url={self.url}, year={self.year}, semester={self.semester}, hash_md5={self.hash_md5})"


@dataclass(frozen=True)
class UnitKey(Key):
    """Key for units as to disambiguate it from keys for files and courses."""

    courseid: str
    year: str
    semester: str

    resource_type = "unit"

    @classmethod
    def from_json(cls, moodle_file_json, moodle_course_json):
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_json["courseid"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        return cls(courseid=courseid, year=year, semester=semester)

    def to_string_key(self):
        """Get string-representation."""
        return f"UnitKey(courseid={self.courseid}, year={self.year}, semester={self.semester})"


@dataclass(frozen=True)
class CourseKey(Key):
    """Key for courses as to disambiguate it from keys for files and units."""

    courseid: str

    resource_type = "course"

    @classmethod
    def from_json(cls, moodle_course_json):
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_json["courseid"]
        return cls(courseid=courseid)

    def to_string_key(self):
        """Get string-representation."""
        return f"CourseKey(courseid={self.courseid})"


@dataclass
class TaskLog:
    """Stores data."""

    pid: str
    previous_json: dict
    json: dict
    moodle_file_json: dict = None
    moodle_course_json: dict = None


@dataclass(frozen=True)
class Link:
    """Represents a link between records."""

    key: Key
    kind: str
    value: str


# pylint: disable-next=too-many-locals
def cache_files(
    directory: Path,
    provided_filepaths_by_url: dict[str, Path],
    urls: list[str],
) -> dict[str, FileCacheInfo]:
    """Creates a file-cache, downloading unprovided files into `directory` and hashing all files.

    :param Path directory: The directory to download unprovided files into.
    :param dict[str, Path] provided_filepaths_by_url: A dictionary that maps some urls to filepaths.
        When a url is in `provided_filepaths_by_url`,
        the file on the corresponding filepath is cached.
        Otherwise the file is downloaded from file-url.
    :param list[str] urls: The URLs of the to-be-cached files.
    """
    file_cache: dict[str, FileCacheInfo] = {}  # to be result
    directory = Path(directory)

    # add provided file-infos to `file_cache`
    for url, path in provided_filepaths_by_url.items():
        hash_ = hashlib.md5()
        path = Path(path)
        with path.open(mode="rb", buffering=1024 * 1024) as file:
            for chunk in file:
                hash_.update(chunk)
        file_cache[url] = FileCacheInfo(hash_md5=hash_.hexdigest(), path=path)

    # get other file-infos from internet
    with requests.Session() as session:
        for idx, url in enumerate(urls):
            if url not in provided_filepaths_by_url:
                with session.get(url, stream=True) as response:
                    response.raise_for_status()

                    # find filename in headers
                    dispos = response.headers.get("content-disposition", "")
                    # all html-headers are encoded in latin1, but python interprets as utf-8
                    dispos = dispos.encode("latin1").decode("utf-8")
                    if match := re.search('filename="([^"]*)"', dispos):
                        filename = match.group(1)
                    else:
                        raise ValueError(f"couldn't find filename in header {dispos}")

                    # save file to `directory`, compute its hash along the way
                    # filepath is of form 'directory/0/file.pdf'
                    filepath = directory.joinpath(str(idx), filename)
                    filepath.parent.mkdir()  # create 'directory/0/'
                    hash_ = hashlib.md5()
                    with filepath.open(mode="wb", buffering=1024 * 1024) as file:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            hash_.update(chunk)
                            file.write(chunk)
                file_cache[url] = FileCacheInfo(
                    hash_md5=hash_.hexdigest(),
                    path=filepath,
                )

    # return
    return file_cache


def fetch_else_create(key: Key) -> TaskLog:
    """Fetch moodle-result corresponding to `key`, create database-entry if none exists.

    :param Key key: the key which to attempt fetching from pidstore
    """
    service = current_records_lom.records_service
    create = partial(service.create, identity=system_identity)
    read = partial(service.read, identity=system_identity)

    database_key = key.to_string_key()
    try:
        moodle_pid = PersistentIdentifier.get(pid_type="moodle", pid_value=database_key)
    except PIDDoesNotExistError:
        # create draft with empty metadata
        pids_dict = {"moodle": {"provider": "moodle", "identifier": database_key}}
        metadata = LOMMetadata.create(resource_type=key.resource_type, pids=pids_dict)
        metadata.append_identifier(database_key, catalog="moodle")
        draft_item = create(data=metadata.json)

        pid: str = draft_item.id
        previous_json = None
        json_ = draft_item.to_dict()
    else:
        # get lomid corresponding to moodle_pid
        lomid_pid = PersistentIdentifier.get_by_object(
            pid_type="lomid",
            object_type=moodle_pid.object_type,
            object_uuid=moodle_pid.object_uuid,
        )

        pid: str = lomid_pid.pid_value
        previous_json = read(id_=pid).to_dict()
        json_ = copy.deepcopy(previous_json)

    return TaskLog(pid=pid, previous_json=previous_json, json=json_)


def prepare_tasks(
    moodle_data: dict,
    file_cache: dict[str, FileCacheInfo],
) -> dict[Key, TaskLog]:
    """Prepare database-drafts, initialize one `TaskLog` per draft.

    :param dict moodle_data: Data whose format matches `MoodleSchema`
    :param dict[str, FileCacheInfo] file_cache: file-cache,
        contains one file per "fileurl" within `moodle_data`
    """
    task_logs = {}  # to be result
    moodle_file_jsons = (
        file_json
        for moodlecourse in moodle_data["moodlecourses"]
        for file_json in moodlecourse["files"]
    )

    # prepare: gather necessary information, create records if no previous versions exist
    for moodle_file_json in moodle_file_jsons:
        file_key = FileKey.from_json_and_cache(moodle_file_json, file_cache)
        file_item = fetch_else_create(file_key)
        file_item.moodle_file_json = moodle_file_json
        task_logs[file_key] = file_item
        for moodle_course_json in moodle_file_json["courses"]:
            if moodle_course_json["courseid"] == "0":
                # courseid '0' signifies moodle-only-courses, don't prepare those
                continue

            unit_key = UnitKey.from_json(moodle_file_json, moodle_course_json)
            if unit_key not in task_logs:
                unit_item = fetch_else_create(unit_key)
                unit_item.moodle_file_json = moodle_file_json
                unit_item.moodle_course_json = moodle_course_json
                task_logs[unit_key] = unit_item

            course_key = CourseKey.from_json(moodle_course_json)
            if course_key not in task_logs:
                course_item = fetch_else_create(course_key)
                course_item.moodle_file_json = moodle_file_json
                course_item.moodle_course_json = moodle_course_json
                task_logs[course_key] = course_item

    return task_logs


# pylint: disable-next=too-many-locals
def insert_files_into_db(
    task_logs: dict[Key, TaskLog], file_cache: dict[str, FileCacheInfo]
) -> None:
    """Insert files referenced by `task_logs` into database using files from `file_cache`."""
    service = current_records_lom.records_service
    edit = partial(service.edit, identity=system_identity)

    df_service = service.draft_files
    commit_file = partial(df_service.commit_file, identity=system_identity)
    init_files = partial(df_service.init_files, identity=system_identity)
    list_draft_files = partial(df_service.list_files, identity=system_identity)
    set_file_content = partial(df_service.set_file_content, identity=system_identity)

    list_files = partial(service.files.list_files, identity=system_identity)

    for key, task_log in task_logs.items():
        if isinstance(key, FileKey):
            file_info = file_cache[key.url]

            # get files
            try:
                former_files = list(list_draft_files(id_=task_log.pid).entries)
            except NoResultFound:
                former_files = list(list_files(id_=task_log.pid).entries)
            if len(former_files) == 0:
                # no file attached yet ~> attach file

                # ensure a draft exists (files can only be uploaded to a draft, not to a record)
                edit(id_=task_log.pid)

                # upload file
                filename = file_info.path.name
                init_files(id_=task_log.pid, data=[{"key": filename}])
                with file_info.path.open(mode="rb", buffering=1024 * 1024) as file:
                    set_file_content(id_=task_log.pid, file_key=filename, stream=file)
                commit_file(id_=task_log.pid, file_key=filename)

                task_log.json["files"]["default_preview"] = filename

            elif len(former_files) == 1:
                # a file is already attached
                pass
            else:
                # LOM-records of resource_type 'file' may only have at most 1 file attached
                raise ValueError(
                    "encountered LOM-record of resource_type 'file' with more than 1 file attached"
                )


# pylint: disable-next=too-many-locals
def get_links(task_logs: dict[Key, TaskLog]) -> set[Link]:
    """Infer links from `task_logs`.

    Returns inferred links.
    If links to preceding courses are inferred and if those preceding courses exist,
    those preceding courses will add a task_log to `task_logs`.
    """
    # links' elements are of form (file_key, 'ispartof', 'asdfg-hjk42')
    links: set[Link] = set()  # to be result
    for key, task_log in task_logs.items():
        if isinstance(key, FileKey):
            # link all units with file
            for moodle_course_json in task_log.moodle_file_json["courses"]:
                if moodle_course_json["courseid"] == "0":
                    # don't consider moodle-only-courses
                    continue

                unit_key = UnitKey.from_json(
                    task_log.moodle_file_json, moodle_course_json
                )
                unit_log = task_logs[unit_key]
                links.add(Link(key, "ispartof", unit_log.pid))
                links.add(Link(unit_key, "haspart", task_log.pid))

        elif isinstance(key, UnitKey):
            # link unit with course
            course_key = CourseKey(key.courseid)
            course_log = task_logs[course_key]
            links.add(Link(key, "ispartof", course_log.pid))
            links.add(Link(course_key, "haspart", task_log.pid))

        elif isinstance(key, CourseKey):
            # link course with previous course, if it exists
            sourceid = task_log.moodle_course_json["sourceid"]
            if sourceid == "-1":
                # course has no associated preceding course
                continue

            source_course_key = CourseKey(sourceid)
            try:
                moodle_pid = PersistentIdentifier.get(
                    pid_type="moodle",
                    pid_value=source_course_key.to_string_key(),
                )
            except PIDDoesNotExistError:
                # source course has no entry in database
                continue

            if source_course_key not in task_logs:
                # add task-log for source-course
                service = current_records_lom.records_service
                read = partial(service, identity=system_identity)

                lomid_pid = PersistentIdentifier.get_by_object(
                    pid_type="lomid",
                    object_type=moodle_pid.object_type,
                    object_uuid=moodle_pid.object_uuid,
                )
                pid: str = lomid_pid.pid_value
                previous_json = read(id_=pid).to_dict()
                json_ = copy.deepcopy(previous_json)

                task_logs[source_course_key] = TaskLog(
                    pid=pid,
                    previous_json=previous_json,
                    json=json_,
                )

            links.add(Link(source_course_key, "iscontinuedby", task_log.pid))
            links.add(Link(key, "continues", task_logs[source_course_key].pid))

        else:
            raise TypeError("Cannot handle key of type {type(key)}.")

    return links


def update_course_metadata(course_tasklog: TaskLog) -> None:
    """Update `course_tasklog.json` using `course_tasklog.moodle_file_json` and `course_tasklog.moodle_course_json`."""
    metadata = LOMMetadata(course_tasklog.json or {}, overwritable=True)
    file_json = course_tasklog.moodle_file_json
    course_json = course_tasklog.moodle_course_json

    # convert courseid
    courseid = course_json["courseid"]
    metadata.append_identifier(courseid, catalog="moodle-id")

    # convert course-identifier
    identifier = course_json["identifier"]
    metadata.append_identifier(identifier, catalog="teachcenter-course-id")

    # convert coursename
    coursename = course_json["coursename"]
    metadata.set_title(coursename, language_code="x-none")

    # convert structure
    structure = course_json["structure"]
    metadata.append_keyword(structure, language_code="x-none")

    # convert context
    context = file_json["context"]
    metadata.append_context(context)

    course_tasklog.json = metadata.json


def update_unit_metadata(unit_tasklog: TaskLog) -> None:
    """Update `unit_tasklog.json` using `unit_tasklog.moodle_file_json` and `unit_tasklog.moodle_course_json`."""
    metadata = LOMMetadata(unit_tasklog.json or {}, overwritable=True)
    file_json = unit_tasklog.moodle_file_json
    course_json = unit_tasklog.moodle_course_json

    # multi-use input data
    year = file_json["year"]
    semester = file_json["semester"]

    # convert title
    coursename = course_json["coursename"]
    title = f"{coursename} ({semester} {year})"
    metadata.set_title(title, language_code="x-none")

    # convert language
    language = course_json["courselanguage"]
    metadata.append_language(language)

    # convert description
    description = html.unescape(course_json["description"])
    metadata.append_description(description, language_code="x-none")

    # convert semester
    semester = file_json["semester"]
    metadata.append_keyword(semester, language_code="x-none")

    # convert to version
    version = f"{semester} {year}"
    metadata.set_version(version, datetime=year)

    # convert lecturers
    for lecturer in course_json["lecturer"].split(","):
        lecturer = lecturer.strip()
        metadata.append_contribute(lecturer, role="Author")

    # convert organisation
    organisation = course_json["organisation"]
    metadata.append_contribute(organisation, role="Unknown")

    # convert year
    year = file_json["year"]
    metadata.set_datetime(year)

    # convert objective
    objective = html.unescape(course_json["objective"])
    metadata.append_educational_description(objective, language_code="x-none")

    unit_tasklog.json = metadata.json


# pylint: disable-next=too-many-locals
def update_file_metadata(
    file_tasklog: TaskLog,
    file_cache: dict[str, FileCacheInfo],
) -> None:
    """Update `file_tasklog.json` using `file_tasklog.moodle_file_json`."""
    metadata = LOMMetadata(file_tasklog.json or {}, overwritable=True)
    file_json = file_tasklog.moodle_file_json

    # multi-use input data
    language = file_json["language"]

    # convert title
    if title := file_json["title"]:
        metadata.set_title(title, language_code=language)
    else:
        file_info = file_cache[file_json["fileurl"]]
        metadata.set_title(file_info.path.name, language_code=language)

    # convert language
    metadata.append_language(language)

    # abstract
    if abstract := html.unescape(file_json["abstract"]):
        metadata.append_description(abstract, language_code=language)

    # convert tags
    for tag in file_json["tags"]:
        if tag:
            metadata.append_keyword(tag, language_code=language)

    # convert persons
    for person in file_json["persons"]:
        name = f"{person['firstname']} {person['lastname']}"
        metadata.append_contribute(name, role=person["role"])

    # convert timereleased
    timereleased = file_json["timereleased"]
    datetime_obj = datetime.fromtimestamp(int(timereleased))
    datetime_isoformat = str(datetime_obj.date().isoformat())
    metadata.set_datetime(datetime_isoformat)

    # convert mimetype
    mimetype = file_json["mimetype"]
    metadata.append_format(mimetype)

    # convert filesize
    filesize = file_json["filesize"]
    metadata.set_size(filesize)

    # convert resourcetype
    # https://skohub.io/dini-ag-kim/hcrt/heads/master/w3id.org/kim/hcrt/slide.en.html
    resourcetype = file_json["resourcetype"]
    learningresourcetype_by_resourcetype = {
        "No selection": None,
        "Presentationslide": "slide",
    }
    if learningresourcetype := learningresourcetype_by_resourcetype[resourcetype]:
        metadata.append_learningresourcetype(learningresourcetype)

    # convert license
    license_url = file_json["license"]["source"]
    metadata.set_rights_url(license_url)

    # convert classification
    oefos_ids = [
        value["identifier"]
        for classification in file_json["classification"]
        for value in classification["values"]
    ]
    # reorder to ['1234', '123', '2345', '234', '2']
    oefos_ids.sort(key=lambda id_: id_.ljust(6, chr(255)))
    # metadata.append_oefos(oefos_ids)
    for id_ in oefos_ids:
        metadata.append_oefos_id(id_)
        metadata.append_oefos_id(id_, "en")

    file_tasklog.json = metadata.json


# pylint: disable-next=too-many-locals
def insert_moodle_into_db(
    moodle_data: dict,
    filepaths_by_url: dict[str, Path] = None,
) -> None:
    """Insert data encoded in `moodle-data` into invenio-database.

    :param dict moodle_data: The data to be inserted into database,
        whose format matches `MoodleSchema`
    :param dict filepaths_by_url: A dictionary
        that maps some file-urls within `moodle_data` to filepaths.
        When a file-url is found in `filepaths_by_url`,
        the file on the corresponding filepath is used.
        Otherwise the file is downloaded from file-url.
    """
    # validate input
    moodle_data = MoodleSchema().load(moodle_data)
    filepaths_by_url = filepaths_by_url or {}
    moodle_file_jsons = [
        file_json
        for moodlecourse in moodle_data["moodlecourses"]
        for file_json in moodlecourse["files"]
    ]

    with TemporaryDirectory() as temp_dir:
        # download unprovided urls into `temp_dir`, build `file_cache`
        temp_dir = Path(temp_dir)
        file_cache: dict[str, FileCacheInfo] = cache_files(
            directory=temp_dir,
            provided_filepaths_by_url=filepaths_by_url,
            urls=[moodle_file_jsn["fileurl"] for moodle_file_jsn in moodle_file_jsons],
        )

        # initialize `task_logs`, which keeps track of one log each per course/unit/file
        task_logs: dict[Key, TaskLog] = prepare_tasks(moodle_data, file_cache)

        # enter files into database
        insert_files_into_db(task_logs, file_cache)

    # link records
    for link in get_links(task_logs):
        task_log = task_logs[link.key]
        metadata = LOMMetadata(task_log.json)
        metadata.append_relation(link.value, kind=link.kind)
        task_log.json = metadata.json

    # update lom-jsons with info from moodle
    for key, task_log in task_logs.items():
        if task_log.moodle_file_json is None:
            # this skips task_logs for courses from previous semesters
            continue

        if isinstance(key, FileKey):
            update_file_metadata(task_log, file_cache)
        elif isinstance(key, UnitKey):
            update_unit_metadata(task_log)
        elif isinstance(key, CourseKey):
            update_course_metadata(task_log)
        else:
            raise TypeError("Cannot handle key of type {type(key)}.")

    # update drafts
    service = current_records_lom.records_service
    edit = partial(service.edit, identity=system_identity)
    update_draft = partial(service.update_draft, identity=system_identity)
    for task_log in task_logs.values():
        if task_log.previous_json != task_log.json:
            # json got updated, now update database with new json
            edit(id_=task_log.pid)  # ensure a draft exists
            update_draft(id_=task_log.pid, data=task_log.json)

    # publish created drafts
    # uow rolls back all `publish`s if one fails as to prevent an inconsistent database-state
    read_draft = partial(service.read_draft, identity=system_identity)
    publish = partial(service.publish, identity=system_identity)
    with UnitOfWork() as uow:
        for task_log in task_logs.values():
            # only publish if a draft was created
            # (drafts are created iff record-updates are needed)
            try:
                # check if a draft exists for task_log.pid
                read_draft(id_=task_log.pid)
            except NoResultFound:
                # no draft found: continue
                continue
            else:
                # draft exists: publish
                publish(id_=task_log.pid, uow=uow)

        uow.commit()


def fetch_moodle() -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    response = requests.get(current_app.config["MOODLE_FETCH_URL"])
    response.raise_for_status()

    moodle_data = response.json()

    insert_moodle_into_db(moodle_data)
