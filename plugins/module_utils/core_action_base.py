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
inter-plugin delegation, cross-platform command execution, and
command specification processing.

Command Specification Structure:
    {
        "implementation": {
            "cmd_type": {
                "template": ("command", "arg1", "{placeholder}"),
                "parser": optional_parser_function,
                "validator": optional_validator_function,
            },
        },
    }

Parser functions receive (rc, output, e_prefix) and return:
    (parsed_output, error_list_or_none)

Validator functions receive (parsed_output, e_prefix) and return:
    Optional[Exception] - None if valid, exception if invalid

If no parser is specified, stdout is returned as-is.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, Union

from ansible_collections.o0_o.utils.plugins.module_utils.typeguard_compat import (  # noqa: E501
    typechecked,
)

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC as CORE_COMMAND_SPEC,
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
    - Command specification processing via _process_command_spec()
    - Binary-safe command execution context manager

    Command specifications are defined in COMMAND_SPEC class attribute.
    Subclasses can extend by merging their specs:

        class PosixActionBase(CoreActionBase):
            COMMAND_SPEC = {
                **CoreActionBase.COMMAND_SPEC,
                "gnu": {"stat": {...}},
                "bsd": {"stat": {...}},
            }

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

    # Command specifications - subclasses extend via dict merge
    COMMAND_SPEC: Dict[str, Dict[str, Any]] = CORE_COMMAND_SPEC

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
    def _def_inventory_hostname(
        self, task_vars: Optional[Dict[str, Any]] = None
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

    @typechecked
    def _display_longest_command(
        self, commands_result: Dict[str, Any], context: str = ""
    ) -> None:
        """Display debug information about the longest running command.

        :param dict commands_result: Result from _run() call
        :param str context: Context description for the debug message
        """
        if not isinstance(commands_result.get("commands"), dict):
            return

        # Find the longest running command
        longest_cmd = None
        longest_elapsed = 0

        for cmd_key, cmd_result in commands_result["commands"].items():
            if "elapsed" in cmd_result:
                elapsed = cmd_result["elapsed"].get("seconds", 0)
                if elapsed > longest_elapsed:
                    longest_elapsed = elapsed
                    longest_cmd = cmd_result.get("cmd", cmd_key)

        context_str = f" ({context})" if context else ""
        if longest_elapsed > 0:
            self._display.vvv(
                f"[{self.inventory_hostname}] Longest command{context_str}: "
                f"{longest_cmd} took {longest_elapsed}s"
            )
        else:
            self._display.vvv(
                f"[{self.inventory_hostname}] All commands{context_str} "
                f"completed in under 1 second"
            )

    @typechecked
    def _process_command_spec(
        self,
        cmd_type: str,
        **cmd_kwargs: str,
    ) -> list[Dict[str, Any]]:
        """Process command spec and return list of command requests.

        Looks up cmd_type in self.COMMAND_SPEC across all
        implementations and builds command request dicts with
        formatted templates.

        :param str cmd_type: Command type to look up
        :param **cmd_kwargs: Format arguments for command template
        :returns list[Dict[str, Any]]: List of command request dicts
        :raises TypeError: If spec structure is malformed
        :raises ValueError: If template is missing or empty
        """
        results: list[Dict[str, Any]] = []
        spec = self.COMMAND_SPEC

        if not isinstance(spec, dict):
            raise TypeError("COMMAND_SPEC is not a dict")

        for implementation_name, implementation in spec.items():
            if not isinstance(implementation, dict):
                raise TypeError(
                    f"The {implementation_name} implementation in "
                    "COMMAND_SPEC is not a dict"
                )
            variant = implementation.get(cmd_type)
            if variant is not None:
                if not isinstance(variant, dict):
                    raise TypeError(
                        f"[{implementation_name}] Command type {cmd_type} is "
                        "not a dict"
                    )
                cmd_request = variant.copy()
                cmd_request["implementation"] = implementation_name
                cmd_request["type"] = cmd_type
                e_prefix = self._get_command_error_prefix(cmd_request)
                template = cmd_request.pop("template", None)
                if template is None:
                    raise ValueError(
                        f"{e_prefix}Command specification is missing a "
                        "template"
                    )
                if isinstance(template, str):
                    cmd_str = template.format(**cmd_kwargs).strip()
                    if not cmd_str:
                        raise ValueError(f"{e_prefix}Command is empty")
                    cmd_request["command"] = cmd_str
                    cmd_default_name = cmd_str.split()[0]
                elif isinstance(template, Iterable):
                    cmd_tuple = tuple(
                        (
                            arg.format(**cmd_kwargs)
                            if isinstance(arg, str)
                            else arg
                        )
                        for arg in template
                    )
                    if not cmd_tuple:
                        raise ValueError(f"{e_prefix}Command is empty")
                    if not isinstance(cmd_tuple[0], str):
                        raise TypeError(
                            f"{e_prefix}Command (without args) is not a "
                            "string"
                        )
                    if cmd_tuple[0] == "":
                        raise ValueError(
                            f"{e_prefix}Command (without args) is empty"
                        )
                    cmd_request["command"] = cmd_tuple
                    cmd_default_name = cmd_tuple[0].strip()
                else:
                    raise TypeError(
                        f"{e_prefix}Template is not a string or iterable"
                    )
                cmd_request["name"] = (
                    cmd_request.get("name") or cmd_default_name
                )
                results.append(cmd_request)
                if implementation_name == "gnu":
                    # gnu commands may be prefixed with 'g'
                    alt_gnu_request = cmd_request.copy()
                    cmd = alt_gnu_request["command"]
                    if isinstance(cmd, str):
                        alt_gnu_cmd = f"g{cmd}"
                    else:
                        alt_gnu_cmd = (f"g{cmd[0].strip()}", *cmd[1:])
                    alt_gnu_request["command"] = alt_gnu_cmd
                    results.append(alt_gnu_request)

        return results

    @typechecked
    def _get_command_error_prefix(self, command_obj: Dict[str, Any]) -> str:
        """Build error prefix string from command object metadata.

        :param Dict[str, Any] command_obj: Command object with
            implementation and type keys
        :returns str: Error prefix in format '[implementation_type] '
        :raises TypeError: If command_obj is not a dict
        :raises ValueError: If required keys are missing
        """
        if not isinstance(command_obj, dict):
            raise TypeError("Command object is not a dict")

        cmd_implementation = command_obj.get("implementation")
        if not cmd_implementation:
            raise ValueError("Command object is missing implementation")

        cmd_type = command_obj.get("type")
        if not cmd_type:
            raise ValueError("Command object is missing type")

        return f"[{cmd_implementation}_{cmd_type}] "

    @typechecked
    def _process_command_result(
        self,
        cmd_completed: Dict[str, Any],
        non_error_codes: Optional[list[int]] = None,
    ) -> Tuple[Optional[str], Optional[list]]:
        """Process command result: validate, parse, and validate output.

        Extracts stdout from the command result, optionally runs a
        parser, and optionally runs a validator. Returns parsed output
        or errors.

        :param Dict[str, Any] cmd_completed: Completed command dict
            with 'result' key containing rc, stdout, stderr, plus
            optional 'parser' and 'validator' callables
        :param Optional[list[int]] non_error_codes: Return codes
            considered non-error. Defaults to [0]
        :returns Tuple[Optional[str], Optional[list]]:
            (parsed_output, None) on success, or (None, [errors]) on
            failure
        :raises TypeError: If cmd_completed or result is not a dict
        :raises ValueError: If required fields are missing or malformed
        """
        if non_error_codes is None:
            non_error_codes = [0]

        if not isinstance(cmd_completed, dict):
            raise TypeError("Completed command not a dict")

        e_prefix = self._get_command_error_prefix(cmd_completed)

        cmd_result = cmd_completed.get("result")
        if not isinstance(cmd_result, dict):
            raise TypeError(f"{e_prefix}Command result is not a dict")

        # Required fields
        rc = cmd_result.get("rc")
        if rc is None:
            raise ValueError(f"{e_prefix}Command result is missing 'rc'")
        try:
            rc = int(rc)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"{e_prefix}Command result 'rc' is not convertible to int"
            ) from e
        output = cmd_result.get("stdout")
        if output is None:
            raise ValueError(f"{e_prefix}Command result is missing 'stdout'")
        if not isinstance(output, str):
            raise ValueError(f"{e_prefix}Command result 'stdout' is not str")
        output = output.rstrip("\n").replace("\r", "")

        # Optional but validated if present
        if "stderr" in cmd_result:
            if not isinstance(cmd_result["stderr"], str):
                raise ValueError(
                    f"{e_prefix}Command result 'stderr' is not str"
                )

        # Check return code
        if rc not in non_error_codes:
            stderr = cmd_result.get("stderr", "").strip() or "No stderr"
            return (
                None,
                [
                    RuntimeError(
                        f"{e_prefix}command exited with code {rc}: {stderr}"
                    )
                ],
            )

        # Parse output (optional - defaults to pass-through)
        parser = cmd_completed.get("parser")
        if parser is None:
            parsed_output = output
        else:
            if not isinstance(parser, Callable):
                raise TypeError(f"{e_prefix}Parser is not callable")
            parsed_output, parse_errors = parser(rc, output, e_prefix)
            if parse_errors:
                return None, parse_errors

        # Validate output (optional)
        validator = cmd_completed.get("validator")
        if validator is not None:
            if not isinstance(validator, Callable):
                raise TypeError(f"{e_prefix}Validator is not callable")
            validation_error = validator(parsed_output, e_prefix)
            if validation_error is not None:
                return None, [validation_error]

        return parsed_output, None

    @typechecked
    def _run_action(
        self,
        plugin_name: str,
        plugin_args: Dict[str, Any],
        task_vars: Optional[Dict[str, Any]] = None,
        check_mode: Optional[bool] = None,
    ) -> Dict[str, Any]:
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
        task_vars: Optional[Dict[str, Any]] = None,
        check_mode: Optional[bool] = None,
    ) -> Dict[str, Any]:
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
        :param Optional[Dict[str, Any]] task_vars: Dictionary of task
            variables from the calling task
        :param Optional[bool] check_mode: Optional override for Ansible
            check mode
        :returns Dict[str, Any]: The result dictionary from the command
            plugin
        :raises TypeError: If cmd is not a string, list, or tuple
        """
        task_vars = task_vars or {}

        args: Dict[str, Any] = {}

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
