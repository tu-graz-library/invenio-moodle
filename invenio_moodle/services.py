# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Services."""

from collections.abc import Callable
from functools import wraps

from flask_principal import Identity
from marshmallow import ValidationError

from .records import MoodleAPI, MoodleRESTConfig
from .schemas import MoodleSchema
from .types import FileCacheInfo
from .utils import extract_moodle_records, post_processing


class MoodleRESTServiceConfig(MoodleRESTConfig):
    """Rest config."""

    api_cls = MoodleAPI


class MoodleRESTService:
    """Moodle rest service."""

    def __init__(self, config: MoodleRESTServiceConfig) -> None:
        """Construct."""
        self._config = config
        self.api = self.api_cls(config=config)

    @property
    def api_cls(self) -> MoodleAPI:
        """Get api cls."""
        return self._config.api_cls

    def download_file(self, _: Identity, url: str) -> FileCacheInfo:
        """Download file."""
        return self.api.download_file(url)

    def fetch_records(self, _: Identity) -> list[dict]:
        """Fetch moodle."""
        moodle_data = self.api.fetch_records()

        try:
            MoodleSchema().load(moodle_data)
        except ValidationError as error:
            raise RuntimeError(str(error)) from error

        moodle_records = extract_moodle_records(moodle_data)
        post_processing(moodle_records)

        return moodle_records


def build_service[T](func: Callable[..., T]) -> Callable:
    """Decorate to build the services."""

    @wraps(func)
    def build(*_: dict, **kwargs: dict) -> T:
        endpoint = kwargs.pop("endpoint")
        config = MoodleRESTServiceConfig(endpoint)
        kwargs["moodle_service"] = MoodleRESTService(config)

        return func(**kwargs)

    return build
