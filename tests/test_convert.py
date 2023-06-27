# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test convert."""

from invenio_moodle.convert import (
    convert_course_metadata,
    convert_file_metadata,
    convert_unit_metadata,
)


def test_convert_course_metadata(minimal_record: dict, expected_course: dict) -> None:
    """Test convert_course_metadata."""
    metadata = convert_course_metadata(minimal_record["courses"][0], minimal_record)
    assert metadata.json == expected_course


def test_convert_unit_metdata(minimal_record: dict, expected_unit: dict) -> None:
    """Test convert_unit_metadata."""
    metadata = convert_unit_metadata(minimal_record["courses"][0], minimal_record)
    assert metadata.json == expected_unit


def test_convert_file_metdata(minimal_record: dict, expected_file: dict) -> None:
    """Test convert_unit_metadata."""
    metadata = convert_file_metadata(minimal_record)
    assert metadata.json == expected_file
