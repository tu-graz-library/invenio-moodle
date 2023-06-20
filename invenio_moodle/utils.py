# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for inserting moodle-data into invenio-style database."""

from __future__ import annotations

import typing as t
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from invenio_records_resources.services.uow import UnitOfWork, unit_of_work
from sqlalchemy.orm.exc import NoResultFound

from .convert import update_metadata
from .decorators import edit, publish, resolve, update_draft
from .files import insert_files_into_db, prepare_files
from .links import get_links
from .schemas import MoodleSchema

if t.TYPE_CHECKING:
    from .types import Tasks


@edit
@update_draft
def update_drafts(tasks: Tasks, edit: Callable, update_draft: Callable) -> None:
    """Update drafts."""
    for task in tasks:
        if task.previous_metadata == task.metadata:
            continue

        # json got updated, now update database with new json
        edit(id_=task.pid)  # ensure a draft exists
        update_draft(id_=task.pid, data=task.json)


@unit_of_work()
@resolve
@publish
def publish_created_drafts(
    tasks: Tasks,
    resolve: Callable,
    publish: Callable,
    uow: UnitOfWork = None,
) -> None:
    """Publish created drafts."""
    for task in tasks:
        try:
            # check if a draft exists for task.pid
            resolve(pid_value=task.pid)
        except NoResultFound:
            continue
        else:
            publish(id_=task.pid, uow=uow)


def insert_moodle_into_db(moodle_data: dict) -> None:
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

    with TemporaryDirectory() as temp_dir:
        tasks, file_cache = prepare_files(Path(temp_dir), moodle_data)
        insert_files_into_db(tasks, file_cache)

    # link records to each other
    for link in get_links(tasks):
        task = tasks[link.key]
        task.metadata.append_relation(link.value, kind=link.kind)

    for task in tasks:
        # this skips task_logs for courses from previous semesters
        if task.moodle_file_metadata is None:
            continue

        update_metadata(task.key, task, file_cache)

    update_drafts(tasks)
    publish_created_drafts(tasks)
