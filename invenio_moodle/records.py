# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Records."""

from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper

from requests import HTTPError, get, head

from .types import URL


@dataclass
class MoodleRESTConfig:
    """Moodle rest config."""

    endpoint: str = ""


class MoodleConnection:
    """Moodle connection."""

    def __init__(self, config: MoodleRESTConfig) -> None:
        """Construct."""
        self.config = config

    def get(self) -> dict:
        """Get."""
        try:
            response = get(self.config.endpoint, timeout=10)
            response.raise_for_status()
        except HTTPError as error:
            raise RuntimeError(str(error)) from error
        else:
            return response.json()

    def get_filename(self, file_url: URL) -> str:
        """Get filename."""
        headers = head(file_url, timeout=10).headers
        try:
            return headers["Content-Disposition"].split("filename=")[-1].strip('"')
        except KeyError as error:
            msg = f"ERROR moodle no filename found for url: {file_url}"
            raise RuntimeError(msg) from error

    def store_file_temporarily(
        self,
        file_url: URL,
        file_pointer: _TemporaryFileWrapper,
    ) -> None:
        """Store file temporarily."""
        with get(file_url, stream=True, timeout=10) as response:
            copyfileobj(response.raw, file_pointer)


class MoodleAPI:
    """Moodle api."""

    connection_cls = MoodleConnection

    def __init__(self, config: MoodleRESTConfig) -> None:
        """Construct."""
        self.connection = self.connection_cls(config)

    def download_file(self, file_url: URL) -> str:
        """Download file."""
        filename = self.connection.get_filename(file_url)
        prefix = Path(filename).stem
        suffix = Path(filename).suffix

        with NamedTemporaryFile(
            delete=False,
            delete_on_close=False,
            prefix=f"{prefix}-",
            suffix=suffix,
        ) as file_pointer:
            self.connection.store_file_temporarily(file_url, file_pointer)
        return file_pointer.name

    def fetch_records(self) -> dict:
        """Fetch data from the endpoint."""
        return self.connection.get()
