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

"""Unit tests for command_utils module."""

from __future__ import annotations

import pytest
from typeguard import TypeCheckError

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC,
)
from ansible_collections.o0_o.core.plugins.module_utils.command_utils import (
    _get_command_error_prefix,
    _get_command_template_placeholders,
    process_all_command_results,
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
        """Test processing with custom non-error return codes."""
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

        def parser(output, prefix):
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

        def parser(output, prefix):
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


class TestProcessAllCommandResults:
    """Tests for process_all_command_results function."""

    def test_single_command_single_type(self) -> None:
        """Test processing single command returns dict keyed by type."""
        commands = [
            {
                "implementation": "core",
                "type": "whoami",
                "rc": 0,
                "stdout": "testuser\n",
                "stderr": "",
            }
        ]
        results = process_all_command_results(commands)
        assert "whoami" in results
        assert len(results["whoami"]) == 1
        assert results["whoami"][0]["implementation"] == "core"
        assert results["whoami"][0]["parsed"] == "testuser"
        assert results["whoami"][0]["errors"] is None

    def test_multiple_implementations_same_type(self) -> None:
        """Test multiple implementations of same type are grouped."""
        commands = [
            {
                "implementation": "gnu",
                "type": "stat",
                "rc": 0,
                "stdout": "gnu output",
                "stderr": "",
            },
            {
                "implementation": "bsd",
                "type": "stat",
                "rc": 0,
                "stdout": "bsd output",
                "stderr": "",
            },
        ]
        results = process_all_command_results(commands)
        assert "stat" in results
        assert len(results["stat"]) == 2
        assert results["stat"][0]["implementation"] == "gnu"
        assert results["stat"][0]["parsed"] == "gnu output"
        assert results["stat"][1]["implementation"] == "bsd"
        assert results["stat"][1]["parsed"] == "bsd output"

    def test_multiple_types(self) -> None:
        """Test multiple command types are separated correctly."""
        commands = [
            {
                "implementation": "core",
                "type": "whoami",
                "rc": 0,
                "stdout": "root",
                "stderr": "",
            },
            {
                "implementation": "gnu",
                "type": "stat",
                "rc": 0,
                "stdout": "file info",
                "stderr": "",
            },
        ]
        results = process_all_command_results(commands)
        assert "whoami" in results
        assert "stat" in results
        assert len(results["whoami"]) == 1
        assert len(results["stat"]) == 1

    def test_failed_command_has_errors(self) -> None:
        """Test failed command populates errors field."""
        commands = [
            {
                "implementation": "bsd",
                "type": "stat",
                "rc": 1,
                "stdout": "",
                "stderr": "file not found",
            }
        ]
        results = process_all_command_results(commands)
        assert results["stat"][0]["parsed"] is None
        assert results["stat"][0]["errors"] is not None
        assert len(results["stat"][0]["errors"]) == 1

    def test_empty_list(self) -> None:
        """Test empty list returns empty dict."""
        results = process_all_command_results([])
        assert results == {}

    def test_missing_type_raises(self) -> None:
        """Test ValueError raised when type is missing."""
        commands = [
            {
                "implementation": "core",
                "rc": 0,
                "stdout": "output",
                "stderr": "",
            }
        ]
        with pytest.raises(ValueError, match="missing 'type'"):
            process_all_command_results(commands)

    def test_missing_implementation_raises(self) -> None:
        """Test ValueError raised when implementation is missing."""
        commands = [
            {
                "type": "whoami",
                "rc": 0,
                "stdout": "output",
                "stderr": "",
            }
        ]
        with pytest.raises(ValueError, match="missing 'implementation'"):
            process_all_command_results(commands)


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

    def test_command_formatting(self) -> None:
        """Test that commands are properly formatted with kwargs."""
        custom_spec = {
            "test": {
                "greet": {
                    "command": ("echo", "Hello, {name}!"),
                }
            }
        }
        requests = process_command_spec(custom_spec, "greet", name="Alice")
        assert len(requests) == 1
        assert requests[0]["command"] == ("echo", "Hello, Alice!")

    def test_string_command(self) -> None:
        """Test processing string command instead of tuple."""
        custom_spec = {
            "test": {
                "cmd": {
                    "command": "echo hello",
                }
            }
        }
        requests = process_command_spec(custom_spec, "cmd")
        assert len(requests) == 1
        assert requests[0]["command"] == "echo hello"

    def test_missing_command(self) -> None:
        """Test ValueError raised when command is missing."""
        custom_spec = {
            "test": {
                "cmd": {},
            }
        }
        with pytest.raises(ValueError, match="missing a command"):
            process_command_spec(custom_spec, "cmd")

    def test_empty_command(self) -> None:
        """Test ValueError raised when command is empty."""
        custom_spec = {
            "test": {
                "cmd": {
                    "command": (),
                }
            }
        }
        with pytest.raises(ValueError, match="Command is empty"):
            process_command_spec(custom_spec, "cmd")


class TestProcessCommandSpecListExpansion:
    """Tests for list expansion in process_command_spec."""

    def test_scalar_kwargs_unchanged(self) -> None:
        """Test that scalar kwargs work as before."""
        custom_spec = {"test": {"cmd": {"command": ("echo", "{path}")}}}
        requests = process_command_spec(custom_spec, "cmd", path="/tmp/file")
        assert len(requests) == 1
        assert requests[0]["command"] == ("echo", "/tmp/file")
        assert requests[0]["args"] == {"path": "/tmp/file"}

    def test_single_list_expansion(self) -> None:
        """Test expansion of single list kwarg."""
        custom_spec = {"test": {"cmd": {"command": ("echo", "{path}")}}}
        requests = process_command_spec(
            custom_spec, "cmd", path=["/tmp/a", "/tmp/b"]
        )
        assert len(requests) == 2
        assert requests[0]["command"] == ("echo", "/tmp/a")
        assert requests[0]["args"] == {"path": "/tmp/a"}
        assert requests[1]["command"] == ("echo", "/tmp/b")
        assert requests[1]["args"] == {"path": "/tmp/b"}

    def test_cartesian_product(self) -> None:
        """Test cartesian product with multiple list kwargs."""
        custom_spec = {"test": {"cmd": {"command": ("cp", "{src}", "{dest}")}}}
        requests = process_command_spec(
            custom_spec,
            "cmd",
            src=["/a", "/b"],
            dest=["/x", "/y"],
        )
        assert len(requests) == 4
        commands = [r["command"] for r in requests]
        assert ("cp", "/a", "/x") in commands
        assert ("cp", "/a", "/y") in commands
        assert ("cp", "/b", "/x") in commands
        assert ("cp", "/b", "/y") in commands

    def test_mixed_scalar_and_list(self) -> None:
        """Test mixed scalar and list kwargs."""
        custom_spec = {
            "test": {"cmd": {"command": ("chmod", "{mode}", "{path}")}}
        }
        requests = process_command_spec(
            custom_spec,
            "cmd",
            mode="644",
            path=["/a", "/b"],
        )
        assert len(requests) == 2
        assert requests[0]["command"] == ("chmod", "644", "/a")
        assert requests[1]["command"] == ("chmod", "644", "/b")

    def test_empty_list_no_requests(self) -> None:
        """Test that empty list produces no requests."""
        custom_spec = {"test": {"cmd": {"command": ("echo", "{path}")}}}
        requests = process_command_spec(custom_spec, "cmd", path=[])
        assert len(requests) == 0

    def test_kwargs_supplied_but_not_used(self) -> None:
        """Test args is empty when kwargs not in template."""
        custom_spec = {"test": {"cmd": {"command": ("whoami",)}}}
        requests = process_command_spec(
            custom_spec, "cmd", path="/tmp", mode="644"
        )
        assert len(requests) == 1
        assert requests[0]["command"] == ("whoami",)
        assert requests[0]["args"] == {}

    def test_single_item_list_like_scalar(self) -> None:
        """Test single-item list behaves like scalar."""
        custom_spec = {"test": {"cmd": {"command": ("echo", "{path}")}}}
        requests = process_command_spec(custom_spec, "cmd", path=["/tmp/file"])
        assert len(requests) == 1
        assert requests[0]["command"] == ("echo", "/tmp/file")

    def test_string_command_with_list(self) -> None:
        """Test list expansion with string command."""
        custom_spec = {"test": {"cmd": {"command": "echo {path}"}}}
        requests = process_command_spec(custom_spec, "cmd", path=["/a", "/b"])
        assert len(requests) == 2
        assert requests[0]["command"] == "echo /a"
        assert requests[1]["command"] == "echo /b"

    def test_gnu_alt_with_list_expansion(self) -> None:
        """Test GNU alternate commands with list expansion."""
        custom_spec = {"gnu": {"cmd": {"command": ("stat", "{path}")}}}
        requests = process_command_spec(custom_spec, "cmd", path=["/a", "/b"])
        # 2 paths x 2 (stat + gstat) = 4 requests
        assert len(requests) == 4
        commands = [r["command"] for r in requests]
        assert ("stat", "/a") in commands
        assert ("stat", "/b") in commands
        assert ("gstat", "/a") in commands
        assert ("gstat", "/b") in commands

    def test_unused_kwargs_no_duplicates(self) -> None:
        """Test that unused kwargs don't cause duplicate commands."""
        custom_spec = {
            "core": {
                "uses_path": {"command": ("stat", "{path}")},
                "no_path": {"command": ("whoami",)},
            }
        }
        requests = process_command_spec(custom_spec, path=["/a", "/b"])
        # uses_path: 2 requests (one per path)
        # no_path: 1 request (path kwarg not used)
        assert len(requests) == 3
        commands = [r["command"] for r in requests]
        assert ("stat", "/a") in commands
        assert ("stat", "/b") in commands
        assert ("whoami",) in commands
        # Verify no duplicate whoami
        assert commands.count(("whoami",)) == 1
        # Verify args preserved correctly
        for req in requests:
            if req["command"] == ("whoami",):
                assert req["args"] == {}
            elif req["command"] == ("stat", "/a"):
                assert req["args"] == {"path": "/a"}
            elif req["command"] == ("stat", "/b"):
                assert req["args"] == {"path": "/b"}

    def test_mixed_used_and_unused_kwargs(self) -> None:
        """Test mixed used and unused kwargs across commands."""
        custom_spec = {
            "core": {
                "needs_src": {"command": ("cat", "{src}")},
                "needs_dest": {"command": ("touch", "{dest}")},
                "needs_both": {"command": ("cp", "{src}", "{dest}")},
                "needs_none": {"command": ("pwd",)},
            }
        }
        requests = process_command_spec(
            custom_spec,
            src=["/a", "/b"],
            dest=["/x", "/y"],
        )
        # needs_src: 2 requests (expands src only)
        # needs_dest: 2 requests (expands dest only)
        # needs_both: 4 requests (cartesian product)
        # needs_none: 1 request (no expansion)
        assert len(requests) == 9

        commands = [r["command"] for r in requests]
        # needs_src variations
        assert ("cat", "/a") in commands
        assert ("cat", "/b") in commands
        # needs_dest variations
        assert ("touch", "/x") in commands
        assert ("touch", "/y") in commands
        # needs_both variations (cartesian product)
        assert ("cp", "/a", "/x") in commands
        assert ("cp", "/a", "/y") in commands
        assert ("cp", "/b", "/x") in commands
        assert ("cp", "/b", "/y") in commands
        # needs_none (single)
        assert ("pwd",) in commands
        assert commands.count(("pwd",)) == 1


class TestGetCommandTemplatePlaceholders:
    """Tests for _get_command_template_placeholders function."""

    def test_string_single_placeholder(self) -> None:
        """Test extracting single placeholder from string."""
        result = _get_command_template_placeholders("echo {path}")
        assert result == {"path"}

    def test_string_multiple_placeholders(self) -> None:
        """Test extracting multiple placeholders from string."""
        result = _get_command_template_placeholders("cp {src} {dest}")
        assert result == {"src", "dest"}

    def test_string_no_placeholders(self) -> None:
        """Test string with no placeholders."""
        result = _get_command_template_placeholders("whoami")
        assert result == set()

    def test_tuple_single_placeholder(self) -> None:
        """Test extracting placeholder from tuple command."""
        result = _get_command_template_placeholders(("stat", "{path}"))
        assert result == {"path"}

    def test_tuple_multiple_placeholders(self) -> None:
        """Test extracting multiple placeholders from tuple."""
        result = _get_command_template_placeholders(("cp", "{src}", "{dest}"))
        assert result == {"src", "dest"}

    def test_tuple_no_placeholders(self) -> None:
        """Test tuple with no placeholders."""
        result = _get_command_template_placeholders(("whoami",))
        assert result == set()

    def test_tuple_mixed_placeholders(self) -> None:
        """Test tuple with mix of placeholder and literal args."""
        result = _get_command_template_placeholders(("chmod", "644", "{path}"))
        assert result == {"path"}

    def test_repeated_placeholder(self) -> None:
        """Test that repeated placeholders are deduplicated."""
        result = _get_command_template_placeholders("echo {x} {x} {x}")
        assert result == {"x"}

    def test_empty_string(self) -> None:
        """Test empty string returns empty set."""
        result = _get_command_template_placeholders("")
        assert result == set()

    def test_empty_tuple(self) -> None:
        """Test empty tuple returns empty set."""
        result = _get_command_template_placeholders(())
        assert result == set()
