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

"""Command specification processing utilities.

Standalone functions for processing command specifications, building
error prefixes, and handling command results. These functions are
designed to be used with COMMAND_SPEC dictionaries imported by the
calling module.

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

from collections.abc import Callable, Iterable
from typing import Any, Optional, Union

from ansible_collections.o0_o.utils.plugins.module_utils.typeguard_compat import (  # noqa: E501
    typechecked,
)


@typechecked
def _get_command_error_prefix(command_obj: dict[str, Any]) -> str:
    """Build error prefix string from command object metadata.

    :param dict[str, Any] command_obj: Command object with
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
def process_command_spec(
    spec: dict[str, dict[str, Any]],
    cmd_type: str,
    **cmd_kwargs: str,
) -> list[dict[str, Any]]:
    """Process command spec and return list of command requests.

    Looks up cmd_type in spec across all implementations and builds
    command request dicts with formatted templates.

    :param dict[str, dict[str, Any]] spec: Command specification dict
    :param str cmd_type: Command type to look up
    :param **cmd_kwargs: Format arguments for command template
    :returns list[dict[str, Any]]: List of command request dicts
    :raises TypeError: If spec structure is malformed
    :raises ValueError: If template is missing or empty
    """
    results: list[dict[str, Any]] = []

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
            e_prefix = _get_command_error_prefix(cmd_request)
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
def process_command_result(
    cmd_completed: dict[str, Any],
    non_error_codes: Optional[list[int]] = None,
    parser_args: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[list]]:
    """Process command result: validate, parse, and validate output.

    Extracts stdout from the command result, optionally runs a
    parser, and optionally runs a validator. Returns parsed output
    or errors.

    :param dict[str, Any] cmd_completed: Completed command dict
        with 'result' key containing rc, stdout, stderr, plus
        optional 'parser' and 'validator' callables
    :param Optional[list[int]] non_error_codes: Return codes
        considered non-error. Defaults to [0]
    :param Optional[dict[str, Any]] parser_args: Additional keyword
        arguments to pass to the parser function
    :returns tuple[Optional[str], Optional[list]]:
        (parsed_output, None) on success, or (None, [errors]) on
        failure
    :raises TypeError: If cmd_completed or result is not a dict
    :raises ValueError: If required fields are missing or malformed
    """
    if non_error_codes is None:
        non_error_codes = [0]

    if not isinstance(cmd_completed, dict):
        raise TypeError("Completed command not a dict")

    e_prefix = _get_command_error_prefix(cmd_completed)

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
        if parser_args:
            if not isinstance(parser_args, dict):
                raise TypeError(f"{e_prefix}parser_args is not a dict")
            parsed_output, parse_errors = parser(
                rc, output, e_prefix, **parser_args
            )
        else:
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
def display_longest_command(
    display: Any,
    inventory_hostname: str,
    commands_result: dict[str, Any],
    context: str = "",
) -> None:
    """Display debug information about the longest running command.

    :param Any display: Ansible Display object with vvv() method
    :param str inventory_hostname: Host identifier for log messages
    :param dict[str, Any] commands_result: Result dict with 'commands'
        key
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
        display.vvv(
            f"[{inventory_hostname}] Longest command{context_str}: "
            f"{longest_cmd} took {longest_elapsed}s"
        )
    else:
        display.vvv(
            f"[{inventory_hostname}] All commands{context_str} "
            f"completed in under 1 second"
        )


@typechecked
def format_error_message(
    errors: Iterable[Union[Exception, str]],
    max_display: int = 3,
) -> str:
    """Format a collection of errors into a human-readable message.

    Generates a message string that communicates the scope and nature of
    errors encountered. For single errors, provides the error type and
    message. For multiple errors, lists them with numbering up to a
    limit, then summarizes any remaining errors.

    :param Iterable[Union[Exception, str]] errors: Collection of
        errors to format. Can be Exception instances or strings.
    :param int max_display: Maximum number of individual errors to
        display before summarizing. Defaults to 3.
    :returns str: Formatted error message string
    :raises ValueError: If errors is empty or max_display < 1
    """
    if max_display < 1:
        raise ValueError("max_display must be at least 1")

    error_list = list(errors)

    if not error_list:
        raise ValueError("errors iterable is empty")

    total = len(error_list)

    def format_single(err: Union[Exception, str]) -> str:
        """Format a single error with type name if applicable."""
        if isinstance(err, Exception):
            return f"{type(err).__name__}: {err}"
        return str(err)

    # Single error - simple format
    if total == 1:
        return f"1 error encountered: {format_single(error_list[0])}"

    # Multiple errors
    parts = [f"{total} errors encountered:"]

    # Add numbered errors up to the limit
    display_count = min(total, max_display)
    for i, err in enumerate(error_list[:display_count], start=1):
        parts.append(f"({i}) {format_single(err)}")

    # Add summary of remaining errors if any
    remaining = total - display_count
    if remaining > 0:
        if remaining == 1:
            parts.append("... and 1 other error")
        else:
            parts.append(f"... and {remaining} other errors")

    return " ".join(parts)
