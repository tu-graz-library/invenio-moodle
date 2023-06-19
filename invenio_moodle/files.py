# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Provide functions to store files into the database."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Callable
from functools import partial
from pathlib import Path

from invenio_access.permissions import system_identity
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_lom.proxies import current_records_lom
from invenio_records_lom.utils import LOMMetadata
from requests import Response, Session
from sqlalchemy.orm.exc import NoResultFound

from .decorators import (
    commit_file,
    edit,
    init_files,
    list_draft_files,
    list_files,
    set_file_content,
)
from .types import (
    CourseKey,
    FileCache,
    FileCacheInfo,
    FileKey,
    FilePaths,
    Key,
    Task,
    Tasks,
    UnitKey,
)


def save_file_locally(
    response: Response,
    idx: int,
    directory: Path,
) -> tuple[str, Path]:
    """Save file locally."""
    # find filename in headers
    dispos = response.headers.get("content-disposition", "")

    # all html-headers are encoded in latin1, but python interprets as utf-8
    dispos = dispos.encode("latin1").decode("utf-8")

    if match := re.search('filename="([^"]*)"', dispos):
        filename = match.group(1)
    else:
        msg = f"couldn't find filename in header {dispos}"
        raise ValueError(msg)

    # save file to `directory`, compute its hash along the way
    # filepath is of form 'directory/0/file.pdf'
    filepath = directory.joinpath(str(idx), filename.replace(" ", "_"))
    hash_ = hashlib.md5()  # noqa: S324

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
    """Create a file-cache.

    It creates a file-cache by downloading unprovided files into
    `directory` and hashing all files.

    :param Path directory: The directory to download unprovided files into.
    :param dict[str, Path] provided_filepaths_by_url:
        A dictionary that maps some urls to filepaths.
        When a url is in `provided_filepaths_by_url`,
        the file on the corresponding filepath is cached.
        Otherwise the file is downloaded from file-url.
    :param list[str] urls: The URLs of the to-be-cached files.
    """
    file_cache: FileCache = {}  # to be result
    directory = Path(directory)

    # add provided file-infos to `file_cache`
    for url, _path in provided_filepaths_by_url.items():
        hash_ = hashlib.md5()  # noqa: S324
        path = Path(_path)
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


def build_file_cache(
    temp_dir: str,
    moodle_file_jsons: list[dict],
    filepaths_by_url: list[str],
) -> FileCache:
    """Build file cache."""
    temp = Path(temp_dir)
    urls = [jsn["fileurl"] for jsn in moodle_file_jsons]
    file_cache: FileCache = cache_files(
        directory=temp,
        provided_filepaths_by_url=filepaths_by_url,
        urls=urls,
    )
    return file_cache


def create_moodle_file_jsons(moodle_data: dict) -> list:
    """Create moodle file jsons."""
    return [
        file_json
        for moodlecourse in moodle_data["moodlecourses"]
        for file_json in moodlecourse["files"]
    ]


def prepare_files(
    temp_dir: str,
    moodle_data: dict,
    filepaths_by_url: FilePaths,
) -> tuple[Tasks, FileCache]:
    """Prepare files."""
    moodle_file_jsons = create_moodle_file_jsons(moodle_data)

    # download unprovided urls into `temp_dir`, build `file_cache`
    file_cache = build_file_cache(temp_dir, moodle_file_jsons, filepaths_by_url)

    # initialize `task_logs`, which keeps track of one log each per course/unit/file
    task_logs = prepare_tasks(moodle_file_jsons, file_cache)

    return task_logs, file_cache


def fetch_else_create(key: Key) -> Task:
    """Fetch moodle-result corresponding to `key`, create database-entry if none exists.

    :param Key key: the key which to attempt fetching from pidstore
    """
    service = current_records_lom.records_service
    create = partial(service.create, identity=system_identity)
    read = partial(service.read, identity=system_identity)

    database_key = str(key)
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

    return Task(key=key, pid=pid, previous_json=previous_json, json=json_)


def prepare_tasks(moodle_file_jsons: list, file_cache: FileCache) -> Tasks:
    """Prepare database-drafts, initialize one `TaskLog` per draft.

    :param dict moodle_data: Data whose format matches `MoodleSchema`
    :param dict[str, FileCacheInfo] file_cache: file-cache,
        contains one file per "fileurl" within `moodle_data`
    """
    tasks = Tasks()

    # prepare: gather necessary information, create records if no
    # previous versions exist
    for moodle_file_json in moodle_file_jsons:
        file_key = FileKey.from_json_and_cache(moodle_file_json, file_cache)
        file_item = fetch_else_create(file_key)
        file_item.moodle_file_json = moodle_file_json
        tasks.append(file_item)

        for moodle_course_json in moodle_file_json["courses"]:
            if moodle_course_json["courseid"] == "0":
                # courseid '0' signifies moodle-only-courses, don't prepare those
                continue

            unit_key = UnitKey.from_json(moodle_file_json, moodle_course_json)
            if unit_key not in tasks:
                unit_item = fetch_else_create(unit_key)
                unit_item.moodle_file_json = moodle_file_json
                unit_item.moodle_course_json = moodle_course_json
                tasks.append(unit_item)

            course_key = CourseKey.from_json(moodle_course_json)
            if course_key not in tasks:
                course_item = fetch_else_create(course_key)
                course_item.moodle_file_json = moodle_file_json
                course_item.moodle_course_json = moodle_course_json
                tasks.append(course_item)

    return tasks


@edit
@commit_file
@init_files
@list_draft_files
@set_file_content
@list_files
def insert_files_into_db(
    tasks: Tasks,
    file_cache: FileCache,
    edit: Callable,
    commit_file: Callable,
    init_files: Callable,
    list_draft_files: Callable,
    set_file_content: Callable,
    list_files: Callable,
) -> None:
    """Insert files into DB.

    Insert files into db referenced by `task_logs` into database using
    files from `file_cache`.
    """
    for task in tasks:
        if not isinstance(task.key, FileKey):
            continue

        file_info = file_cache[task.key.url]

        # get files
        try:
            former_files = list(list_draft_files(id_=task.pid).entries)
        except NoResultFound:
            former_files = list(list_files(id_=task.pid).entries)

        # LOM-records of resource_type 'file' may only have at most 1 file attached
        if len(former_files) > 1:
            msg = (
                "encountered LOM-record of resource_type 'file'"
                " with more than 1 file attached"
            )
            raise ValueError(msg)

        # a file is already attached
        if len(former_files) == 1:
            continue

        # no file attached yet ~> attach file

        # ensure a draft exists (files can only be uploaded to a draft, not to a record)
        edit(id_=task.pid)

        # upload file
        filename = file_info.path.name
        init_files(id_=task.pid, data=[{"key": filename}])

        # ATTENTION: 1024 * 1024 may be a problem?
        with file_info.path.open(mode="rb", buffering=1024 * 1024) as fp:
            set_file_content(id_=task.pid, file_key=filename, stream=fp)
        commit_file(id_=task.pid, file_key=filename)

        task.json["files"]["default_preview"] = filename
