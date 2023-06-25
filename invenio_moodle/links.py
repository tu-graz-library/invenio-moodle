# # -*- coding: utf-8 -*-
# #
# # Copyright (C) 2022-2023 Graz University of Technology.
# #
# # invenio-moodle is free software; you can redistribute it and/or modify
# # it under the terms of the MIT License; see LICENSE file for more details.

# """Create links between lom records."""

# import copy
# from collections.abc import Callable
# from functools import singledispatch

# from invenio_pidstore.errors import PIDDoesNotExistError
# from invenio_pidstore.models import PersistentIdentifier

# from .decorators import read
# from .types import CourseKey, CourseTask, FileTask, Link, Links, Task, Tasks, UnitTask
# from .utils import is_course_root


# @singledispatch
# def extract_links(task: Task) -> Links:  # noqa: ARG001
#     """Dispatcher for add_links."""
#     msg = f"Cannot handle key of type {task.key}."
#     raise TypeError(msg)


# @extract_links.register
# def _(
#     task: FileTask,
# ) -> Links:
#     """Get file key links."""
#     links = Links()

#     for unit_task in task.unit_tasks:
#         links.append(Link(task.key, "ispartof", unit_task.pid))
#         links.append(Link(unit_task.key, "haspart", task.pid))

#     return links


# @extract_links.register
# def _(
#     task: UnitTask,
# ) -> Links:
#     """Link unit with course."""
#     links = Links()

#     for file_task in task.unit_tasks:
#         links.append(Link(task.key))
#     return Links(
#         Link(task.key, "ispartof", course_task.pid),
#         Link(course_key, "haspart", task.pid),
#     )


# @read
# @extract_links.register
# def _(
#     task: CourseTask,
#     tasks: Tasks,
#     read: Callable,
# ) -> None:
#     """Link course with previous course, if it exists."""
#     sourceid = task.moodle_course_json["sourceid"]

#     if is_course_root(sourceid):
#         return

#     source_course_key = CourseKey(sourceid)
#     try:
#         moodle_pid = PersistentIdentifier.get(
#             pid_type="moodle",
#             pid_value=str(source_course_key),
#         )
#     except PIDDoesNotExistError:
#         # source course has no entry in database
#         return

#     if source_course_key not in tasks:
#         lomid_pid = PersistentIdentifier.get_by_object(
#             pid_type="lomid",
#             object_type=moodle_pid.object_type,
#             object_uuid=moodle_pid.object_uuid,
#         )
#         pid: str = lomid_pid.pid_value
#         previous_metadata = read(id_=pid).to_dict()
#         json_ = copy.deepcopy(previous_metadata)

#         tasks.append(
#             Task(
#                 key=source_course_key,
#                 pid=pid,
#                 previous_metadata=previous_metadata,
#                 json=json_,
#             ),
#         )

#     links.add(Link(source_course_key, "iscontinuedby", task.pid))
#     links.add(Link(key, "continues", tasks[source_course_key].pid))


# def get_links(tasks: Tasks) -> Links:
#     """Infer links from `tasks`.

#     Returns inferred links.
#     If links to preceding courses are inferred and if those preceding courses exist,
#     those preceding courses will add a task to `tasks`.

#     links elements are of form (file_key, 'ispartof', 'asdfg-hjk42')
#     """
#     TODO
#     return {extract_links(task.key, task, tasks) for task in tasks}
