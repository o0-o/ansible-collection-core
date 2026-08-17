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

"""Unit tests for CoreActionBase class."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


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


class TestDefEffectiveUser:
    """Tests for _def_effective_user method."""

    def test_become_with_explicit_user(self, base) -> None:
        """Test effective user is become_user when become is active."""
        base._play_context.become = True
        base._play_context.become_user = "deploy"
        result = base._def_effective_user({})
        assert result == "deploy"
        assert base.effective_user == "deploy"

    def test_become_without_explicit_user(self, base) -> None:
        """Test effective user defaults to root when become
        has no user."""
        base._play_context.become = True
        base._play_context.become_user = None
        result = base._def_effective_user({})
        assert result == "root"
        assert base.effective_user == "root"

    def test_no_become_uses_remote_user(self, base) -> None:
        """Test effective user is remote_user when not becoming."""
        base._play_context.become = False
        base._play_context.remote_user = "ansible"
        base._play_context.connection_user = None
        result = base._def_effective_user({})
        assert result == "ansible"

    def test_no_become_falls_back_to_connection_user(self, base) -> None:
        """Test fallback to connection_user when remote_user is None."""
        base._play_context.become = False
        base._play_context.remote_user = None
        base._play_context.connection_user = "conn_user"
        result = base._def_effective_user({})
        assert result == "conn_user"

    def test_fallback_to_task_vars(self, base) -> None:
        """Test fallback to ansible_user from task_vars."""
        base._play_context.become = False
        base._play_context.remote_user = None
        base._play_context.connection_user = None
        result = base._def_effective_user({"ansible_user": "taskuser"})
        assert result == "taskuser"

    def test_fallback_to_local_user(self, base) -> None:
        """Test fallback to local username as last resort."""
        base._play_context.become = False
        base._play_context.remote_user = None
        base._play_context.connection_user = None
        result = base._def_effective_user({})
        # Should be the local user running the test
        import getpass

        assert result == getpass.getuser()

    def test_become_false_explicitly(self, base) -> None:
        """Test become=False does not use become_user."""
        base._play_context.become = False
        base._play_context.become_user = "nobody"
        base._play_context.remote_user = "ssh_user"
        result = base._def_effective_user({})
        assert result == "ssh_user"


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


def _wire_delegation(base, plugin_result):
    """Wire the task copy and action loader for a delegation test.

    Returns (copied_task, plugin) where copied_task.args is a real
    dict the code under test clears and fills, and plugin.run returns
    plugin_result.
    """
    copied_task = MagicMock()
    copied_task.args = {"stale": "value"}
    base._task.copy.return_value = copied_task

    plugin = MagicMock()
    plugin.run.return_value = plugin_result
    # ActionBase on newer ansible-core replaces the injected
    # shared_loader_obj with the global loader, so swap the attribute
    base._shared_loader_obj = MagicMock()
    base._shared_loader_obj.action_loader.get.return_value = plugin

    return copied_task, plugin


class TestRunAction:
    """Tests for _run_action delegation semantics."""

    def test_recursion_guard(self, base) -> None:
        """Test delegating to the running action raises."""
        with pytest.raises(RecursionError, match="infinite recursion"):
            base._run_action("o0_o.core.test", {})

    def test_recursion_guard_is_case_insensitive(self, base) -> None:
        """Test the recursion guard normalizes case and whitespace."""
        with pytest.raises(RecursionError):
            base._run_action(" O0_O.Core.TEST ", {})

    def test_delegates_args_and_returns_result(self, base) -> None:
        """Test delegated args replace the copied task's args."""
        copied_task, plugin = _wire_delegation(base, {"rc": 0})

        result = base._run_action(
            "o0_o.core.other", {"cmd": "echo hi"}, task_vars={"x": 1}
        )

        assert result == {"rc": 0}
        assert copied_task.args == {"cmd": "echo hi"}
        plugin.run.assert_called_once_with(task_vars={"x": 1})

    def test_no_raw_injection_without_raw(self, base) -> None:
        """Test no raw arg is injected when self.raw is unset."""
        copied_task, plugin = _wire_delegation(base, {})

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert "raw" not in copied_task.args

    def test_no_raw_injection_for_auto(self, base) -> None:
        """Test raw='auto' leaves the delegated plugin's default."""
        copied_task, plugin = _wire_delegation(base, {})
        base.raw = "auto"

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert "raw" not in copied_task.args

    @pytest.mark.parametrize("raw_mode", [True, False])
    def test_strict_bool_raw_propagates(self, base, raw_mode: bool) -> None:
        """Test strict boolean raw modes propagate to the delegate."""
        copied_task, plugin = _wire_delegation(base, {})
        base.raw = raw_mode

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert copied_task.args["raw"] is raw_mode

    def test_auto_learns_raw_from_result(self, base) -> None:
        """Test raw='auto' adopts the delegated result's raw mode."""
        _wire_delegation(base, {"raw": True})
        base.raw = "auto"

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert base.raw is True

    def test_auto_learns_native_from_result(self, base) -> None:
        """Test raw='auto' adopts a native delegated result."""
        _wire_delegation(base, {"raw": False})
        base.raw = "auto"

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert base.raw is False

    def test_raw_result_escalates_non_auto(self, base) -> None:
        """Test a raw delegated result escalates a boolean raw mode."""
        _wire_delegation(base, {"raw": True})
        base.raw = False

        base._run_action("o0_o.core.other", {"cmd": "true"})

        assert base.raw is True

    def test_check_mode_override(self, base) -> None:
        """Test the check_mode override lands on the delegate's task."""
        copied_task, plugin = _wire_delegation(base, {})

        base._run_action("o0_o.core.other", {}, check_mode=True)

        assert plugin._task.check_mode is True

    def test_falls_back_to_execute_module(self, base, monkeypatch) -> None:
        """Test a missing action plugin falls back to the module."""
        base._task.copy.return_value = MagicMock()
        base._shared_loader_obj = MagicMock()
        base._shared_loader_obj.action_loader.get.return_value = None
        execute_module = MagicMock(return_value={"rc": 0, "fallback": True})
        monkeypatch.setattr(base, "_execute_module", execute_module)

        result = base._run_action(
            "o0_o.core.missing", {"a": 1}, task_vars={"x": 1}
        )

        assert result == {"rc": 0, "fallback": True}
        execute_module.assert_called_once_with(
            module_name="o0_o.core.missing",
            module_args={"a": 1},
            task_vars={"x": 1},
        )
