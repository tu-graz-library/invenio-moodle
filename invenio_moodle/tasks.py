# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Celery tasks for `invenio-moodle`."""


from celery import shared_task
from flask import current_app
from invenio_access.permissions import system_identity

from .proxies import current_moodle


@shared_task(ignore_result=True)
def import_records() -> None:
    """Fetch data from moodle and enter it into database."""
    import_func = current_app.config["MOODLE_REPOSITORY_IMPORT_FUNC"]
    moodle_service = current_moodle.moodle_rest_service

    current_app.logger.info("Start importing records from moodle.")

    moodle_records = moodle_service.fetch_records(system_identity)

    for moodle_record in moodle_records:
        try:
            record = import_func(system_identity, moodle_record, moodle_service)
            msg = "Moodle record: %s imported successfully."
            current_app.logger.info(msg, str(record.pid))
        except RuntimeError as error:
            msg = "Moodle import error: %s."
            current_app.logger.error(msg, str(error))
