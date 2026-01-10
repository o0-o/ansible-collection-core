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

"""Unit tests for CoreActionBase class and command utilities."""

from __future__ import annotations

import pytest
from typeguard import TypeCheckError

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC,
)
from ansible_collections.o0_o.core.plugins.module_utils.command_utils import (
    _get_command_error_prefix,
    process_command_result,
    process_command_spec,
)


class TestGetCommandErrorPrefix:
    """Tests for _get_command_error_prefix function."""

    @pytest.mark.parametrize(
        "impl,cmd_type,expected",
        [
            ("core", "whoami", "[core_whoami] "),
            ("gnu", "stat", "[gnu_stat] "),
            ("bsd", "ls", "[bsd_ls] "),
        ],
    )
    def test_valid_prefix(
        self, impl: str, cmd_type: str, expected: str
    ) -> None:
        """Test prefix generation with valid command objects."""
        cmd_obj = {"implementation": impl, "type": cmd_type}
        assert _get_command_error_prefix(cmd_obj) == expected

    def test_missing_implementation(self) -> None:
        """Test ValueError raised when implementation is missing."""
        cmd_obj = {"type": "whoami"}
        with pytest.raises(ValueError, match="missing implementation"):
            _get_command_error_prefix(cmd_obj)

    def test_missing_type(self) -> None:
        """Test ValueError raised when type is missing."""
        cmd_obj = {"implementation": "core"}
        with pytest.raises(ValueError, match="missing type"):
            _get_command_error_prefix(cmd_obj)

    def test_not_a_dict(self) -> None:
        """Test TypeCheckError raised when command_obj is not a dict."""
        with pytest.raises(TypeCheckError):
            _get_command_error_prefix("not a dict")

    def test_empty_implementation(self) -> None:
        """Test ValueError when implementation is empty string."""
        cmd_obj = {"implementation": "", "type": "whoami"}
        with pytest.raises(ValueError, match="missing implementation"):
            _get_command_error_prefix(cmd_obj)

    def test_empty_type(self) -> None:
        """Test ValueError raised when type is empty string."""
        cmd_obj = {"implementation": "core", "type": ""}
        with pytest.raises(ValueError, match="missing type"):
            _get_command_error_prefix(cmd_obj)


class TestProcessCommandResult:
    """Tests for process_command_result function."""

    def test_successful_command_no_parser(self) -> None:
        """Test processing successful command without parser."""
        cmd_completed = {
            "implementation": "core",
            "type": "whoami",
            "rc": 0,
            "stdout": "testuser\n",
            "stderr": "",
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "testuser"
        assert errors is None

    def test_successful_command_strips_newlines(self) -> None:
        """Test that trailing newlines are stripped from output."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "output\n\n",
            "stderr": "",
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "output"

    def test_successful_command_strips_carriage_returns(self) -> None:
        """Test that carriage returns are stripped from output."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "line1\r\nline2\r\n",
            "stderr": "",
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "line1\nline2"

    def test_failed_command_nonzero_rc(self) -> None:
        """Test processing command with non-zero return code."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 1,
            "stdout": "",
            "stderr": "error message",
        }
        output, errors = process_command_result(cmd_completed)
        assert output is None
        assert errors is not None
        assert len(errors) == 1
        assert "exited with code 1" in str(errors[0])
        assert "error message" in str(errors[0])

    def test_failed_command_no_stderr(self) -> None:
        """Test processing failed command with no stderr."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 1,
            "stdout": "",
            "stderr": "",
        }
        output, errors = process_command_result(cmd_completed)
        assert output is None
        assert "No stderr" in str(errors[0])

    def test_custom_non_error_codes(self) -> None:
        """Test processing with custom non-error return codes in spec."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "non_error_codes": [0, 1],
            "rc": 1,
            "stdout": "output",
            "stderr": "",
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "output"
        assert errors is None

    def test_with_validator_success(self) -> None:
        """Test processing with validator that passes."""
        cmd_completed = {
            "implementation": "core",
            "type": "hello_world",
            "rc": 0,
            "stdout": "Hello, world!",
            "stderr": "",
            "validator": lambda output, prefix: None,
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "Hello, world!"
        assert errors is None

    def test_with_validator_failure(self) -> None:
        """Test processing with validator that fails."""
        cmd_completed = {
            "implementation": "core",
            "type": "hello_world",
            "rc": 0,
            "stdout": "Wrong output",
            "stderr": "",
            "validator": lambda output, prefix: ValueError(
                "validation failed"
            ),
        }
        output, errors = process_command_result(cmd_completed)
        assert output is None
        assert errors is not None
        assert "validation failed" in str(errors[0])

    def test_with_parser_success(self) -> None:
        """Test processing with parser that succeeds."""

        def parser(rc, output, prefix):
            return output.upper(), None

        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "hello",
            "stderr": "",
            "parser": parser,
        }
        output, errors = process_command_result(cmd_completed)
        assert output == "HELLO"
        assert errors is None

    def test_with_parser_failure(self) -> None:
        """Test processing with parser that returns errors."""

        def parser(rc, output, prefix):
            return None, [ValueError("parse error")]

        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "data",
            "stderr": "",
            "parser": parser,
        }
        output, errors = process_command_result(cmd_completed)
        assert output is None
        assert "parse error" in str(errors[0])

    def test_missing_rc(self) -> None:
        """Test ValueError raised when rc is missing."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "stdout": "output",
            "stderr": "",
        }
        with pytest.raises(ValueError, match="missing 'rc'"):
            process_command_result(cmd_completed)

    def test_missing_stdout(self) -> None:
        """Test ValueError raised when stdout is missing."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stderr": "",
        }
        with pytest.raises(ValueError, match="missing 'stdout'"):
            process_command_result(cmd_completed)

    def test_non_callable_parser(self) -> None:
        """Test TypeError raised when parser is not callable."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "output",
            "stderr": "",
            "parser": "not callable",
        }
        with pytest.raises(TypeError, match="Parser is not callable"):
            process_command_result(cmd_completed)

    def test_non_callable_validator(self) -> None:
        """Test TypeError raised when validator is not callable."""
        cmd_completed = {
            "implementation": "core",
            "type": "test",
            "rc": 0,
            "stdout": "output",
            "stderr": "",
            "validator": "not callable",
        }
        with pytest.raises(TypeError, match="Validator is not callable"):
            process_command_result(cmd_completed)


