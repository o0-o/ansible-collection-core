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

"""Pytest fixtures for core module_utils unit tests."""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from ansible.plugins.action import ActionBase

from ansible_collections.o0_o.core.plugins.module_utils import (
    CoreActionBase,
)


class TestCoreActionBase(CoreActionBase, ActionBase):
    """Test class that combines CoreActionBase mixin with ActionBase."""

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Dummy run method for testing."""
        return {"changed": False}


@pytest.fixture
def base() -> TestCoreActionBase:
    """Create a TestCoreActionBase instance for unit testing.

    Provides a TestCoreActionBase instance with mocked Ansible
    dependencies for testing CoreActionBase methods.

    :returns: Configured TestCoreActionBase instance with mocked
        dependencies
    """
    base = TestCoreActionBase(
        task=MagicMock(),
        connection=MagicMock(),
        play_context=MagicMock(),
        loader=MagicMock(),
        templar=MagicMock(),
        shared_loader_obj=MagicMock(),
    )

    # Add display mock
    base._display = MagicMock()

    # Initialize inventory_hostname (normally set by action plugin)
    base.inventory_hostname = "localhost"

    # Mock task action for _run_action recursion check
    base._task.action = "o0_o.core.test"

    return base
