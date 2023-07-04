# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Command-line interface for `invenio_moodle`."""

from click import STRING, group, option, secho
from click_params import URL
from flask.cli import with_appcontext
from invenio_config_tugraz import get_identity_from_user_by_email
from invenio_records_lom.proxies import current_records_lom
from marshmallow import ValidationError

from .api import fetch_moodle
from .types import Color


@group()
def moodle() -> None:
    """invenio-moodle commands."""


@moodle.command()
@option("--endpoint", type=URL, required=True)
@option("--user-email", type=STRING, required=True)
@with_appcontext
def import_by_endpoint(endpoint: str, user_email: str) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    identity = get_identity_from_user_by_email(email=user_email)
    records_service = current_records_lom.records_service

    try:
        fetch_moodle(endpoint, records_service, identity)
    except ValidationError as error:
        secho(error, fg=Color.error)
