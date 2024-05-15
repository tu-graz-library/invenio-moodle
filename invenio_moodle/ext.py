# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Flask extension for invenio-moodle."""

from flask import Flask

from . import config
from .services import MoodleRESTService, MoodleRESTServiceConfig


class InvenioMoodle:
    """invenio-moodle extension."""

    def __init__(self, app: Flask = None) -> None:
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Flask application initialization."""
        self.init_config(app)
        self.init_services(app)
        app.extensions["invenio-moodle"] = self

    def init_config(self, app: Flask) -> None:
        """Init config."""
        for k in dir(config):
            app.config.setdefault(k, getattr(config, k))

    def init_services(self, app: Flask) -> None:
        """Init Services."""
        endpoint = app.config.get("MOODLE_ENDPOINT", "")
        config = MoodleRESTServiceConfig(endpoint)
        self.moodle_rest_service = MoodleRESTService(config)
