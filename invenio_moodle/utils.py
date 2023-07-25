# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for inserting moodle-data into invenio-style database."""

from __future__ import annotations

from typing import TYPE_CHECKING

from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PersistentIdentifier
from invenio_records_lom.utils import LOMMetadata

from .convert import convert_moodle_to_lom
from .files import add_file_to_draft
from .types import BaseRecord, FileKey, FileRecord, LinkKey, LinkRecord, Status

if TYPE_CHECKING:
    from flask_principal import Identity
    from invenio_records_lom import LOMRecordService
    from invenio_records_resources.services.records import RecordItem

    from .types import Key


def is_not_moodle_only_course(moodle_course_metadata: dict) -> bool:
    """Check if it is a moodle only course."""
    return moodle_course_metadata["courseid"] != "0"


def is_course_root(sourceid: str) -> bool:
    """Check if parent exists."""
    return sourceid == "-1"


def extract_moodle_records(moodle_data: dict) -> list[dict]:
    """Create moodle file jsons."""
    return [
        file_json
        for _, moodle_course in moodle_data["moodlecourses"].items()
        for file_json in moodle_course["files"]
    ]


def create_draft(
    key: Key,
    moodle_pid_value: str,
    records_service: LOMRecordService,
    identity: Identity,
) -> RecordItem:
    """Create draft with empty metadata."""
    pids_dict = {
        "moodle": {
            "provider": "moodle",
            "identifier": moodle_pid_value,
        },
    }
    metadata = LOMMetadata.create(resource_type=key.resource_type, pids=pids_dict)
    metadata.append_identifier(moodle_pid_value, catalog="moodle")
    return records_service.create(data=metadata.json, identity=identity)


def get_from_database_or_create(
    key: Key,
    records_service: LOMRecordService,
    identity: Identity,
) -> BaseRecord:
    """Fetch moodle-result corresponding to `key`, create database-entry if none exists.

    :param Key key: the key which to attempt fetching from pidstore


    File:
    A File could be already in database. A File should not be added twice and it
    is looked up by its file hash (hash_md5). If it is there already it will be
    linked to the new Unit where it is used.

    Unit:
    An Unit will ever be created from scratch. They are unique and created every
    year new

    Course:
    A Course could be new, but it is usually not. A Course only changes if a new
    curriculum will be defined.
    """
    moodle_pid_value = key.get_moodle_pid_value()

    try:
        moodle_pid = PersistentIdentifier.get(
            pid_type="moodle",
            pid_value=moodle_pid_value,
        )
    except PIDDoesNotExistError:
        draft = create_draft(key, moodle_pid_value, records_service, identity)
        pid: str = draft.id
        lom_metadata = LOMMetadata(draft.to_dict(), overwritable=True)
        status = Status.NEW
    else:
        # get lomid corresponding to moodle_pid
        lom_pid = PersistentIdentifier.get_by_object(
            pid_type="lomid",
            object_type=moodle_pid.object_type,
            object_uuid=moodle_pid.object_uuid,
        )

        pid: str = lom_pid.pid_value
        metadata = records_service.edit(id_=pid, identity=identity).to_dict()
        lom_metadata = LOMMetadata(metadata, overwritable=True)
        status = Status.EDIT

    if isinstance(key, FileKey):
        type_of_record = FileRecord
    elif isinstance(key, LinkKey):
        type_of_record = LinkRecord
    else:
        type_of_record = BaseRecord

    return type_of_record(key, pid, lom_metadata, status)


def build_intermediate_records(
    moodle_records: list[dict],
    records_service: LOMRecordService,
    identity: Identity,
) -> dict[Key, BaseRecord]:
    """Build course tree.

    :param dict moodle_data: Data whose format matches `MoodleSchema`
    """
    records = {}

    # prepare: gather necessary information, create records if no
    # previous versions exist
    for moodle_file_metadata in moodle_records:
        file_key = FileKey(moodle_file_metadata)
        file_record = get_from_database_or_create(file_key, records_service, identity)
        convert_moodle_to_lom(moodle_file_metadata, file_record.metadata)
        records[file_key] = file_record

    return records


def import_record(
    record: BaseRecord,
    records_service: LOMRecordService,
    identity: Identity,
) -> None:
    """Import Record."""
    if isinstance(record, FileRecord) and record.status == Status.NEW:
        add_file_to_draft(record, records_service.draft_files, identity)

    records_service.update_draft(
        id_=record.pid,
        data=record.json,
        identity=identity,
    )
    records_service.publish(id_=record.pid, identity=identity)


def remove_moodle_only_course(moodle_records: dict) -> None:
    """Remove moodle only course.

    This is indicated by the courseid == 0
    """
    for moodle_file_metadata in moodle_records:
        not_moodle_only_courses = list(
            filter(is_not_moodle_only_course, moodle_file_metadata["courses"]),
        )
        moodle_file_metadata["courses"] = not_moodle_only_courses


def post_processing(moodle_records: dict) -> dict:
    """Post process moodle data.

    Remove unwanted fields:
        - remove course with courseid == 0
    """
    remove_moodle_only_course(moodle_records)
