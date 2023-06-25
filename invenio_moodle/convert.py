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


class Visitor:
    """Visitor base class."""

    def visit(self, value: dict, record: LOMMetadata) -> None:
        """Convert record from Moodle JSON format to LOMMetadata."""
        for attribute, val in value.items():
            self.visit_attribute(attribute, val, record)

    def visit_attribute(
        self,
        attribute: str,
        value: dict,
        record: LOMMetadata,
    ) -> None:
        """Traverse first level elements of dictionary and extract attributes."""

        def func_not_found(*_: dict, **__: dict) -> None:
            msg = f"NO visitor node: '{attribute}'"
            raise ValueError(msg)

        visit_function = getattr(self, f"visit_{attribute}", func_not_found)
        return visit_function(value, record)


class MoodleCourseToLOMCourse(Visitor):
    """Convert Moodle course type to LOM course resource type."""

    def visit_courseid(self, value: str, record: LOMMetadata) -> None:
        """Visit courseid."""
        record.append_identifier(value, catalog="moodle-id")

    def visit_identifier(self, value: str, record: LOMMetadata) -> None:
        """Visit identifier."""
        record.append_identifier(value, catalog="teachcenter-course-id")

    def visit_coursename(self, value: str, record: LOMMetadata) -> None:
        """Visit coursename."""
        record.set_title(value, language_code="x-none")

    def visit_structure(self, value: str, record: LOMMetadata) -> None:
        """Visit structure."""
        record.append_keyword(value, language_code="x-none")

    def visit_context(self, value: str, record: LOMMetadata) -> None:
        """Visit context."""
        record.append_context(value)


class MoodleUnitToLOMUnit(Visitor):
    """Moodle unit to lom unit."""

    def visit(self, value: str, record: LOMMetadata) -> None:
        """Visit."""
        super().visit(value, record)

        title = f"{self.course_name} ({self.semester} {self.year})"
        record.set_title(title, language_code="x-none")

        version = f"{self.semester} {self.year}"
        record.set_version(version, datetime=self.year)

    def visit_year(self, value: str, record: LOMMetadata) -> None:
        """Visit year."""
        self.year = value
        record.set_datetime(value)

    def visit_semester(self, value: str, record: LOMMetadata) -> None:
        """Visit semester."""
        self.semester = value
        record.append_keyword(value, language_code="x-none")

    def visit_coursename(self, value: str, _: LOMMetadata) -> None:
        """Visit coursename."""
        self.course_name = value

    def visit_courselanguage(self, value: str, record: LOMMetadata) -> None:
        """Visit courselanguage."""
        record.append_language(value)

    def visit_description(self, value: str, record: LOMMetadata) -> None:
        """Visit description."""
        record.append_description(value, language_code="x-none")

    def visit_lecturer(self, value: str, record: LOMMetadata) -> None:
        """Visit lecturer."""
        for lecturer in value.split(","):
            record.append_contribute(lecturer.strip(), role="Author")

    def visit_organisation(self, value: str, record: LOMMetadata) -> None:
        """Visit organisation."""
        record.append_contribute(value, role="Unknown")

    def visit_objective(self, value: str, record: LOMMetadata) -> None:
        """Visit objective."""
        record.append_educational_description(value, language_code="x-none")


class MoodleFileToLOMFile(Visitor):
    """Moodle file to lom file."""

    def visit(self, value: str, record: LOMMetadata) -> None:
        """Visit."""
        super().visit(value, record)

        record.set_title(self.title, language_code=self.language)

        for tag in filter(bool, self.tags):
            record.append_keyword(tag, language_code=self.language)

        if abstract := unescape(self.abstract):
            record.append_description(abstract, language_code=self.language)

    def visit_language(self, value: str, record: LOMMetadata) -> None:
        """Visit language."""
        self.language = value
        record.append_language(value)

    def visit_title(self, value: str, _: LOMMetadata) -> None:
        """Visit title."""
        self.title = value

    def visit_abstract(self, value: str, _: LOMMetadata) -> None:
        """Visit abstract."""
        self.abstract = value

    def visit_tags(self, value: str, _: LOMMetadata) -> None:
        """Visit tags."""
        self.tags = value

    def visit_persons(self, value: str, record: LOMMetadata) -> None:
        """Visit persons."""
        for person in value:
            name = f"{person['firstname']} {person['lastname']}"
            record.append_contribute(name, role=person["role"])

    def visit_timereleased(self, value: str, record: LOMMetadata) -> None:
        """Visit timereleased."""
        datetime_obj = datetime.fromtimestamp(value)
        datetime_isoformat = datetime_obj.date().isoformat()
        record.set_datetime(datetime_isoformat)

    def visit_mimetype(self, value: str, record: LOMMetadata) -> None:
        """Visit mimetype."""
        record.append_format(value)

    def visit_filesize(self, value: str, record: LOMMetadata) -> None:
        """Visit filesize."""
        record.set_size(value)

    def visit_resourcetype(self, value: str, record: LOMMetadata) -> None:
        """Visit resourcetype."""
        # https://skohub.io/dini-ag-kim/hcrt/heads/master/w3id.org/kim/hcrt/slide.en.html
        learningresourcetype_by_resourcetype = {
            "No selection": None,
            "Presentationslide": "slide",
            "Exercise": "assessment",
        }
        if learningresourcetype := learningresourcetype_by_resourcetype[value]:
            record.append_learningresourcetype(learningresourcetype)

    def visit_license(self, value: str, record: LOMMetadata) -> None:
        """Visit license."""
        record.set_rights_url(value["source"])

    def visit_classification(self, classifications: str, record: LOMMetadata) -> None:
        """Visit classification."""
        oefos_ids = [
            value["identifier"]
            for classification in classifications
            for value in classification["values"]
        ]

        # reorder to ['1234', '123', '2345', '234', '2']
        oefos_ids.sort(key=lambda id_: id_.ljust(6, chr(255)))

        # metadata.append_oefos(oefos_ids) # noqa: ERA001
        for id_ in oefos_ids:
            record.append_oefos_id(id_)
            record.append_oefos_id(id_, "en")


def convert_course_metadata(
    moodle_course_metadata: dict,
    moodle_file_metadata: dict,
) -> LOMMetadata:
    """Create metadata of the course.

    it seams not necessary to have the course_metadata explicitly here, but
    there are multiple courses which course does this file belong to?
    """
    metadata = LOMMetadata(overwritable=True)

    visitor = MoodleFileToLOMFile()
    visitor.visit(moodle_file_metadata, metadata)
    visitor.visit(moodle_course_metadata, metadata)

    return metadata


def convert_unit_metadata(
    moodle_course_metadata: dict,
    moodle_file_metadata: dict,
) -> LOMMetadata:
    """Create metadata of an unit."""
    metadata = LOMMetadata(overwritable=True)

    visitor = MoodleFileToLOMFile()
    visitor.visit(moodle_file_metadata, metadata)
    visitor.visit(moodle_course_metadata, metadata)

    return metadata


def convert_file_metadata(moodle_file_metadata: dict) -> LOMMetadata:
    """Convert file metadata."""
    metadata = LOMMetadata(overwritable=True)

    visitor = MoodleFileToLOMFile()
    visitor.visit(moodle_file_metadata, metadata)

    return metadata
