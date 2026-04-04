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
Base class for Ansible action plugins with cross-platform support.

This module provides a mixin class with utilities for action plugins,
including inventory hostname detection, command timing display,
inter-plugin delegation, and cross-platform command execution.

For command specification processing, see command_utils.py which
provides standalone functions that can be used with any COMMAND_SPEC.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Generator, Optional, Union

from ansible_collections.o0_o.utils.plugins.module_utils import typechecked

from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    CONNECTION_BY_PLATFORM,
)


class CoreActionBase:
    """
    Mixin class for Ansible action plugins with cross-platform support.

    This mixin provides cross-cutting helpers that are useful across
    different types of action plugins, regardless of the target system.

    Provides:
    - Connection type detection for platform-specific routing
    - Inventory hostname detection for logging
    - Command timing display for debugging
    - Inter-plugin delegation using FQCNs
    - Cross-platform command execution via _command()
    - Binary-safe command execution context manager

    For command specification processing, import the standalone
    functions from command_utils and your COMMAND_SPEC directly.

    Note: @typechecked is applied to methods rather than the class to
    avoid metaclass conflicts when subclasses also inherit from Ansible
    base classes like ActionBase.

    Usage:
        from ansible.plugins.action import ActionBase
        from ansible_collections.o0_o.core.plugins.module_utils import (
            CoreActionBase,
        )

        class ActionModule(CoreActionBase, ActionBase):
            def run(self, tmp=None, task_vars=None):
                ...
    """

    @contextmanager
    @typechecked
    def _binary_safe_execution(self) -> Generator[None, None, None]:
        """Context manager to allow non-UTF-8 data in module responses.

        Temporarily disables Ansible's strict UTF-8 response validation,
        allowing binary data to pass through module execution without
        raising deserialization errors.

        This is necessary when reading binary file content via the
        command module, as Ansible's default behavior rejects responses
        containing surrogate characters (used for non-UTF-8 bytes).

        The raw module does not require this workaround as it bypasses
        the module response deserialization layer.

        Usage::

            with self._binary_safe_execution():
                result = self._execute_module(
                    module_name='command',
                    module_args={'_raw_params': f'cat {path}'},
                    task_vars=task_vars,
                )

        :yields: None
        :raises RuntimeError: If ansible.constants has not been imported
        """
        # Verify ansible.constants is available (must be imported by the
        # action plugin since module_utils cannot import it directly)
        if "ansible.constants" not in sys.modules:
            raise RuntimeError(
                "_binary_safe_execution() requires ansible.constants to be "
                "imported. Add 'from ansible import constants' to your "
                "action plugin."
            )

        constants = sys.modules["ansible.constants"]

        original = constants.MODULE_STRICT_UTF8_RESPONSE
        constants.MODULE_STRICT_UTF8_RESPONSE = False
        try:
            yield
        finally:
            constants.MODULE_STRICT_UTF8_RESPONSE = original

    @typechecked
    def _get_connection_type(self) -> str:
        """Get the connection plugin type name.

        :returns str: Connection type (e.g., 'ssh', 'winrm', 'local')
        """
        return getattr(self._play_context, "connection", "ssh")

    @typechecked
    def _get_platform(self) -> str:
        """Get the platform based on connection plugin.

        Maps the connection plugin to a platform category for routing
        to platform-specific modules.

        :returns str: Platform ('posix' or 'windows')
        :raises ValueError: If connection type is not recognized
        """
        connection_type = self._get_connection_type()
        for platform, connections in CONNECTION_BY_PLATFORM.items():
            if connection_type in connections:
                return platform
        # Build error message with all known platforms
        known = ", ".join(
            f"{p} ({', '.join(sorted(c))})"
            for p, c in CONNECTION_BY_PLATFORM.items()
        )
        raise ValueError(
            f"Connection '{connection_type}' is not recognized. "
            f"Known platforms: {known}"
        )

    @typechecked
    def _def_inventory_hostname(
        self, task_vars: Optional[dict[str, Any]] = None
    ) -> str:
        """Get/define the inventory hostname for log/warning messages.

        Prefers the value from ``task_vars`` when provided, then falls
        back to the task's vars mapping. Defaults to ``localhost`` when
        no value can be determined (e.g., local actions).

        Sets self.inventory_hostname and returns the value.

        :param task_vars: Optional task vars mapping
        :returns str: The inventory hostname or 'localhost' as fallback
        """
        if isinstance(task_vars, dict):
            host = task_vars.get("inventory_hostname")
            if host:
                self.inventory_hostname = str(host)
                return self.inventory_hostname

        try:
            mapping = getattr(self._task, "vars", None)
            if isinstance(mapping, dict):
                host = mapping.get("inventory_hostname")
                if host:
                    self.inventory_hostname = str(host)
                    return self.inventory_hostname
        except Exception:
            pass

        self.inventory_hostname = "localhost"
        return self.inventory_hostname

    def _def_effective_user(
        self, task_vars: Optional[dict[str, Any]] = None
    ) -> str:
        """Determine the effective remote user for this task.

        When ``become`` is active, returns the become user (defaults
        to ``root`` per Ansible convention).  Otherwise returns the
        connection user.  Falls back to ``ansible_user`` from
        task_vars, then to the current local username.

        Sets ``self.effective_user`` and returns the value.

        :param Optional[dict[str, Any]] task_vars: Task variables
        :returns str: The effective remote username
        """
        # Check play_context for become
        play_ctx = getattr(self, "_play_context", None)

        if play_ctx and play_ctx.become:
            user = play_ctx.become_user
            if user:
                self.effective_user = str(user)
                return self.effective_user
            # become without explicit user defaults to root
            self.effective_user = "root"
            return self.effective_user

        # No become — use connection user
        if play_ctx:
            user = play_ctx.remote_user or play_ctx.connection_user
            if user:
                self.effective_user = str(user)
                return self.effective_user

        # Fall back to task_vars
        if isinstance(task_vars, dict):
            user = task_vars.get("ansible_user")
            if user:
                self.effective_user = str(user)
                return self.effective_user

        # Last resort: local username
        import getpass

        self.effective_user = getpass.getuser()
        return self.effective_user

    @typechecked
    def _run_action(
        self,
        plugin_name: str,
        plugin_args: dict[str, Any],
        task_vars: Optional[dict[str, Any]] = None,
        check_mode: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Execute another action plugin using the provided arguments.

        :param str plugin_name: Fully qualified name of the plugin to
            run (e.g. 'ansible.builtin.command')
        :param dict plugin_args: Dictionary of arguments to pass to the
            plugin
        :param Optional[dict] task_vars: Dictionary of task variables
            from the calling task
        :param Optional[bool] check_mode: Override check mode setting
        :returns dict: The result dictionary returned by the plugin's
            run method
        """
        current_fqcn = self._task.action.lower().strip()
        requested_fqcn = plugin_name.lower().strip()

        if requested_fqcn == current_fqcn:
            raise RecursionError(
                f"CoreActionBase attempted to call '{plugin_name}' from "
                "within itself. This would result in infinite recursion."
            )

        task = self._task.copy()
        task.args.clear()
        task.args.update(plugin_args)

        if getattr(self, "raw", False):
            task.args["raw"] = True

        plugin = self._shared_loader_obj.action_loader.get(
            plugin_name,
            task=task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj,
        )

        if plugin is None:
            return self._execute_module(
                module_name=plugin_name,
                module_args=plugin_args,
                task_vars=task_vars,
            )

        if check_mode is not None:
            plugin._task.check_mode = check_mode

        result = plugin.run(task_vars=task_vars)

        # Update raw mode based on delegated plugin's result
        if "raw" in result:
            if getattr(self, "raw", None) == "auto":
                self.raw = result["raw"]
            elif result["raw"]:
                self.raw = True

        return result

    @typechecked
    def _command(
        self,
        cmd: Union[str, list[str], tuple[str, ...]],
        stdin: Optional[str] = None,
        chdir: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
        check_mode: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Run the cross-platform command action plugin.

        Executes a command via o0_o.core.command, which routes to the
        appropriate platform-specific module (POSIX or Windows).

        :param Union[str, list[str], tuple[str, ...]] cmd: Command to
            execute. Can be a shell string, list, or tuple of arguments.
            Tuples are converted to lists automatically.
        :param Optional[str] stdin: Optional standard input to pass to
            the command
        :param Optional[str] chdir: Change to this directory before
            executing
        :param Optional[dict[str, Any]] task_vars: Dictionary of task
            variables from the calling task
        :param Optional[bool] check_mode: Optional override for Ansible
            check mode
        :returns dict[str, Any]: The result dictionary from the command
            plugin
        :raises TypeError: If cmd is not a string, list, or tuple
        """
        task_vars = task_vars or {}

        args: dict[str, Any] = {}

        if stdin is not None:
            args["stdin"] = stdin
        if chdir is not None:
            args["chdir"] = chdir

        if isinstance(cmd, str):
            args["cmd"] = cmd
        elif isinstance(cmd, (list, tuple)):
            args["argv"] = list(cmd)
        else:
            raise TypeError(
                f"Expected cmd to be str, list, or tuple, "
                f"got {type(cmd).__name__}"
            )

        return self._run_action(
            "o0_o.core.command",
            args,
            task_vars=task_vars,
            check_mode=check_mode,
        )
