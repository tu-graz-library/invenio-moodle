# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Module test types."""

from invenio_moodle.types import FileKey


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
