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

Command specifications are defined in command_spec.py and processed
via standalone functions in command_utils.py. Action plugins import
COMMAND_SPEC and the processing functions directly.

The provenance vocabulary every fact in the o0_o namespace speaks -
``evidence`` keyed by kind, ``origins`` naming who composed a fact -
is defined in evidence_utils.py and exported here for the collections
above this one to import.
"""

from __future__ import annotations

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC,
)
from ansible_collections.o0_o.core.plugins.module_utils.command_utils import (
    display_longest_command,
    format_error_message,
    process_all_command_results,
    process_command_result,
    process_command_spec,
)
from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    CONNECTION_BY_PLATFORM,
)
from ansible_collections.o0_o.core.plugins.module_utils.core_action_base import (  # noqa: E501
    CoreActionBase,
)
from ansible_collections.o0_o.core.plugins.module_utils.evidence_utils import (  # noqa: E501
    EVIDENCE,
    EVIDENCE_KINDS,
    ORIGINS,
    command_name,
    command_names,
    commands_run,
    compose_evidence,
    merge_entry,
    merge_evidence,
    name_origins,
)
from ansible_collections.o0_o.core.plugins.module_utils.localhost import (
    LOCALHOST_NAMES,
)
from ansible_collections.o0_o.core.plugins.module_utils.vars_lookup_base import (  # noqa: E501
    VarsLookupBase,
)

__all__ = [
    "COMMAND_SPEC",
    "CONNECTION_BY_PLATFORM",
    "CoreActionBase",
    "EVIDENCE",
    "EVIDENCE_KINDS",
    "LOCALHOST_NAMES",
    "ORIGINS",
    "VarsLookupBase",
    "command_name",
    "command_names",
    "commands_run",
    "compose_evidence",
    "display_longest_command",
    "format_error_message",
    "merge_entry",
    "merge_evidence",
    "name_origins",
    "process_all_command_results",
    "process_command_result",
    "process_command_spec",
]
