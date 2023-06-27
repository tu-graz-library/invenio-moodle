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
        app.config.setdefault("LOM_PERSISTENT_IDENTIFIERS", {})
        app.config.setdefault("LOM_PERSISTENT_IDENTIFIER_PROVIDERS", [])

        for key in dir(config):
            value = getattr(config, key)
            lom_config_variable = key.replace("MOODLE_", "LOM_")

            if lom_config_variable in app.config:
                container = app.config[lom_config_variable]

                if isinstance(container, list):
                    container.extend(value)
                elif isinstance(container, dict):
                    container.update(value)
                else:
                    container = value

            elif key.startswith("MOODLE_"):
                app.config.setdefault(key, value)
