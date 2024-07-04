# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for inserting moodle-data into invenio-style database."""


def is_not_moodle_only_course(moodle_course_metadata: dict) -> bool:
    """Check if it is a moodle only course."""
    return moodle_course_metadata["courseid"] != "0"


def is_course_root(sourceid: str) -> bool:
    """Check if parent exists."""
    return sourceid == "-1"


def extract_moodle_records(moodle_data: dict) -> list[dict]:
    """Create moodle file jsons.

    application profile 2.0
    {
      "elements": [
        {METADATA goes here}
      ]
    }

    application profile 1.0
    {
      "moodlecourses":{
        "1": {
           "files OR elements":[
             {METADATA goes here}
         ]
    }
    """
    # application profile 2.0 uses elements and a flat structure to serve the metadata.
    if "elements" in moodle_data:
        return moodle_data["elements"]

    # application profile 1.0 uses a nested structure with
    elements = []
    for moodle_course in moodle_data["moodlecourses"].values():
        if "files" in moodle_course:
            elements.extend(file_json for file_json in moodle_course["files"])
        if "elements" in moodle_course:
            elements.extend(file_json for file_json in moodle_course["elements"])
    return elements


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
