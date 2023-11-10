# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Default configuration for invenio-moodle."""

from invenio_i18n import gettext as _
from invenio_rdm_records.services.pids.providers import ExternalPIDProvider

MOODLE_CELERY_BEAT_SCHEDULE = {}
"""The celery beat schedule.

This variable is used to configure the celery task which is used to import data
from moodle on a regularly basis.
"""

MOODLE_PERSISTENT_IDENTIFIER_PROVIDERS = [
    ExternalPIDProvider("moodle", "moodle", label=_("MOODLE ID")),
]
"""List of persistent identifier providers.

The values are added to the LOM_PERSISTENT_IDENTIFIER_PROVIDERS list.
"""

MOODLE_PERSISTENT_IDENTIFIERS = {
    "moodle": {
        "providers": ["moodle"],
        "required": False,
        "label": _("MOODLE"),
    },
}
"""Dict of persistent identifiers.

The values are added to the LOM_PERSISTENT_IDENTIFIERS dict.
"""

MOODLE_FETCH_URL = ""
"""The url of the moodle endpoint from where should be fetched the metadata."""

MOODLE_ERROR_MAIL_SENDER = ""
"""The variable is used to configure the sender of the error emails."""

MOODLE_ERROR_MAIL_RECIPIENTS = []
"""The variable is used to configure the list of recipients of the error emails."""
