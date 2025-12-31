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
Base class for Ansible action plugins with cross-platform execution support.

This module provides a mixin class with utilities for action plugins,
including text normalization, inventory hostname detection, command
timing display, inter-plugin delegation, and template-based command
execution with result parsing.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from ansible_collections.o0_o.utils.plugins.module_utils.typeguard_compat import (  # noqa: E501
    typechecked,
)


class CoreActionBase:
    """
    Mixin class for Ansible action plugins with cross-platform support.

    This mixin provides cross-cutting helpers that are useful across
    different types of action plugins, regardless of the target system.

    Utilities include:
    - Text normalization (newline handling)
    - Inventory hostname detection for logging
    - Command timing display for debugging
    - Inter-plugin delegation using FQCNs
    - Template-based command generation and result parsing

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
    def _normalize_newlines(self, text: str) -> str:
        """
        Normalize Windows-style line endings to Unix-style.

        Converts CRLF (\\r\\n) to LF (\\n) for consistent parsing
        across platforms. This matches the behavior of the builtin
        command module.

        :param str text: Text with potential CRLF line endings
        :returns str: Text with normalized LF line endings
        """
        return text.replace("\r\n", "\n")

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
    def _get_run_template(
        self,
        cmd_type: str,
        cmd_variant: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get command tuple, parser, and validator for a command type.

        Retrieves the template configuration for executing and parsing
        a specific command type. For templates with variants, the
        variant-level values override template-level defaults.

        Requires self._run_templates to be defined by the subclass.

        :param str cmd_type: Command type key in _run_templates
        :param Optional[str] cmd_variant: Variant name for commands
            with multiple variants
        :returns Dict[str, Any]: Dict containing:
            - 'cmd': Command tuple with placeholders (e.g., '{path}')
            - 'parser': Callable to parse command result
            - 'validator': Optional callable to validate parsed data,
              or None if no validator defined
        :raises ValueError: If cmd_type or variant is invalid
        :raises TypeError: If template structure is malformed
        :raises AttributeError: If _run_templates is not defined
        """
        templates = getattr(self, "_run_templates", None)
        if templates is None:
            raise AttributeError(
                "_get_run_template requires _run_templates to be defined"
            )

        template = templates.get(cmd_type)
        e_prefix = f"[run_template][{cmd_type}] "

        if template is None:
            valid_types = ", ".join(f"'{t}'" for t in templates.keys())
            raise ValueError(
                f"{e_prefix}invalid template, valid options are {valid_types}"
            )
        if not isinstance(template, dict):
            raise TypeError(f"{e_prefix}template is not a dict")

        cmd = template.get("cmd")
        parser = template.get("parser")
        validator = template.get("validator")

        # Get the command tuple from the template structure
        if cmd_variant is not None:
            e_prefix = f"{e_prefix}[{cmd_variant}] "
            if "variants" not in template:
                raise ValueError(f"{e_prefix}no variants in this template")
            variants = template.get("variants")
            if not isinstance(variants, dict):
                raise TypeError(
                    f"{e_prefix}malformed template, 'variants' is not a dict"
                )
            variant = variants.get(cmd_variant)
            if variant is None:
                valid_variants = ", ".join(f"'{v}'" for v in variants.keys())
                raise ValueError(
                    f"{e_prefix}invalid variant, valid options are "
                    f"{valid_variants}"
                )
            if not isinstance(variant, dict):
                raise TypeError(
                    f"{e_prefix}malformed template, variant is not a dict"
                )
            cmd = variant.get("cmd", cmd)
            parser = variant.get("parser", parser)
            validator = variant.get("validator", validator)

        elif "variants" in template:
            raise ValueError(f"{e_prefix}requires a variant")

        if cmd is None:
            raise ValueError(f"{e_prefix}malformed template, missing command")
        if not isinstance(cmd, tuple):
            raise TypeError(f"{e_prefix}command is not a tuple")
        if parser is None:
            raise ValueError(f"{e_prefix}malformed template, missing a parser")
        if not callable(parser):
            raise TypeError(f"{e_prefix}parser is not callable")

        return {"cmd": cmd, "parser": parser, "validator": validator}

    @typechecked
    def _get_template_command(
        self,
        cmd_type: str,
        variant: Optional[str] = None,
        **fmt_kwargs: str,
    ) -> Dict[str, tuple]:
        """Get command dict with generated key and formatted command tuple.

        Returns a dict with keys built from cmd_type, format kwargs, and
        variant(s). Command tuples have placeholders substituted with the
        provided kwargs.

        When a template has variants and no variant is specified, returns
        commands for ALL variants. This allows a single call to generate
        all variant commands for detection mode.

        Key format: '{cmd_type}_{kwarg_val_1}_{kwarg_val_2}_...[_{variant}]'

        Examples:
            >>> self._get_template_command("sha256", "gnu", path="/tmp/foo")
            {"sha256_/tmp/foo_gnu": ("sha256sum", "/tmp/foo")}

            >>> self._get_template_command("sha256", path="/tmp/foo")
            # Returns all variants if sha256 has variants defined
            {
                "sha256_/tmp/foo_gnu": ("sha256sum", "/tmp/foo"),
                "sha256_/tmp/foo_bsd": ("sha256", "-q", "/tmp/foo"),
                ...
            }

        :param str cmd_type: Command type key in _run_templates
        :param Optional[str] variant: Variant name for commands with
            multiple variants. If None and template has variants,
            returns commands for all variants.
        :param **fmt_kwargs: Keyword arguments for formatting the
            command template (e.g., path='/tmp/file')
        :returns Dict[str, tuple]: Dict with formatted key(s) and
            command tuple(s)
        :raises ValueError: If cmd_type or variant is invalid
        :raises TypeError: If template structure is malformed
        :raises KeyError: If required format keys are missing
        """
        templates = getattr(self, "_run_templates", None)
        if templates is None:
            raise AttributeError(
                "_get_template_command requires _run_templates to be defined"
            )

        raw_template = templates.get(cmd_type)
        if raw_template is None:
            raise ValueError(f"[{cmd_type}] invalid template")

        # Check if template has variants and none specified
        if variant is None and "variants" in raw_template:
            # Compile commands for ALL variants
            result: Dict[str, tuple] = {}
            for var_name in raw_template["variants"].keys():
                result.update(
                    self._get_template_command(cmd_type, var_name, **fmt_kwargs)
                )
            return result

        # Single command (either specific variant or no variants)
        template = self._get_run_template(cmd_type, variant)
        cmd = template["cmd"]
        cmd_tuple = tuple(
            arg.format(**fmt_kwargs) if "{" in arg else arg for arg in cmd
        )

        # Build key: cmd_type_kwarg_vals_variant
        key_parts = [cmd_type]
        key_parts.extend(list(fmt_kwargs.values()))
        if variant is not None:
            key_parts.append(variant)
        key = "_".join(str(p) for p in key_parts)

        return {key: cmd_tuple}

    @typechecked
    def _parse_template_result(
        self,
        run_result: Dict[str, Any],
        prefix: str,
        key: str,
    ) -> tuple:
        """Parse command result(s) for a template key.

        Handles both simple templates (single command) and variant
        templates (multiple command variants). For variants, tries
        each until one succeeds.

        :param Dict[str, Any] run_result: Command results dict from _run()
        :param str prefix: Prefix for result keys (e.g., path or
            command name)
        :param str key: Template key in _run_templates
        :returns tuple[Dict[str, Any], list[Exception]]: Tuple of
            (parsed_data dict, list of errors). On success, errors
            list is empty.
        """
        templates = getattr(self, "_run_templates", None)
        if templates is None:
            raise AttributeError(
                "_parse_template_result requires _run_templates to be defined"
            )

        template = templates.get(key)
        if template is None:
            return {}, []

        errors: list = []
        data: Dict[str, Any] = {}

        if "variants" in template:
            # Template with variants - try each until one succeeds
            shared_parser = template.get("parser")
            for variant, variant_entry in template["variants"].items():
                result_key = f"{key}_{prefix}_{variant}"
                result = run_result.get(result_key)
                if result is not None:
                    parser = variant_entry.get("parser", shared_parser)
                    if parser is None:
                        raise ValueError(
                            f"[{key}] No parser for variant '{variant}'"
                        )
                    data, error = parser(result)
                    if error:
                        errors.extend(
                            error if isinstance(error, list) else [error]
                        )
                    if data and not error:
                        errors = []
                        break
        else:
            # Simple template - single command
            result_key = f"{key}_{prefix}"
            result = run_result.get(result_key)
            if result is not None:
                parser = template.get("parser")
                if parser is None:
                    raise ValueError(f"[{key}] No parser defined")
                data, error = parser(result)
                if error:
                    errors.extend(
                        error if isinstance(error, list) else [error]
                    )

        return data, errors
