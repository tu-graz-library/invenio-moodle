# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test convert."""

from invenio_moodle.schemas import MoodleSchemaApplicationProfile1


def test_simple(minimal_record: dict) -> None:
    """Test Simple."""
    errors = MoodleSchemaApplicationProfile1().validate(
        {
            "applicationprofile": "2.0",
            "moodlecourses": {
                "1": {
                    "elements": [minimal_record],
                },
            },
        },
    )

    assert errors == {}
