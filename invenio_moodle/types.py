# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Color:
    """The class is for the output color management."""

    neutral = "white"
    error = "red"
    warning = "yellow"
    abort = "magenta"
    success = "green"
    alternate = ("blue", "cyan")


@dataclass(frozen=True)
class FileCacheInfo:
    """Holds a file-path and the file's md5-hash."""

    hash_md5: str
    path: Path


@dataclass(frozen=True)
class Key(ABC):
    """Common ancestor to all Key classes."""

    @property
    @abstractmethod
    def resource_type(self) -> str:
        """The resource_type associated to the key, one of `LOM_RESOURCE_TYPES`."""

    @abstractmethod
    def __str__(self) -> str:
        """Convert `self` to unique string representation."""


@dataclass(frozen=True)
class FileKey(Key):
    """Key for files as to disambiguate it from keys for units and courses."""

    url: str
    year: str
    semester: str
    hash_md5: str

    resource_type = "file"

    @classmethod
    def from_json_and_cache(
        cls,
        moodle_file_json: str,
        file_cache: dict[str, FileCacheInfo],
    ) -> FileKey:
        """Create `cls` via info from moodle-json and file-cache."""
        url = moodle_file_json["fileurl"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        hash_md5 = file_cache[url].hash_md5
        return cls(url=url, year=year, semester=semester, hash_md5=hash_md5)

    def __str__(self) -> str:
        """Get string-representation."""
        url = f"url={self.url}"
        year = f"year={self.year}"
        semester = f"semester={self.semester}"
        hash_md5 = f"hash_md5={self.hash_md5}"
        return f"FileKey({url}, {year}, {semester}, {hash_md5})"


@dataclass(frozen=True)
class UnitKey(Key):
    """Key for units as to disambiguate it from keys for files and courses."""

    courseid: str
    year: str
    semester: str

    resource_type = "unit"

    @classmethod
    def from_json(cls, moodle_file_json: dict, moodle_course_json: dict) -> UnitKey:
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_json["courseid"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        return cls(courseid=courseid, year=year, semester=semester)

    def __str__(self) -> str:
        """Get string-representation."""
        course_id = f"courseid={self.courseid}"
        year = f"year={self.year}"
        semester = f"semester={self.semester}"
        return f"UnitKey({course_id}, {year}, {semester})"


@dataclass(frozen=True)
class CourseKey(Key):
    """Key for courses as to disambiguate it from keys for files and units."""

    courseid: str

    resource_type = "course"

    @classmethod
    def from_json(cls, moodle_course_json: dict) -> CourseKey:
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_json["courseid"]
        return cls(courseid=courseid)

    def __str__(self) -> str:
        """Get string-representation."""
        course_id = f"courseid={self.courseid}"
        return f"CourseKey({course_id})"


@dataclass
class TaskLog:
    """Stores data."""

    pid: str
    previous_json: dict
    json: dict
    moodle_file_json: dict = None
    moodle_course_json: dict = None


@dataclass(frozen=True)
class Link:
    """Represents a link between records."""

    key: Key
    kind: str
    value: str


TaskLogs = dict[Key, TaskLog]
FileCache = dict[str, FileCacheInfo]
Links = set[Link]
FilePaths = dict[str, Path]
