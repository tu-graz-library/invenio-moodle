# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Convert Moodle metadata format into LOM format."""

from datetime import datetime
from html import unescape

from invenio_records_lom.utils import LOMMetadata

from .types import FileCache, TaskLog


def update_course_metadata(course_tasklog: TaskLog) -> None:
    """Update `course_tasklog.json`.

    The update uses `course_tasklog.moodle_file_json` and
    `course_tasklog.moodle_course_json`.
    """
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
    """Update `unit_tasklog.json`.

    The update uses `unit_tasklog.moodle_file_json` and
    `unit_tasklog.moodle_course_json`.
    """
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

    unit_tasklog.json = metadata.json


# pylint: disable-next=too-many-locals
def update_file_metadata(file_tasklog: TaskLog, file_cache: FileCache) -> None:
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
    if abstract := unescape(file_json["abstract"]):
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

    file_tasklog.json = metadata.json
