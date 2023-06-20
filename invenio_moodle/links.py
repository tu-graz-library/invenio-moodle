# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Create links between lom records."""

import copy
from collections.abc import Callable
from functools import singledispatch

from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier

from .decorators import read
from .types import CourseKey, FileKey, Key, Link, Links, Task, Tasks, UnitKey


def is_moodle_only_course(moodle_course_metadata: dict) -> bool:
    """Check if it is a moodle only course."""
    return moodle_course_metadata["courseid"] == "0"


def is_course_root(sourceid: str) -> bool:
    """Check if parent exists."""
    return sourceid == "-1"


@singledispatch
def extract_links(key: Key, tasks: Tasks, task: Task) -> Links:  # noqa: ARG001
    """Dispatcher for add_links."""
    msg = f"Cannot handle key of type {key}."
    raise TypeError(msg)


@extract_links.register
def _(
    key: FileKey,
    links: Links,
    tasks: Tasks,
    task: Task,
) -> Links:
    """Get file key links."""
    for moodle_course_metadata in task.moodle_file_metadata["courses"]:
        if is_moodle_only_course(moodle_course_metadata):
            continue

        unit_key = UnitKey(task.moodle_file_json, moodle_course_metadata)
        unit_task = tasks[unit_key]  # <--- somehow strange TODO
        links.add(Link(key, "ispartof", unit_task.pid))
        links.add(Link(unit_key, "haspart", task.pid))

    return links


@extract_links.register
def _(
    key: UnitKey,
    links: Links,
    tasks: Tasks,
    task: Task,
) -> None:
    """Link unit with course."""
    course_key = CourseKey(key.courseid)
    course_task = tasks[course_key]
    links.add(Link(key, "ispartof", course_task.pid))
    links.add(Link(course_key, "haspart", task.pid))


@read
@extract_links.register
def _(
    key: CourseKey,
    links: Links,
    tasks: Tasks,
    task: Task,
    read: Callable,
) -> None:
    """Link course with previous course, if it exists."""
    sourceid = task.moodle_course_json["sourceid"]

    if is_course_root(sourceid):
        return

    source_course_key = CourseKey(sourceid)
    try:
        moodle_pid = PersistentIdentifier.get(
            pid_type="moodle",
            pid_value=str(source_course_key),
        )
    except PIDDoesNotExistError:
        # source course has no entry in database
        return

    if source_course_key not in tasks:
        lomid_pid = PersistentIdentifier.get_by_object(
            pid_type="lomid",
            object_type=moodle_pid.object_type,
            object_uuid=moodle_pid.object_uuid,
        )
        pid: str = lomid_pid.pid_value
        previous_metadata = read(id_=pid).to_dict()
        json_ = copy.deepcopy(previous_metadata)

        tasks.append(
            Task(
                key=source_course_key,
                pid=pid,
                previous_metadata=previous_metadata,
                json=json_,
            ),
        )

    links.add(Link(source_course_key, "iscontinuedby", task.pid))
    links.add(Link(key, "continues", tasks[source_course_key].pid))


def get_links(tasks: Tasks) -> Links:
    """Infer links from `tasks`.

    Returns inferred links.
    If links to preceding courses are inferred and if those preceding courses exist,
    those preceding courses will add a task to `tasks`.

    links elements are of form (file_key, 'ispartof', 'asdfg-hjk42')
    """
    return {extract_links(task.key, tasks, task) for task in tasks}
