# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Jobs."""


from invenio_jobs.jobs import JobType

from .tasks import import_records


class ImportMoodleRecordsJob(JobType):
    """Import moodle records."""

    id = "import_moodle_records"
    title = "Import Moodle Records"
    description = "Import moodle records."

    task = import_records
