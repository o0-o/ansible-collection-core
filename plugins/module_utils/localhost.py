# vim: ts=4:sw=4:sts=4:et:ft=python
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil; -*-
#
# GNU General Public License v3.0+
# SPDX-License-Identifier: GPL-3.0-or-later
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# Copyright (c) 2025 oØ.o (@o0-o)
#
# This file is part of the o0_o.core Ansible Collection.

"""Localhost detection constants.

This module provides constants for identifying localhost variants
in inventory hostnames and connection configurations.
"""

from __future__ import annotations

from typing import FrozenSet


LOCALHOST_NAMES: FrozenSet[str] = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "::1",
    }
)
