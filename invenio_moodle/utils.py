# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for inserting moodle-data into invenio-style database."""

from __future__ import annotations

from functools import partial
from tempfile import TemporaryDirectory

from invenio_access.permissions import system_identity
from invenio_records_lom.proxies import current_records_lom
from invenio_records_lom.utils import LOMMetadata
from invenio_records_resources.services.uow import UnitOfWork, unit_of_work
from requests import get
from sqlalchemy.orm.exc import NoResultFound

from .convert import update_course_metadata, update_file_metadata, update_unit_metadata
from .files import insert_files_into_db, prepare_files
from .links import get_links
from .schemas import MoodleSchema
from .types import CourseKey, FileKey, FilePaths, TaskLogs, UnitKey


def update_drafts(task_logs: TaskLogs):
    """Update drafts."""
    service = current_records_lom.records_service
    edit = partial(service.edit, identity=system_identity)
    update_draft = partial(service.update_draft, identity=system_identity)

    for task_log in task_logs.values():
        if task_log.previous_json == task_log.json:
            continue

        # json got updated, now update database with new json
        edit(id_=task_log.pid)  # ensure a draft exists
        update_draft(id_=task_log.pid, data=task_log.json)


@unit_of_work()
def publish_created_drafts(task_logs: TaskLogs, uow: UnitOfWork = None):
    """Publish created drafts."""
    # uow rolls back all `publish`s if one fails as to prevent an inconsistent database-state
    service = current_records_lom.records_service
    read_draft = partial(service.read_draft, identity=system_identity)
    publish = partial(service.publish, identity=system_identity)

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


# pylint: disable-next=too-many-locals
def insert_moodle_into_db(
    moodle_data: dict, filepaths_by_url: FilePaths = None
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

    with TemporaryDirectory() as temp_dir:
        task_logs, file_cache = prepare_files(temp_dir, moodle_data, filepaths_by_url)

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

    update_drafts(task_logs)
    publish_created_drafts(task_logs)


def fetch_moodle(moodle_fetch_url: str) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    response = get(moodle_fetch_url)
    response.raise_for_status()

    moodle_data = response.json()

    insert_moodle_into_db(moodle_data)
