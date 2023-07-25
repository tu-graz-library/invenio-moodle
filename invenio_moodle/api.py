# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Api functions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from requests import get
from sqlalchemy.orm.exc import NoResultFound

from .schemas import MoodleSchema
from .utils import (
    build_intermediate_records,
    extract_moodle_records,
    import_record,
    post_processing,
)

if TYPE_CHECKING:
    from flask_principal import Identity
    from invenio_records_lom.utils import LOMRecordService


def fetch_moodle(
    moodle_fetch_url: str,
    record_service: LOMRecordService,
    identity: Identity,
) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    response = get(moodle_fetch_url, timeout=15)
    response.raise_for_status()

    moodle_data = response.json()

    insert_moodle_into_db(moodle_data, record_service, identity)


def insert_moodle_into_db(
    moodle_data: dict,
    records_service: LOMRecordService,
    identity: Identity,
) -> None:
    """Insert data encoded in `moodle-data` into invenio-database.

    :param dict moodle_data: The data to be inserted into database,
        whose format matches `MoodleSchema`
    :param dict filepaths_by_url: A dictionary
        that maps some file-urls within `moodle_data` to filepaths.
        When a file-url is found in `filepaths_by_url`,
        the file on the corresponding filepath is used.
        Otherwise the file is downloaded from file-url.
    """
    # validate input
    moodle_data = MoodleSchema().load(moodle_data)

    moodle_records = extract_moodle_records(moodle_data)
    post_processing(moodle_records)

    records = build_intermediate_records(moodle_records, records_service, identity)

    for record in records.values():
        try:
            import_record(record, records_service, identity)
        except NoResultFound:  # noqa: PERF203
            continue
