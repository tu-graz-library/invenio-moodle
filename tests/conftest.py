# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
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
from flask import Flask

from invenio_moodle import InvenioMoodle


@pytest.fixture(scope="module")
def create_app(instance_path: str) -> Callable:
    """Application factory fixture."""

    def factory(**config: dict) -> Flask:
        app = Flask("testapp", instance_path=instance_path)
        app.config.update(**config)
        InvenioMoodle(app)
        return app

    return factory


@pytest.fixture(scope="module")
def minimal_record() -> dict:
    """Create minimal record."""
    filename = Path("data/minimal_record.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)


@pytest.fixture()
def expected_course() -> dict:
    """Fixture expected_course."""
    filename = Path("data/expected_course.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)


@pytest.fixture()
def expected_unit() -> None:
    """Expectd unit."""
    filename = Path("data/expected_unit.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)


@pytest.fixture()
def expected_file() -> None:
    """Expectd unit."""
    filename = Path("data/expected_file.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)
