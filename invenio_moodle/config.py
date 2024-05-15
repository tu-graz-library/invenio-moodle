# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Default configuration for invenio-moodle."""

import sys

import click

MOODLE_CELERY_BEAT_SCHEDULE = {}
"""The celery beat schedule.

This variable is used to configure the celery task which is used to import data
from moodle on a regularly basis.
"""


MOODLE_ENDPOINT = ""
"""The url of the moodle endpoint from where should be fetched the metadata."""


def default_import_func(*_: dict, **__: dict) -> None:
    """Define the default import func."""
    click.secho("Please set the variable MOODLE_REPOSITORY_IMPORT_FUNC", fg="yellow")
    sys.exit()


MOODLE_REPOSITORY_IMPORT_FUNC = default_import_func
