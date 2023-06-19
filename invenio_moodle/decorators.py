# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Decorators."""

from collections.abc import Callable
from functools import partial, wraps

from invenio_access.permissions import system_identity
from invenio_records_lom.proxies import current_records_lom


def edit(func: Callable) -> Callable:
    """Edit decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["edit"] = partial(service.edit, identity=system_identity)
        func(*args, **kwargs)

    return wrapper


def update_draft(func: Callable) -> Callable:
    """Edit decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["update_draft"] = partial(service.update_draft, identity=system_identity)
        func(*args, **kwargs)

    return wrapper


def publish(func: Callable) -> Callable:
    """Publish decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["publish"] = partial(service.publish, identity=system_identity)
        func(*args, **kwargs)

    return wrapper


def resolve(func: Callable) -> Callable:
    """Resolve decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["resolve"] = partial(
            service.draft_cls.pid.resolve,
            registered_only=False,
        )
        func(*args, **kwargs)

    return wrapper


def read(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["read"] = partial(service, identity=system_identity)
        func(*args, **kwargs)

    return wrapper


def commit_file(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        df_service = current_records_lom.records_service.draft_files
        kwargs["commit_file"] = partial(
            df_service.commit_file,
            identity=system_identity,
        )
        func(*args, **kwargs)

    return wrapper


def init_files(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        df_service = current_records_lom.records_service.draft_files
        kwargs["init_files"] = partial(df_service.init_files, identity=system_identity)
        func(*args, **kwargs)

    return wrapper


def list_draft_files(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        df_service = current_records_lom.records_service.draft_files
        kwargs["list_draft_files"] = partial(
            df_service.list_files,
            identity=system_identity,
        )
        func(*args, **kwargs)

    return wrapper


def set_file_content(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        df_service = current_records_lom.records_service.draft_files
        kwargs["set_file_content"] = partial(
            df_service.set_file_content,
            identity=system_identity,
        )
        func(*args, **kwargs)

    return wrapper


def list_files(func: Callable) -> Callable:
    """Read decorator."""

    @wraps(func)
    def wrapper(*args: dict, **kwargs: dict) -> Callable:
        """Wrap."""
        service = current_records_lom.records_service
        kwargs["list_files"] = partial(
            service.files.list_files,
            identity=system_identity,
        )
        func(*args, **kwargs)

    return wrapper
