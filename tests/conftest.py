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
from invenio_i18n import InvenioI18N

from invenio_moodle import InvenioMoodle


@pytest.fixture(scope="module")
def create_app(instance_path: str) -> Callable:
    """Application factory fixture."""

    def factory(**config: dict) -> Flask:
        app = Flask("testapp", instance_path=instance_path)
        app.config.update(**config)
        InvenioI18N(app)
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
def expected_lom_metadata() -> None:
    """Expectd unit."""
    filename = Path("data/lom_metadata.json")
    directory = Path(__file__).parent
    filepath = directory / filename
    with filepath.open("r") as fp:
        return load(fp)
