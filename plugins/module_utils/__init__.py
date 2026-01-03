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

Command specifications are defined as class attributes on CoreActionBase
and can be extended by subclasses via dict merge.
"""

from __future__ import annotations

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC,
)
from ansible_collections.o0_o.core.plugins.module_utils.connection_types import (  # noqa: E501
    CONNECTION_TYPES,
)
from ansible_collections.o0_o.core.plugins.module_utils.core_action_base import (  # noqa: E501
    CoreActionBase,
)
from ansible_collections.o0_o.core.plugins.module_utils.parsers import (
    validate_hello_world,
)

__all__ = [
    "COMMAND_SPEC",
    "CONNECTION_TYPES",
    "CoreActionBase",
    "validate_hello_world",
]
