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

"""Unit tests for command_spec module."""

from __future__ import annotations

import pytest

from ansible_collections.o0_o.core.plugins.module_utils.command_spec import (
    COMMAND_SPEC,
)


class TestCommandSpecStructure:
    """Tests for COMMAND_SPEC data structure validation."""

    def test_has_core_implementation(self) -> None:
        """Test COMMAND_SPEC contains core implementation."""
        assert "core" in COMMAND_SPEC

    def test_core_has_hello_world(self) -> None:
        """Test core implementation contains hello_world command."""
        assert "hello_world" in COMMAND_SPEC["core"]

    def test_core_has_whoami(self) -> None:
        """Test core implementation contains whoami command."""
        assert "whoami" in COMMAND_SPEC["core"]

    def test_hello_world_has_template(self) -> None:
        """Test hello_world command has template."""
        assert "template" in COMMAND_SPEC["core"]["hello_world"]

    def test_hello_world_has_validator(self) -> None:
        """Test hello_world command has validator."""
        assert "validator" in COMMAND_SPEC["core"]["hello_world"]

    def test_hello_world_validator_is_callable(self) -> None:
        """Test hello_world validator is callable."""
        validator = COMMAND_SPEC["core"]["hello_world"]["validator"]
        assert callable(validator)

    def test_whoami_has_template(self) -> None:
        """Test whoami command has template."""
        assert "template" in COMMAND_SPEC["core"]["whoami"]

    def test_whoami_has_no_validator(self) -> None:
        """Test whoami command has no validator (optional)."""
        assert "validator" not in COMMAND_SPEC["core"]["whoami"]

    def test_hello_world_template_is_tuple(self) -> None:
        """Test hello_world template is a tuple."""
        template = COMMAND_SPEC["core"]["hello_world"]["template"]
        assert isinstance(template, tuple)

    def test_whoami_template_is_tuple(self) -> None:
        """Test whoami template is a tuple."""
        template = COMMAND_SPEC["core"]["whoami"]["template"]
        assert isinstance(template, tuple)

    @pytest.mark.parametrize(
        "impl,cmd_type",
        [
            ("core", "hello_world"),
            ("core", "whoami"),
        ],
    )
    def test_all_commands_have_templates(
        self, impl: str, cmd_type: str
    ) -> None:
        """Test all commands have non-empty templates."""
        template = COMMAND_SPEC[impl][cmd_type]["template"]
        assert template, f"{impl}.{cmd_type} has empty template"
