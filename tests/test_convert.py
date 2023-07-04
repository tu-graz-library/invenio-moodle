# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test convert."""

from invenio_moodle.convert import convert_moodle_to_lom


def test_convert_moodle_to_lom(
    minimal_record: dict,
    expected_lom_metadata: dict,
) -> None:
    """Test convert_unit_metadata."""
    metadata = convert_moodle_to_lom(minimal_record)

    assert metadata.json == expected_lom_metadata
