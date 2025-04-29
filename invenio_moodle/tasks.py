# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for `invenio-moodle`."""


from celery import shared_task
from flask import current_app
from invenio_access.permissions import system_identity

from .proxies import current_moodle


@shared_task(ignore_result=True)
def try_fetch_moodle_except_mail() -> None:
    """Fetch data from moodle and enter it into database."""
    import_func = current_app.config["MOODLE_IMPORT_FUNC"]
    moodle_service = current_moodle.moodle_rest_service

    records = moodle_service.fetch_records(system_identity)

    for record in records:
        try:
            import_func(system_identity, record, moodle_service)
        except RuntimeError as error:
            msg = "ERROR moodle import error: %s"
            current_app.logger.error(msg, str(error))
