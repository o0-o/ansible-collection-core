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
