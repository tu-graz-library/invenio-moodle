# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Jobs."""


from invenio_jobs.jobs import JobType, PredefinedArgsSchema
from invenio_jobs.models import Job
from marshmallow.fields import String

from .tasks import import_records


class MoodlePredefinedArgsSchema(PredefinedArgsSchema):
    """Moodle predefined args schema."""

    dry_run = String(
        metadata={
            "description": "bool value to describe dry run",
        },
    )


class ImportMoodleRecordsJob(JobType):
    """Import moodle records."""

    id = "import_moodle_records"
    title = "Import Moodle Records"
    description = "Import moodle records."

    task = import_records

    arguments_schema = MoodlePredefinedArgsSchema

    @classmethod
    def build_task_arguments(
        cls,
        job_obj: Job,  # noqa: ARG003
        dry_run: str | None = None,
        **__: dict,
    ) -> dict[str, bool]:
        """Define extra arguments to be injected on task execution."""
        parsed_dry_run = dry_run in ["true", "True", 1, "1", "t", "T"]
        return {"dry_run": parsed_dry_run}
