#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-moodle is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

# Quit on errors
set -o errexit

# Quit on unbound symbols
set -o nounset

ruff check .

python -m check_manifest
python -m sphinx.cmd.build -qnNW docs docs/_build/html
python -m pytest
