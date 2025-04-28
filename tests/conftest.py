# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

from collections.abc import Callable
from json import load
from pathlib import Path

import pytest
from _pytest.fixtures import FixtureFunctionMarker
from invenio_app.factory import create_api as _create_api


@pytest.fixture(scope="module")
def create_app(instance_path: FixtureFunctionMarker) -> Callable:
    """Application factory fixture."""
    return _create_api


@pytest.fixture(scope="module")
def minimal_record() -> dict:
    """Create minimal record."""
    filename = Path("data/minimal_record.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)


@pytest.fixture
def expected_lom_metadata() -> None:
    """Expectd unit."""
    filename = Path("data/lom_metadata.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)
