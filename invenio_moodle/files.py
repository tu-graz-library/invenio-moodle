# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Provide functions to store files into the database."""

import copy
import hashlib
import re
from functools import partial
from pathlib import Path

from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_lom.proxies import current_records_lom
from invenio_records_lom.utils import LOMMetadata
from requests import Response, Session
from sqlalchemy.orm.exc import NoResultFound

from .types import (
    CourseKey,
    FileCache,
    FileCacheInfo,
    FileKey,
    FilePaths,
    Key,
    TaskLog,
    TaskLogs,
    UnitKey,
)


def save_file_locally(response: Response, idx: int, directory: Path):
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
    filepath = directory.joinpath(str(idx), filename.replace(" ", "_"))
    hash_ = hashlib.md5()

    # create 'directory/0/'
    filepath.parent.mkdir(parents=True)

    with filepath.open(mode="wb", buffering=1024 * 1024) as fp:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            hash_.update(chunk)
            fp.write(chunk)

    return hash_.hexdigest(), filepath


def cache_files(
    directory: Path,
    provided_filepaths_by_url: FilePaths,
    urls: list[str],
) -> FileCache:
    """Creates a file-cache, downloading unprovided files into `directory` and hashing all files.

    :param Path directory: The directory to download unprovided files into.
    :param dict[str, Path] provided_filepaths_by_url: A dictionary that maps some urls to filepaths.
        When a url is in `provided_filepaths_by_url`,
        the file on the corresponding filepath is cached.
        Otherwise the file is downloaded from file-url.
    :param list[str] urls: The URLs of the to-be-cached files.
    """
    file_cache: FileCache = {}  # to be result
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
    with Session() as session:
        for idx, url in enumerate(urls):
            if url in provided_filepaths_by_url:
                continue

            with session.get(url, stream=True) as response:
                response.raise_for_status()

                hash_md5, filepath = save_file_locally(response, idx, directory)

            file_cache[url] = FileCacheInfo(hash_md5=hash_md5, path=filepath)

    return file_cache


def build_file_cache(temp_dir, moodle_file_jsons, filepaths_by_url):
    """Build file cache."""
    temp_dir = Path(temp_dir)
    urls = [jsn["fileurl"] for jsn in moodle_file_jsons]
    file_cache: FileCache = cache_files(
        directory=temp_dir,
        provided_filepaths_by_url=filepaths_by_url,
        urls=urls,
    )
    return file_cache


def create_moodle_file_jsons(moodle_data: dict):
    """Create moodle file jsons."""
    return [
        file_json
        for moodlecourse in moodle_data["moodlecourses"]
        for file_json in moodlecourse["files"]
    ]


def prepare_files(
    temp_dir: str, moodle_data: dict, filepaths_by_url: FilePaths
) -> TaskLogs:
    """Prepare files."""
    moodle_file_jsons = create_moodle_file_jsons(moodle_data)

    # download unprovided urls into `temp_dir`, build `file_cache`
    file_cache = build_file_cache(temp_dir, moodle_file_jsons, filepaths_by_url)

    # initialize `task_logs`, which keeps track of one log each per course/unit/file
    task_logs = prepare_tasks(moodle_file_jsons, file_cache)

    return task_logs, file_cache


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


def prepare_tasks(moodle_file_jsons: list, file_cache: FileCache) -> TaskLogs:
    """Prepare database-drafts, initialize one `TaskLog` per draft.

    :param dict moodle_data: Data whose format matches `MoodleSchema`
    :param dict[str, FileCacheInfo] file_cache: file-cache,
        contains one file per "fileurl" within `moodle_data`
    """
    task_logs = {}  # to be result

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
def insert_files_into_db(task_logs: TaskLogs, file_cache: FileCache) -> None:
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
        if not isinstance(key, FileKey):
            continue

        file_info = file_cache[key.url]

        # get files
        try:
            former_files = list(list_draft_files(id_=task_log.pid).entries)
        except NoResultFound:
            former_files = list(list_files(id_=task_log.pid).entries)

        # LOM-records of resource_type 'file' may only have at most 1 file attached
        if len(former_files) > 1:
            msg = "encountered LOM-record of resource_type 'file' with more than 1 file attached"
            raise ValueError(msg)

        # a file is already attached
        if len(former_files) == 1:
            continue

        # no file attached yet ~> attach file

        # ensure a draft exists (files can only be uploaded to a draft, not to a record)
        edit(id_=task_log.pid)

        # upload file
        filename = file_info.path.name
        init_files(id_=task_log.pid, data=[{"key": filename}])
        # TODO: 1024 * 1024 may be a problem?
        with file_info.path.open(mode="rb", buffering=1024 * 1024) as fp:
            set_file_content(id_=task_log.pid, file_key=filename, stream=fp)
        commit_file(id_=task_log.pid, file_key=filename)

        task_log.json["files"]["default_preview"] = filename
