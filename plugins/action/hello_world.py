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

"""
Cross-platform hello_world action plugin using COMMAND_SPEC pattern.

Demonstrates the command specification approach for cross-platform
command execution with templating, parsing, and validation.
"""

from __future__ import annotations

from typing import Any, Optional

from ansible.plugins.action import ActionBase

from ansible_collections.o0_o.core.plugins.module_utils import (
    CoreActionBase,
)
from ansible_collections.o0_o.utils.plugins.module_utils import (
    format_error_message,
)


class ActionModule(CoreActionBase, ActionBase):
    """Echo 'Hello, world!' and validate the output."""

    TRANSFERS_FILES = False
    _requires_connection = True
    _supports_check_mode = True
    _supports_async = False

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute hello_world command and return the output.

        :param Optional[str] tmp: Unused temporary directory path
        :param Optional[dict[str, Any]] task_vars: Available Ansible
            variables
        :returns dict[str, Any]: Result dictionary with 'message' key
        """
        task_vars = task_vars or {}
        self._def_inventory_hostname(task_vars)
        result = super().run(tmp, task_vars=task_vars)
        del tmp  # unused

        # Process command spec to get command requests
        cmd_requests = self._process_command_spec("hello_world")

        if not cmd_requests:
            result["failed"] = True
            result["msg"] = "No command specification found for 'hello_world'"
            return result

        # Run the first (and only) command request
        cmd_request = cmd_requests[0]

        # Execute the command
        cmd_result = self._command(
            cmd=cmd_request["command"],
            task_vars=task_vars,
        )

        # Add result to request dict to create cmd_completed
        cmd_completed = cmd_request.copy()
        cmd_completed["result"] = cmd_result

        # Process the completed command (includes validation)
        output, errors = self._process_command_result(cmd_completed)

        result["changed"] = False
        result["invocation"] = self._task.args.copy()

        if errors:
            result["failed"] = True
            result["msg"] = format_error_message(errors)
        else:
            result["message"] = output

        return result
