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
from pathlib import Path

from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_lom import LOMMetadata
from requests import Response, Session
from sqlalchemy.orm.exc import NoResultFound

from .decorators import (
    commit_file,
    create,
    edit,
    init_files,
    list_draft_files,
    list_files,
    read,
    set_file_content,
)
from .types import (
    CourseKey,
    FileCache,
    FileCacheInfo,
    FileKey,
    Key,
    Task,
    Tasks,
    UnitKey,
)
from .utils import is_moodle_only_course


def save_file_locally(response: Response, idx: int, directory: Path) -> FileCacheInfo:
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

    return FileCacheInfo(hash_md5=hash_.hexdigest(), path=filepath)


def cache_files(directory: Path, urls: list[str]) -> FileCache:
    """Create a file-cache.

    It creates a file-cache by downloading unprovided files into
    `directory` and hashing all files.

    :param Path directory: The directory to download unprovided files into.
    :param list[str] urls: The URLs of the to-be-cached files.
    """
    file_cache: FileCache = {}

    with Session() as session:
        for idx, url in enumerate(urls):
            with session.get(url, stream=True) as response:
                response.raise_for_status()

            file_cache[url] = save_file_locally(response, idx, directory)

    return file_cache


def build_file_cache(temp_dir: Path, moodle_records: list[dict]) -> FileCache:
    """Build file cache.

    download unprovided urls into `temp_dir`, build `file_cache`
    """
    urls = [jsn["fileurl"] for jsn in moodle_records]
    file_cache: FileCache = cache_files(
        directory=temp_dir,
        urls=urls,
    )
    return file_cache


def extract_moodle_records(moodle_data: dict) -> list[dict]:
    """Create moodle file jsons."""
    return [
        file_json
        for moodle_course in moodle_data["moodlecourses"]
        for file_json in moodle_course["files"]
    ]


def prepare_files(temp_dir: Path, moodle_data: dict) -> tuple[Tasks, FileCache]:
    """Prepare files."""
    moodle_records = extract_moodle_records(moodle_data)

    file_cache = build_file_cache(temp_dir, moodle_records)
    tasks = prepare_tasks(moodle_records, file_cache)

    return tasks, file_cache


@create
@read
def fetch_else_create(key: Key, create: Callable, read: Callable) -> Task:
    """Fetch moodle-result corresponding to `key`, create database-entry if none exists.

    :param Key key: the key which to attempt fetching from pidstore
    """
    database_key = str(key)
    try:
        moodle_pid = PersistentIdentifier.get(pid_type="moodle", pid_value=database_key)
    except PIDDoesNotExistError:
        # create draft with empty metadata
        pids_dict = {
            "moodle": {
                "provider": "moodle",
                "identifier": database_key,
            },
        }
        metadata = LOMMetadata.create(resource_type=key.resource_type, pids=pids_dict)
        metadata.append_identifier(database_key, catalog="moodle")
        draft_item = create(data=metadata.json)

        pid: str = draft_item.id
        previous_metadata = None
        metadata = LOMMetadata(draft_item.to_dict())
    else:
        # get lomid corresponding to moodle_pid
        lomid_pid = PersistentIdentifier.get_by_object(
            pid_type="lomid",
            object_type=moodle_pid.object_type,
            object_uuid=moodle_pid.object_uuid,
        )

        pid: str = lomid_pid.pid_value
        previous_metadata = read(id_=pid).to_dict()
        metadata = LOMMetadata(copy.deepcopy(previous_metadata))

    return Task(
        key=key,
        pid=pid,
        previous_metadata=previous_metadata,
        metadata=metadata,
    )


def prepare_tasks(moodle_records: list[dict], file_cache: FileCache) -> Tasks:
    """Prepare database-drafts, initialize one `Task` per draft.

    :param dict moodle_data: Data whose format matches `MoodleSchema`
    :param dict[str, FileCacheInfo] file_cache: file-cache,
        contains one file per "fileurl" within `moodle_data`

    initialize `tasks`, which keeps track of one task each per course/unit/file
    """
    tasks = Tasks()

    # prepare: gather necessary information, create records if no
    # previous versions exist
    for moodle_file_metadata in moodle_records:
        file_key = FileKey(moodle_file_metadata, file_cache)
        file_task = fetch_else_create(file_key)
        file_task.moodle_record_metadata = moodle_file_metadata
        tasks.append(file_task)

        for moodle_course_metadata in moodle_file_metadata["courses"]:
            if is_moodle_only_course(moodle_course_metadata):
                continue

            unit_key = UnitKey(moodle_file_metadata, moodle_course_metadata)
            if unit_key not in tasks:
                unit_task = fetch_else_create(unit_key)
                unit_task.moodle_file_metadata = moodle_file_metadata
                unit_task.moodle_course_metadata = moodle_course_metadata
                tasks.append(unit_task)

            course_key = CourseKey(moodle_course_metadata)
            if course_key not in tasks:
                course_task = fetch_else_create(course_key)
                course_task.moodle_file_metadata = moodle_file_metadata
                course_task.moodle_course_metadata = moodle_course_metadata
                tasks.append(course_task)

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
    for task in tasks.filter_by(FileKey):
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
        file_info = file_cache[task.key.url]
        filename = file_info.path.name
        init_files(id_=task.pid, data=[{"key": filename}])

        # ATTENTION: 1024 * 1024 may be a problem?
        with file_info.path.open(mode="rb", buffering=1024 * 1024) as fp:
            set_file_content(id_=task.pid, file_key=filename, stream=fp)
        commit_file(id_=task.pid, file_key=filename)

        task.metadata.record["files.default_preview"] = filename
