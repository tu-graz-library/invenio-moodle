# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Command-line interface for `invenio_moodle`."""

import click
from click_params import URL
from flask import current_app
from flask.cli import with_appcontext

from .utils import fetch_moodle


@click.group()
def moodle():
    """invenio-moodle commands."""


@moodle.command()
@with_appcontext
@click.option("--moodle-fetch-url", type=URL)
def fetch(moodle_fetch_url: str = None):
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    if not moodle_fetch_url:
        moodle_fetch_url = current_app.config["MOODLE_FETCH_URL"]

    fetch_moodle(moodle_fetch_url)
