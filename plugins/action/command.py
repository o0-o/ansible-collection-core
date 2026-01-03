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
Cross-platform command execution action plugin.

Inspects the connection plugin and delegates to the appropriate
platform-specific command module:
- Windows (winrm, psrp): ansible.windows.win_command
- POSIX (ssh, local, etc.): o0_o.posix.command

Only shared parameters are accepted. For platform-specific features,
use the underlying modules directly.
"""

from __future__ import annotations

from typing import Any, Optional

from ansible.plugins.action import ActionBase

from ansible_collections.o0_o.windows.plugins.module_utils import (
    WindowsActionBase,
)
from ansible_collections.o0_o.posix.plugins.module_utils import (
    PosixActionBase,
)


class ActionModule(PosixActionBase, WindowsActionBase, ActionBase):
    """Cross-platform command dispatcher action plugin.

    Automatically routes command execution to the appropriate
    platform-specific module based on the connection plugin in use.
    """

    TRANSFERS_FILES = False
    _requires_connection = True
    _supports_check_mode = True
    _supports_async = False

    def _validate_args(self) -> dict[str, Any]:
        """
        Validate module arguments against the shared argument spec.

        :returns dict[str, Any]: Validated arguments for delegation
        """
        argument_spec = {
            "cmd": {"type": "str"},
            "argv": {"type": "list", "elements": "str"},
            "chdir": {"type": "path"},
            "creates": {"type": "path"},
            "removes": {"type": "path"},
            "stdin": {"type": "str"},
        }
        mutually_exclusive = [["cmd", "argv"]]
        required_one_of = [["cmd", "argv"]]

        _validation_result, validated_args = self.validate_argument_spec(
            argument_spec=argument_spec,
            mutually_exclusive=mutually_exclusive,
            required_one_of=required_one_of,
        )

        return validated_args

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute the command via the appropriate platform module.

        :param Optional[str] tmp: Temporary directory path (unused)
        :param Optional[dict[str, Any]] task_vars: Task variables
        :returns dict[str, Any]: Ansible result dictionary
        """
        task_vars = task_vars or {}
        self._def_inventory_hostname(task_vars)
        result = super().run(tmp, task_vars=task_vars)
        del tmp  # unused

        # Validate arguments and filter out None values
        plugin_args = {
            k: v for k, v in self._validate_args().items() if v is not None
        }

        # Determine target module based on connection type
        if self._is_posix_connection():
            target_module = "o0_o.posix.command"
        elif self._is_windows_connection():
            target_module = "ansible.windows.win_command"
        else:
            result["failed"] = True
            connection_type = self._get_connection_type()
            result["msg"] = (
                f"o0_o.core.command only supports POSIX or Windows "
                f"connections. Connection '{connection_type}' is not "
                "recognized as either."
            )
            return result

        self._display.vvv(f"Delegating to {target_module}")

        # Delegate to the appropriate command module
        delegated_result = self._run_action(
            plugin_name=target_module,
            plugin_args=plugin_args,
            task_vars=task_vars,
        )

        result.update(delegated_result)
        result["invocation"] = self._task.args.copy()
        result["module"] = target_module

        return result
