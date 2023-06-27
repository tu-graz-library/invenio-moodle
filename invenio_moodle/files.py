# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Provide functions to store files into the database."""

from __future__ import annotations

import hashlib
import re
import typing as t
from pathlib import Path
from tempfile import TemporaryDirectory

from requests import Response, Session

from .types import FileCacheInfo

if t.TYPE_CHECKING:
    from flask_principal import Identity
    from invenio_records_resources.services import FileService

    from .types import FileRecord


def save_file_locally(response: Response, idx: int, directory: Path) -> FileCacheInfo:
    """Save file locally."""
    # find filename in headers
    dispos = response.headers.get("content-disposition", "")

    # all html-headers are encoded in latin1, but python interprets as utf-8
    dispos = dispos.encode("latin1").decode("utf-8")

    if match := re.search('filename="([^"]*)"', dispos):
        filename = match.group(1)
    else:
        msg = f"couldn't find filename in header {dispos}"
        raise ValueError(msg)

    # save file to `directory`, compute its hash along the way
    # filepath is of form 'directory/0/file.pdf'
    filepath = directory.joinpath(str(idx), filename.replace(" ", "_"))
    hash_ = hashlib.md5()  # noqa: S324

    # create 'directory/0/'
    filepath.parent.mkdir(parents=True)

    with filepath.open(mode="wb", buffering=1024 * 1024) as fp:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            hash_.update(chunk)
            fp.write(chunk)

    return FileCacheInfo(hash_md5=hash_.hexdigest(), path=filepath)


def cache_file(url: str) -> FileCacheInfo:
    """Create a file-cache.

    It creates a file-cache by downloading unprovided files into
    `directory` and hashing all files.

    :param Path directory: The directory to download unprovided files into.
    :param list[str] urls: The URLs of the to-be-cached files.
    """
    with Session() as session, TemporaryDirectory() as temp_dir:
        directory = Path(temp_dir)
        with session.get(url, stream=True) as response:
            response.raise_for_status()

        return save_file_locally(response, directory)


def add_file_to_draft(
    record: FileRecord,
    draft_files: FileService,
    identity: Identity,
) -> None:
    """Add file to draft."""
    file_info = cache_file(record.url)
    filename = file_info.path.name
    draft_files.init_files(id_=record.pid, data=[{"key": filename}], identity=identity)

    # ATTENTION: 1024 * 1024 may be a problem?
    with file_info.path.open(mode="rb", buffering=1024 * 1024) as fp:
        draft_files.set_file_content(
            id_=record.pid,
            file_key=filename,
            stream=fp,
            identity=identity,
        )
    draft_files.commit_file(id_=record.pid, file_key=filename, identity=identity)
