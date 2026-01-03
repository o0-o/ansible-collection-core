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

"""Command specifications for cross-platform command execution.

This module defines command templates organized by implementation type.
Each specification includes a template, optional parser, and optional
validator. If no parser is specified, stdout is returned as-is.

Subclasses in other collections can extend COMMAND_SPEC by merging:

    from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
        COMMAND_SPEC as CORE_COMMAND_SPEC,
    )
    from ansible_collections.o0_o.posix.plugins.module_utils.parsers import (
        parse_stat,
    )

    COMMAND_SPEC = {
        **CORE_COMMAND_SPEC,
        "gnu": {
            "stat": {
                "template": ("stat", "-c", "%s", "{path}"),
                "parser": parse_stat,
            },
        },
    }
"""

from __future__ import annotations

from typing import Any, Dict

from ansible_collections.o0_o.core.plugins.module_utils.parsers import (
    strip_only,
    validate_hello_world,
)

COMMAND_SPEC: Dict[str, Dict[str, Any]] = {
    "core": {
        "hello_world": {
            "template": ("echo", "Hello, world!"),
            "parser": strip_only,
            "validator": validate_hello_world,
        },
        "whoami": {
            "template": ("whoami",),
        },
    }
}
