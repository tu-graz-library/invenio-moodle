# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Api functions."""

from requests import get

from .utils import insert_moodle_into_db


def fetch_moodle(moodle_fetch_url: str) -> None:
    """Fetch data from MOODLE_FETCH_URL and insert it into the database."""
    response = get(moodle_fetch_url, timeout=10)
    response.raise_for_status()

    moodle_data = response.json()

    insert_moodle_into_db(moodle_data)
