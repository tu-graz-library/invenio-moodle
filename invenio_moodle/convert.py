# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Convert Moodle metadata format into LOM format."""

from datetime import datetime
from functools import singledispatch
from html import unescape

from invenio_records_lom.utils import LOMMetadata

from .types import CourseKey, FileCache, FileKey, Key, Task, UnitKey


@singledispatch
def update_metadata(key: Key, task: Task, **kwargs: dict) -> None:  # noqa: ARG001
    """Update Metadata."""
    msg = f"Cannot handle key of type {key}."
    raise TypeError(msg)


@update_metadata.register
def _(key: CourseKey, course_task: Task, **kwargs: dict) -> None:  # noqa: ARG001
    """Create metadata of the course.

    Update the metadata of the `course_task` by using the metadata from
    `moodle_file_metadata` and `moodle_course_metadata` metadata.
    """
    metadata = LOMMetadata(course_task.metadata or {}, overwritable=True)
    file_json = course_task.moodle_file_metadata
    course_json = course_task.moodle_course_metadata

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

    course_task.set_metadata(metadata)


@update_metadata.register
def _(key: UnitKey, unit_task: Task, **kwargs: dict) -> None:  # noqa: ARG001
    """Update `unit_task.metadata`.

    The update uses `unit_tasklog.moodle_file_metadata` and
    `unit_tasklog.moodle_course_metadata`.
    """
    metadata = LOMMetadata(unit_task.metadata or {}, overwritable=True)
    file_json = unit_task.moodle_file_metadata
    course_json = unit_task.moodle_course_metadata

    # multi-use input data
    year = file_json["year"]
    semester = file_json["semester"]

    # convert title
    course_name = course_json["coursename"]
    title = f"{course_name} ({semester} {year})"
    metadata.set_title(title, language_code="x-none")

    # convert language
    language = course_json["courselanguage"]
    metadata.append_language(language)

    # convert description
    description = unescape(course_json["description"])
    metadata.append_description(description, language_code="x-none")

    # convert semester
    semester = file_json["semester"]
    metadata.append_keyword(semester, language_code="x-none")

    # convert to version
    version = f"{semester} {year}"
    metadata.set_version(version, datetime=year)

    # convert lecturers
    for lecturer in course_json["lecturer"].split(","):
        metadata.append_contribute(lecturer.strip(), role="Author")

    # convert organisation
    organisation = course_json["organisation"]
    metadata.append_contribute(organisation, role="Unknown")

    # convert year
    year = file_json["year"]
    metadata.set_datetime(year)

    # convert objective
    objective = unescape(course_json["objective"])
    metadata.append_educational_description(objective, language_code="x-none")

    unit_task.set_metadata(metadata)


@update_metadata.register
def _(key: FileKey, file_task: Task, file_cache: FileCache) -> None:  # noqa: ARG001
    """Update `file_task.metadata` using `file_tasklog.moodle_file_metadata`."""
    metadata = LOMMetadata(file_task.metadata or {}, overwritable=True)
    file_json = file_task.moodle_file_metadata

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
    if abstract := unescape(file_json["abstract"]):
        metadata.append_description(abstract, language_code=language)

    # convert tags
    for tag in filter(bool, file_json["tags"]):
        metadata.append_keyword(tag, language_code=language)

    # convert persons
    for person in file_json["persons"]:
        name = f"{person['firstname']} {person['lastname']}"
        metadata.append_contribute(name, role=person["role"])

    # convert timereleased
    time_released = int(file_json["timereleased"])
    datetime_obj = datetime.fromtimestamp(time_released)
    datetime_isoformat = datetime_obj.date().isoformat()
    metadata.set_datetime(datetime_isoformat)

    # convert mimetype
    metadata.append_format(file_json["mimetype"])

    # convert filesize
    metadata.set_size(file_json["filesize"])

    # convert resourcetype
    # https://skohub.io/dini-ag-kim/hcrt/heads/master/w3id.org/kim/hcrt/slide.en.html
    resourcetype = file_json["resourcetype"]
    learningresourcetype_by_resourcetype = {
        "No selection": None,
        "Presentationslide": "slide",
        "Exercise": "assessment",
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

    # metadata.append_oefos(oefos_ids) # noqa: ERA001
    for id_ in oefos_ids:
        metadata.append_oefos_id(id_)
        metadata.append_oefos_id(id_, "en")

    file_task.set_metadata(metadata)
