# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2023 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Flask extension for invenio-moodle."""

from flask import Flask

from . import config


class InvenioMoodle:
    """invenio-moodle extension."""

    def __init__(self, app: Flask = None) -> None:
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Flask application initialization."""
        self.init_config(app)
        app.extensions["invenio-moodle"] = self

    def init_config(self, app: Flask) -> None:
        """Initialize configuration."""
        for k in dir(config):
            if k == "MOODLE_CELERY_BEAT_SCHEDULE":
                app.config.setdefault("CELERY_BEAT_SCHEDULE", {})
                app.config["CELERY_BEAT_SCHEDULE"].update(getattr(config, k))

            elif k == "MOODLE_PERSISTENT_IDENTIFIER_PROVIDERS":
                app.config.setdefault("LOM_PERSISTENT_IDENTIFIER_PROVIDERS", [])
                app.config["LOM_PERSISTENT_IDENTIFIER_PROVIDERS"].extend(
                    getattr(config, k),
                )

            elif k == "MOODLE_PERSISTENT_IDENTIFIERS":
                app.config.setdefault("LOM_PERSISTENT_IDENTIFIERS", {})
                app.config["LOM_PERSISTENT_IDENTIFIERS"].update(getattr(config, k))

            if k.startswith("MOODLE_"):
                app.config.setdefault(k, getattr(config, k))
