# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for `invenio-moodle`."""

import traceback

from celery import shared_task
from flask import current_app
from flask_mail import Message

from .api import fetch_moodle


@shared_task(ignore_result=True)
def try_fetch_moodle_except_mail() -> None:
    """Fetch data from moodle and enter it into database."""
    try:
        moodle_fetch_url = current_app.config["MOODLE_FETCH_URL"]
        fetch_moodle(moodle_fetch_url)

    except Exception:  # noqa: BLE001
        config = current_app.config
        msg = Message(
            "Something went wrong when fetching data from moodle",
            sender=config["MOODLE_ERROR_MAIL_SENDER"],
            recipients=config["MOODLE_ERROR_MAIL_RECIPIENTS"],
            body=traceback.format_exc(),
        )
        current_app.extensions["mail"].send(msg)
