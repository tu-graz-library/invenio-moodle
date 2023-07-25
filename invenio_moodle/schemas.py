# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Schemas for validating input from moodle."""

from collections import Counter, defaultdict

from invenio_records_lom.services.schemas.fields import ControlledVocabularyField
from marshmallow import Schema, ValidationError, validates_schema
from marshmallow.fields import Constant, Dict, List, Nested, String


class ClassificationValuesSchema(Schema):
    """Moodle classification-values schema."""

    identifier = String(required=True)
    name = String(required=True)


class ClassificationSchema(Schema):
    """Moodle classification schema."""

    type = Constant("oefos", required=True)  # noqa: A003
    url = Constant(
        "https://www.data.gv.at/katalog/dataset/stat_ofos-2012",
        required=True,
    )
    values = List(Nested(ClassificationValuesSchema), required=True)


class CourseSchema(Schema):
    """Moodle course schema."""

    courseid = String(required=True)
    courselanguage = String(required=True)
    coursename = String(required=True)
    description = String(required=True)
    identifier = String(required=True)
    lecturer = String(required=True)
    objective = String(required=True)
    organisation = String(required=True)
    sourceid = String(required=True)
    structure = ControlledVocabularyField(
        vocabulary=[
            "",
            "Seminar (SE)",
            "Vorlesung (VO)",
            "Übung (UE)",
            "Seminar-Projekt (SP)",
            "Vorlesung und Übung (VU)",
            "Orientierungslehrveranstaltung (OL)",
        ],
        required=True,
    )


class LicenseSchema(Schema):
    """Moodle license schema."""

    fullname = String(required=True)
    shortname = String(required=True)
    source = String(required=True)


class PersonSchema(Schema):
    """Moodle person schema."""

    firstname = String(required=True)
    lastname = String(required=True)
    role = String(required=True)


class FileSchema(Schema):
    """Moodle file schema."""

    abstract = String(required=True)
    classification = List(Nested(ClassificationSchema), required=True)
    contenthash = String(required=True)
    context = String(required=True)
    courses = List(Nested(CourseSchema), required=True)
    filecreationtime = String(required=True)
    filesize = String(required=True)
    fileurl = String(required=True)
    language = String(required=True)
    license = Nested(LicenseSchema)  # noqa: A003
    mimetype = String(required=True)
    persons = List(Nested(PersonSchema), required=True)
    resourcetype = String(required=True)
    semester = ControlledVocabularyField(vocabulary=["SS", "WS"], required=True)
    tags = List(String(), required=True)
    timereleased = String(required=True)
    title = String(required=True)
    year = String(required=True)


class MoodleCourseSchema(Schema):
    """Moodle moodlecourse schema."""

    files = List(Nested(FileSchema))


class MoodleSchema(Schema):
    """Moodle moodlecourses schema.

    Data coming from moodle should be in this format.
    """

    applicationprofile = String(required=True)
    moodlecourses = Dict(
        keys=String(),
        values=Nested(MoodleCourseSchema, required=True),
    )

    @validates_schema
    def validate_urls_unique(self, data: dict, **__: dict) -> None:
        """Check that each file-URL only appears once."""
        urls_counter = Counter(
            file_["fileurl"]
            for _, moodlecourse in data["moodlecourses"].items()
            for file_ in moodlecourse["files"]
        )
        duplicated_urls = [url for url, count in urls_counter.items() if count > 1]
        if duplicated_urls:
            msg = f"Different file-JSONs with same URL {duplicated_urls}."
            raise ValidationError(msg)

    @validates_schema
    def validate_course_jsons_unique_per_courseid(self, data: dict, **__: dict) -> None:
        """Validate against unique courseid.

        Check that course-ids that appear multiple times have same
        json in all their appearances.
        """
        jsons_by_courseid = defaultdict(list)
        for moodlecourse in data["moodlecourses"].values():
            for file_ in moodlecourse["files"]:
                for course in file_["courses"]:
                    course_id = course["courseid"]
                    if course not in jsons_by_courseid[course_id]:
                        jsons_by_courseid[course_id].append(course)

        ambiguous_courseids = {
            course_id
            for course_id, jsons in jsons_by_courseid.items()
            if len(jsons) > 1
        }

        # '0' is special courseid shared by all moodle-only courses,
        # it is allowed to be ambiguous
        ambiguous_courseids -= {"0"}

        if ambiguous_courseids:
            course_ids = ", ".join(course_id for course_id in ambiguous_courseids)
            msg = f"Different course-JSONs with same courseid {course_ids}."
            raise ValidationError(msg)
