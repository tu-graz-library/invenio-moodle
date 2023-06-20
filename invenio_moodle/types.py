# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Types."""

from __future__ import annotations

import typing as t
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from dataclasses import dataclass
from functools import singledispatchmethod
from pathlib import Path

if t.TYPE_CHECKING:
    from invenio_records_lom import LOMMetadata


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

    @singledispatchmethod
    def __init__(self, url: str, year: str, semester: str, hash_md5: str) -> None:
        """Construct."""
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "year", year)
        object.__setattr__(self, "semester", semester)
        object.__setattr__(self, "hash_md5", hash_md5)

    @__init__.register
    def _(
        self,
        moodle_file_metadata: dict,
        file_cache: dict[str, FileCacheInfo],
    ) -> FileKey:
        """Create `cls` via info from moodle-json and file-cache."""
        url = moodle_file_metadata["fileurl"]
        year = moodle_file_metadata["year"]
        semester = moodle_file_metadata["semester"]
        hash_md5 = file_cache[url].hash_md5
        return self.__init__(url=url, year=year, semester=semester, hash_md5=hash_md5)

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

    @singledispatchmethod
    def __init__(self, courseid: str, year: str, semester: str) -> None:
        """Construct UnitKey."""
        object.__setattr__(self, "courseid", courseid)
        object.__setattr__(self, "year", year)
        object.__setattr__(self, "semester", semester)

    @__init__.register
    def _(self, moodle_file_json: dict, moodle_course_json: dict) -> None:
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_json["courseid"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        return self.__init__(courseid=courseid, year=year, semester=semester)

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

    @singledispatchmethod
    def __init__(self, courseid: str) -> None:
        """Construct CourseKey."""
        object.__setattr__(self, "courseid", courseid)

    @__init__.register
    def _(self, moodle_course_metadata: dict) -> None:
        """Create `cls` via info from moodle-json."""
        courseid = moodle_course_metadata["courseid"]
        return self.__init__(courseid=courseid)

    def __str__(self) -> str:
        """Get string-representation."""
        course_id = f"courseid={self.courseid}"
        return f"CourseKey({course_id})"


@dataclass
class Task:
    """Stores data."""

    key: Key
    pid: str
    previous_metadata: dict
    metadata: LOMMetadata
    moodle_file_metadata: dict = None
    moodle_course_metadata: dict = None

    def update_metadata(self, metadata: LOMMetadata) -> None:
        """Set metadata."""
        self.metadata = metadata


class Tasks(list):
    """List of tasks."""

    def __getitem__(self, key: Key) -> Task | None:
        """Return the task by key."""
        for task in self:
            if task.key == key:
                return task
        return None

    def __contains__(self, task: Task) -> bool:
        """Return true if task exists already."""
        return any(task.key == t.key for t in self)

    def filter_by(self, key: Key) -> Generator[Task, None, None]:
        """Filter tasks by func."""
        for task in self:
            if isinstance(task.key, key):
                yield task


@dataclass(frozen=True)
class Link:
    """Represents a link between records."""

    key: Key
    kind: str
    value: str


FileCache = dict[str, FileCacheInfo]
Links = set[Link]
