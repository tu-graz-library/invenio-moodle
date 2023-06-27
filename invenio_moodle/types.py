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
from functools import singledispatchmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

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

    def __hash__(self) -> str:
        """Get hash."""
        return self.get_moodle_pid_value()

    @abstractmethod
    def get_moodle_pid_value(self) -> str:
        """Return the primary hash of Key."""


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
        # dataclass frozen is nice but needs following not handy construct
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "year", year)
        object.__setattr__(self, "semester", semester)
        object.__setattr__(self, "hash_md5", hash_md5)

    @__init__.register
    def _(
        self,
        moodle_file_metadata: dict,
    ) -> None:
        """Create `cls` via info from moodle-json and file-cache."""
        url = moodle_file_metadata["fileurl"]
        year = moodle_file_metadata["year"]
        semester = moodle_file_metadata["semester"]
        hash_md5 = moodle_file_metadata["contenthash"]
        self.__init__(url, year, semester, hash_md5)

    def __str__(self) -> str:
        """Get string-representation."""
        url = f"url={self.url}"
        year = f"year={self.year}"
        semester = f"semester={self.semester}"
        hash_md5 = f"hash_md5={self.hash_md5}"
        return f"FileKey({url}, {year}, {semester}, {hash_md5})"

    def get_moodle_pid_value(self) -> str:
        """Get hash."""
        return self.hash_md5


@dataclass(frozen=True)
class UnitKey(Key):
    """Key for units as to disambiguate it from keys for files and courses."""

    course_id: str
    year: str
    semester: str

    resource_type = "unit"

    @singledispatchmethod
    def __init__(self, course_id: str, year: str, semester: str) -> None:
        """Construct UnitKey."""
        object.__setattr__(self, "course_id", course_id)
        object.__setattr__(self, "year", year)
        object.__setattr__(self, "semester", semester)

    @__init__.register
    def _(self, moodle_file_json: dict, moodle_course_json: dict) -> None:
        """Create `cls` via info from moodle-json."""
        course_id = moodle_course_json["courseid"]
        year = moodle_file_json["year"]
        semester = moodle_file_json["semester"]
        self.__init__(course_id, year, semester)

    def __str__(self) -> str:
        """Get string-representation."""
        course_id = f"course_id={self.course_id}"
        year = f"year={self.year}"
        semester = f"semester={self.semester}"
        return f"UnitKey({course_id}, {year}, {semester})"

    def get_moodle_pid_value(self) -> str:
        """Get hash."""
        return f"{self.course_id}-{self.year}-{self.semester}"


@dataclass(frozen=True)
class CourseKey(Key):
    """Key for courses as to disambiguate it from keys for files and units."""

    course_id: str

    resource_type = "course"

    @singledispatchmethod
    def __init__(self, course_id: str) -> None:
        """Construct CourseKey."""
        object.__setattr__(self, "course_id", course_id)

    @__init__.register
    def _(self, moodle_course_metadata: dict) -> None:
        """Create `cls` via info from moodle-json."""
        course_id = moodle_course_metadata["courseid"]
        self.__init__(course_id)

    def __str__(self) -> str:
        """Get string-representation."""
        course_id = f"course_id={self.course_id}"
        return f"CourseKey({course_id})"

    def get_moodle_pid_value(self) -> str:
        """Get hash."""
        return self.course_id


@dataclass
class BaseRecord:
    """Base."""

    key: Key
    metadata: LOMMetadata

    @property
    def pid(self) -> str:
        """Get pid."""
        return self.key.get_moodle_pid_value()

    @abstractmethod
    def construct_up_links(self, records: BaseRecord) -> None:
        """Construct up links.

        Up describes the direction from files -> unit -> course
        """

    @abstractmethod
    def construct_down_links(self, records: BaseRecord) -> None:
        """Construct down links.

        Down describes the direction from course -> unit -> files
        """


@dataclass
class FileRecord(BaseRecord):
    """File."""

    file_url: str

    def construct_up_links(self, records: list[BaseRecord]) -> None:
        """Construct up links."""
        for record in records:
            self.metadata.append_relation(record.pid, "ispartof")

    def construct_down_links(self, _: BaseRecord) -> None:
        """Construct down links."""
        msg = "There exists no down under file."
        raise RuntimeError(msg)


@dataclass
class UnitRecord(BaseRecord):
    """Unit."""

    def construct_up_links(self, records: list[BaseRecord]) -> None:
        """Construct up links."""
        for record in records:
            self.metadata.append_relation(record.pid, "ispartof")

    def construct_down_links(self, records: list[BaseRecord]) -> None:
        """Construct down links."""
        for record in records:
            self.metadata.append_relation(record.pid, "haspart")


@dataclass
class CourseRecord(BaseRecord):
    """Course."""

    def construct_up_links(self, _: list[BaseRecord]) -> None:
        """Construct up links."""
        msg = "There exists no up upper course."
        raise RuntimeError(msg)

    def construct_down_links(self, records: list[BaseRecord]) -> None:
        """Construct down links."""
        for record in records:
            self.metadata.append_relation(record.pid, "haspart")
