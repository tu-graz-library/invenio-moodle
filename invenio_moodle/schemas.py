# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Schemas for validating input from moodle."""

from collections import Counter, defaultdict
from types import MappingProxyType

from marshmallow import Schema, ValidationError, validates_schema
from marshmallow.fields import Constant, Dict, Integer, List, Nested, String

from .utils import extract_moodle_records


class ControlledVocabularyField(String):
    """A controlled vocabulary field."""

    default_error_messages = MappingProxyType(
        {
            "not_in_vocabulary": "Value {string!r} not in controlled vocabulary {vocabulary!r}.",
        },
    )

    def __init__(self, *, vocabulary: list | None = None, **kwargs: dict) -> None:
        """Initialize self."""
        self.vocabulary = vocabulary
        super().__init__(**kwargs)

    def _deserialize(
        self,
        value: str | None,
        attr: str | None,
        data: dict | None,
        **kwargs: dict,
    ) -> str:
        string = super()._deserialize(value, attr, data, **kwargs)
        if string not in self.vocabulary:
            msg = "not_in_vocabulary"
            raise self.make_error(msg, vocabulary=self.vocabulary, string=string)
        return string


class ClassificationValuesSchema(Schema):
    """Moodle classification-values schema."""

    identifier = String(required=True)
    name = String(required=True)


class ClassificationSchema(Schema):
    """Moodle classification schema."""

    type = Constant("oefos", required=True)
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


class ElementSchema(Schema):
    """Moodle file schema."""

    abstract = String(required=True)
    classification = List(Nested(ClassificationSchema), required=True)
    contenthash = String()  # application profile 1.0
    identifier = String()  # application profile 2.0
    context = String(required=True)
    courses = List(Nested(CourseSchema), required=True)
    filecreationtime = String()
    filesize = Integer()
    fileurl = String()  # application profile 1.0
    source = String()  # application profile 2.0
    language = String(required=True)
    license = Nested(LicenseSchema)
    mimetype = String()
    persons = List(Nested(PersonSchema), required=True)
    resourcetype = String(required=True)
    semester = ControlledVocabularyField(vocabulary=["SS", "WS"], required=True)
    tags = List(String(), required=True)
    timereleased = String(required=True)
    title = String(required=True)
    year = String(required=True)
    duration = String()


class MoodleCourseSchema(Schema):
    """Moodle moodlecourse schema."""

    elements = List(Nested(ElementSchema))


class MoodleSchema(Schema):
    """Moodle moodlecourses schema.

    Data coming from moodle should be in this format.
    """

    @validates_schema
    def validate_urls_unique(self, data: dict, **__: dict) -> None:
        """Check that each file-URL only appears once."""
        urls_counter = Counter(
            file_["fileurl"] if "fileurl" in file_ else file_["source"]
            for file_ in extract_moodle_records(data)
        )
        duplicated_urls = [url for url, count in urls_counter.items() if count > 1]
        if duplicated_urls:
            msg = f"Different file-JSONs with same URL {duplicated_urls}."
            raise ValidationError(msg)

    # @validates_schema
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
                    if course_id not in jsons_by_courseid[course_id]:
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


class MoodleSchemaApplicationProfile1(MoodleSchema):
    """Moodle Schema for application profile 1.0."""

    applicationprofile = String(required=True)
    moodlecourses = Dict(
        keys=String(),
        values=Nested(MoodleCourseSchema, required=True),
    )


class MoodleSchemaApplicationProfile2(MoodleSchema):
    """Moodle schema for application profile 2.0."""

    applicationprofile = String(required=True)
    moodlecourses = List(Nested(MoodleCourseSchema))
