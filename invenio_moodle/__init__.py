# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Provides API for Moodle."""

from .ext import InvenioMoodle

__version__ = "0.2.3"

__all__ = ("__version__", "InvenioMoodle")
