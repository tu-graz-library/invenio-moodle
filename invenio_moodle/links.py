# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Create links between lom records."""

import copy
from collections.abc import Callable

from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier

from .decorators import read
from .types import CourseKey, FileKey, Key, Link, Links, TaskLog, TaskLogs, UnitKey


def is_moodle_only_course(moodle_course_json: dict) -> bool:
    """Check if it is a moodle only course."""
    return moodle_course_json["courseid"] == "0"


def is_course_the_root(sourceid: str) -> bool:
    """Check if parent exists."""
    return sourceid == "-1"


def add_file_key_links(
    links: Links,
    task_logs: TaskLogs,
    key: Key,
    task_log: TaskLog,
) -> Links:
    """Get file key links."""
    for moodle_course_json in task_log.moodle_file_json["courses"]:
        if is_moodle_only_course(moodle_course_json):
            continue

        unit_key = UnitKey.from_json(task_log.moodle_file_json, moodle_course_json)
        unit_log = task_logs[unit_key]
        links.add(Link(key, "ispartof", unit_log.pid))
        links.add(Link(unit_key, "haspart", task_log.pid))

    return links


def add_unit_key_links(
    links: Links,
    task_logs: TaskLogs,
    key: Key,
    task_log: TaskLog,
) -> None:
    """Link unit with course."""
    course_key = CourseKey(key.courseid)
    course_log = task_logs[course_key]
    links.add(Link(key, "ispartof", course_log.pid))
    links.add(Link(course_key, "haspart", task_log.pid))


@read
def add_course_key_links(
    links: Links,
    task_logs: TaskLogs,
    key: Key,
    task_log: TaskLog,
    read: Callable,
) -> None:
    """Link course with previous course, if it exists."""
    sourceid = task_log.moodle_course_json["sourceid"]

    if is_course_the_root(sourceid):
        return

    source_course_key = CourseKey(sourceid)
    try:
        pid_value = str(source_course_key)
        moodle_pid = PersistentIdentifier.get(pid_type="moodle", pid_value=pid_value)
    except PIDDoesNotExistError:
        # source course has no entry in database
        return

    if source_course_key not in task_logs:
        # add task-log for source-course

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


def get_links(task_logs: TaskLogs) -> Links:
    """Infer links from `task_logs`.

    Returns inferred links.
    If links to preceding courses are inferred and if those preceding courses exist,
    those preceding courses will add a task_log to `task_logs`.

    links elements are of form (file_key, 'ispartof', 'asdfg-hjk42')
    """
    links: Links = set()

    for key, task_log in task_logs.items():
        if isinstance(key, FileKey):
            add_file_key_links(links, task_logs, key, task_log)
        elif isinstance(key, UnitKey):
            add_unit_key_links(links, task_logs, key, task_log)
        elif isinstance(key, CourseKey):
            add_course_key_links(links, task_logs, key, task_log)
        else:
            msg = f"Cannot handle key of type {type(key)}."
            raise TypeError(msg)

    return links
