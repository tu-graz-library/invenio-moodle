# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test types."""
from invenio_records_lom.utils import LOMMetadata

from invenio_moodle.types import (
    CourseKey,
    CourseRecord,
    FileKey,
    FileRecord,
    UnitKey,
    UnitRecord,
)


def test_filekey(minimal_record: dict) -> None:
    """Test FileKey."""
    file_key = FileKey("https://url", "2021", "WS", "a3died")

    assert file_key.get_moodle_pid_value() == "a3died"
    assert (
        str(file_key)
        == "FileKey(url=https://url, year=2021, semester=WS, hash_md5=a3died)"
    )

    file_key = FileKey(minimal_record)
    content_hash = "f234b1feaf60f1fb63ba5cb4be24bd7a60d806e1"

    assert file_key.get_moodle_pid_value() == content_hash
    assert (
        str(file_key)
        == f"FileKey(url=https://path/to/file, year=2023, semester=SS, hash_md5={content_hash})"  # noqa: E501
    )


def test_unitkey(minimal_record: dict) -> None:
    """Test UnitKey."""
    unit_key = UnitKey("38dkede", "2023", "WS")

    assert unit_key.get_moodle_pid_value() == "38dkede-2023-WS"
    assert str(unit_key) == "UnitKey(course_id=38dkede, year=2023, semester=WS)"

    unit_key = UnitKey(minimal_record, minimal_record["courses"][0])

    assert unit_key.get_moodle_pid_value() == "240587-2023-SS"
    assert str(unit_key) == "UnitKey(course_id=240587, year=2023, semester=SS)"


def test_coursekey(minimal_record: dict) -> None:
    """Test CourseKey."""
    course_key = CourseKey("38dkede")

    assert course_key.get_moodle_pid_value() == "38dkede"
    assert str(course_key) == "CourseKey(course_id=38dkede)"

    course_key = CourseKey(minimal_record["courses"][0])

    assert course_key.get_moodle_pid_value() == "240587"
    assert str(course_key) == "CourseKey(course_id=240587)"


def test_filerecord() -> None:
    """Test FileRecord."""
    lom_metadata = LOMMetadata()
    file_key = FileKey("https://url", "2021", "WS", "a3died")
    file_record = FileRecord(file_key, lom_metadata, "fileurl")

    lom_metadata_unit = LOMMetadata()
    unit_key = UnitKey("38dkede", "2023", "WS")
    unit_record = UnitRecord(unit_key, lom_metadata_unit)

    file_record.construct_up_links([unit_record])

    expected = {
        "metadata": {
            "relation": [
                {
                    "kind": {
                        "source": {
                            "langstring": {"#text": "LOMv1.0", "lang": "x-none"},
                        },
                        "value": {
                            "langstring": {"#text": "ispartof", "lang": "x-none"},
                        },
                    },
                    "resource": {
                        "identifier": [
                            {
                                "catalog": "repo-pid",
                                "entry": {
                                    "langstring": {
                                        "#text": "38dkede-2023-WS",
                                        "lang": "x-none",
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
    }
    assert file_record.metadata.json == expected


def test_unitrecord() -> None:
    """Test UnitRecord."""
    lom_metadata_file = LOMMetadata()
    file_key = FileKey("https://url", "2021", "WS", "a3died")
    file_record = FileRecord(file_key, lom_metadata_file, "fileurl")

    lom_metadata_unit = LOMMetadata()
    unit_key = UnitKey("38dkede", "2023", "WS")
    unit_record = UnitRecord(unit_key, lom_metadata_unit)

    lom_metadata_course = LOMMetadata()
    course_key = CourseKey("38dkede")
    course_record = CourseRecord(course_key, lom_metadata_course)

    unit_record.construct_down_links([file_record])
    unit_record.construct_up_links([course_record])

    expected = {
        "metadata": {
            "relation": [
                {
                    "kind": {
                        "source": {
                            "langstring": {"#text": "LOMv1.0", "lang": "x-none"},
                        },
                        "value": {
                            "langstring": {"#text": "haspart", "lang": "x-none"},
                        },
                    },
                    "resource": {
                        "identifier": [
                            {
                                "catalog": "repo-pid",
                                "entry": {
                                    "langstring": {
                                        "#text": "a3died",
                                        "lang": "x-none",
                                    },
                                },
                            },
                        ],
                    },
                },
                {
                    "kind": {
                        "source": {
                            "langstring": {"#text": "LOMv1.0", "lang": "x-none"},
                        },
                        "value": {
                            "langstring": {"#text": "ispartof", "lang": "x-none"},
                        },
                    },
                    "resource": {
                        "identifier": [
                            {
                                "catalog": "repo-pid",
                                "entry": {
                                    "langstring": {
                                        "#text": "38dkede",
                                        "lang": "x-none",
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
    }

    assert unit_record.metadata.json == expected


def test_courserecord() -> None:
    """Test CourseRecord."""
    lom_metadata_unit = LOMMetadata()
    unit_key = UnitKey("38dkede", "2023", "WS")
    unit_record = UnitRecord(unit_key, lom_metadata_unit)

    lom_metadata_course = LOMMetadata()
    course_key = CourseKey("38dkede")
    course_record = CourseRecord(course_key, lom_metadata_course)

    course_record.construct_down_links([unit_record])

    expected = {
        "metadata": {
            "relation": [
                {
                    "kind": {
                        "source": {
                            "langstring": {"#text": "LOMv1.0", "lang": "x-none"},
                        },
                        "value": {
                            "langstring": {"#text": "haspart", "lang": "x-none"},
                        },
                    },
                    "resource": {
                        "identifier": [
                            {
                                "catalog": "repo-pid",
                                "entry": {
                                    "langstring": {
                                        "#text": "38dkede-2023-WS",
                                        "lang": "x-none",
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
    }

    assert course_record.metadata.json == expected
