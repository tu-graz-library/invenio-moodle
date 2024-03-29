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
from enum import Enum, auto, unique
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
        """Get moodle pid value."""
        return self.hash_md5


@dataclass(frozen=True)
class LinkKey(Key):
    """Key for links only records."""

    url: str

    resource_type = "link"

    @singledispatchmethod
    def __init__(self, url: str) -> None:
        """Construct."""
        object.__setattr__(self, "url", url)

    def __str__(self) -> str:
        """Get string-representation."""
        url = f"url={self.url}"
        return f"LinkKey({url})"

    def get_moodle_pid_value(self) -> str:
        """Get moodle pid value."""
        return self.url


@unique
class Status(Enum):
    """Status."""

    NEW = auto()
    EDIT = auto()


@dataclass
class BaseRecord:
    """Base."""

    key: Key
    pid: str
    metadata: LOMMetadata
    status: Status

    @property
    def json(self) -> dict:
        """Get json."""
        return self.metadata.json


@dataclass
class FileRecord(BaseRecord):
    """File."""

    @property
    def url(self) -> str:
        """Get url."""
        return self.key.url

    @property
    def hash_md5(self) -> str:
        """Get hash_md5."""
        return self.key.hash_md5


@dataclass
class LinkRecord(BaseRecord):
    """Link."""