class TestProcessCommandSpec:
    """Tests for process_command_spec function."""

    def test_whoami_spec(self) -> None:
        """Test processing whoami command spec."""
        requests = process_command_spec(COMMAND_SPEC, "whoami")
        assert len(requests) == 1
        request = requests[0]
        assert request["implementation"] == "core"
        assert request["type"] == "whoami"
        assert request["command"] == ("whoami",)
        assert request["lookup"] == "whoami"

    def test_hello_world_spec(self) -> None:
        """Test processing hello_world command spec."""
        requests = process_command_spec(COMMAND_SPEC, "hello_world")
        assert len(requests) == 1
        request = requests[0]
        assert request["implementation"] == "core"
        assert request["type"] == "hello_world"
        assert request["command"] == ("echo", "Hello, world!")
        assert "validator" in request

    def test_nonexistent_command(self) -> None:
        """Test processing nonexistent command returns empty list."""
        requests = process_command_spec(COMMAND_SPEC, "nonexistent")
        assert requests == []

    def test_template_formatting(self) -> None:
        """Test that templates are properly formatted with kwargs."""
        custom_spec = {
            "test": {
                "greet": {
                    "template": ("echo", "Hello, {name}!"),
                }
            }
        }
        requests = process_command_spec(custom_spec, "greet", name="Alice")
        assert len(requests) == 1
        assert requests[0]["command"] == ("echo", "Hello, Alice!")

    def test_string_template(self) -> None:
        """Test processing string template instead of tuple."""
        custom_spec = {
            "test": {
                "cmd": {
                    "template": "echo hello",
                }
            }
        }
        requests = process_command_spec(custom_spec, "cmd")
        assert len(requests) == 1
        assert requests[0]["command"] == "echo hello"

    def test_missing_template(self) -> None:
        """Test ValueError raised when template is missing."""
        custom_spec = {
            "test": {
                "cmd": {},
            }
        }
        with pytest.raises(ValueError, match="missing a template"):
            process_command_spec(custom_spec, "cmd")

    def test_empty_template(self) -> None:
        """Test ValueError raised when template is empty."""
        custom_spec = {
            "test": {
                "cmd": {
                    "template": (),
                }
            }
        }
        with pytest.raises(ValueError, match="Command is empty"):
            process_command_spec(custom_spec, "cmd")


class TestDefInventoryHostname:
    """Tests for _def_inventory_hostname method."""

    def test_from_task_vars(self, base) -> None:
        """Test hostname retrieved from task_vars."""
        result = base._def_inventory_hostname(
            {"inventory_hostname": "testhost"}
        )
        assert result == "testhost"
        assert base.inventory_hostname == "testhost"

    def test_fallback_to_task(self, base) -> None:
        """Test hostname fallback to task vars mapping."""
        base._task.vars = {"inventory_hostname": "taskhost"}
        result = base._def_inventory_hostname({})
        assert result == "taskhost"
        assert base.inventory_hostname == "taskhost"

    def test_fallback_to_localhost(self, base) -> None:
        """Test hostname fallback to localhost."""
        base._task.vars = {}
        result = base._def_inventory_hostname({})
        assert result == "localhost"
        assert base.inventory_hostname == "localhost"

    def test_none_task_vars(self, base) -> None:
        """Test with None task_vars."""
        base._task.vars = {}
        result = base._def_inventory_hostname(None)
        assert result == "localhost"


class TestGetConnectionType:
    """Tests for _get_connection_type method."""

    @pytest.mark.parametrize("connection", ["ssh", "local", "winrm", "psrp"])
    def test_connection_types(self, base, connection: str) -> None:
        """Test connection type detection for various types."""
        base._play_context.connection = connection
        assert base._get_connection_type() == connection

    def test_default_connection(self, base) -> None:
        """Test default connection type when not set."""
        delattr(base._play_context, "connection")
        assert base._get_connection_type() == "ssh"
