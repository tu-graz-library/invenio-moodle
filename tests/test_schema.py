# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test convert."""

from invenio_moodle.schemas import MoodleSchema


def test_simple(minimal_record: dict) -> None:
    """Test Simple."""
    errors = MoodleSchema().validate(
        {
            "applicationprofile": "1.0",
            "moodlecourses": {
                "1": {
                    "files": [minimal_record],
                },
            },
        },
    )

    assert errors == {}
