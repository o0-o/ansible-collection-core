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

"""Module utilities for the o0_o.core collection.

This module provides cross-platform command execution primitives
including base classes for action plugins that need to run commands
on remote hosts across different platforms (POSIX, Windows).
"""

from __future__ import annotations

__all__: list[str] = []
