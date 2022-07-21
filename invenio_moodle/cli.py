# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Command-line interface for `invenio_moodle`."""

import click
from flask.cli import with_appcontext

from .utils import fetch_moodle


@click.group()
def moodle():
    """invenio-moodle commands."""


@moodle.command()
@with_appcontext
def fetch():
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    fetch_moodle()
