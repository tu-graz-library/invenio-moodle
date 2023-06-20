# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Command-line interface for `invenio_moodle`."""

import click
from click_params import URL
from flask.cli import with_appcontext

from .api import fetch_moodle
from .click_param_types import JSON


@click.group()
def moodle() -> None:
    """invenio-moodle commands."""


@moodle.command()
@click.option("--endpoint", type=URL, required=True)
@with_appcontext
def import_by_endpoint(endpoint: str = None) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    fetch_moodle(endpoint)
