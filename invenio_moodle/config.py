# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Default configuration for invenio-moodle."""

from flask_babelex import gettext as _
from invenio_rdm_records.services.pids import providers

MOODLE_CELERY_BEAT_SCHEDULE = {}

MOODLE_PERSISTENT_IDENTIFIER_PROVIDERS = [
    providers.ExternalPIDProvider("moodle", "moodle", label=_("MOODLE ID")),
]

MOODLE_PERSISTENT_IDENTIFIERS = {
    "moodle": {
        "providers": ["moodle"],
        "required": False,
        "label": _("MOODLE"),
    },
}

MOODLE_FETCH_URL = ""

MOODLE_ERROR_MAIL_SENDER = ""
MOODLE_ERROR_MAIL_RECIPIENTS = []
