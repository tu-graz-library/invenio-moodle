# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Command-line interface for `invenio_moodle`."""

from click import STRING, group, option, secho
from click_params import URL
from flask import current_app
from flask.cli import with_appcontext
from invenio_access.utils import get_identity
from invenio_accounts import current_accounts

from .services import MoodleRESTService, build_service
from .types import Color


@group()
def moodle() -> None:
    """invenio-moodle commands."""


@moodle.command()
@option("--endpoint", type=URL, required=True)
@option("--user-email", type=STRING, required=True)
@option("--dry-run", is_flag=True, default=False)
@build_service
@with_appcontext
def import_by_endpoint(
    moodle_service: MoodleRESTService,
    user_email: str,
    *,
    dry_run: bool,
) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    import_func = current_app.config.get("MOODLE_REPOSITORY_IMPORT_FUNC")

    user = current_accounts.datastore.get_user_by_email(user_email)
    identity = get_identity(user)

    try:
        records = moodle_service.fetch_records(identity)
    except RuntimeError as error:
        secho(str(error), fg=Color.error)
        return

    for moodle_record in records:
        try:
            import_func(identity, moodle_record, moodle_service, dry_run=dry_run)
        except RuntimeError as error:
            secho(error, fg=Color.error)
