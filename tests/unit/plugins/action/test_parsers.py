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

"""Unit tests for parsers module."""

from __future__ import annotations

import pytest
from typeguard import TypeCheckError

from ansible_collections.o0_o.core.plugins.module_utils.parsers import (
    strip_only,
    validate_hello_world,
)


class TestStripOnly:
    """Tests for strip_only parser function."""

    @pytest.mark.parametrize("input_str,expected", [
        ("hello\n", "hello"),
        ("  hello", "hello"),
        ("  hello  \n", "hello"),
        ("hello world", "hello world"),
        ("", ""),
        ("   \n\t  ", ""),
    ])
    def test_strip_whitespace(self, input_str: str, expected: str) -> None:
        """Test parser strips leading/trailing whitespace correctly."""
        output, errors = strip_only(0, input_str, "[test] ")
        assert output == expected
        assert errors is None

    def test_ignores_rc(self) -> None:
        """Test parser ignores return code."""
        output, errors = strip_only(1, "hello", "[test] ")
        assert output == "hello"
        assert errors is None


class TestValidateHelloWorld:
    """Tests for validate_hello_world function."""

    def test_valid_output(self) -> None:
        """Test validation passes for correct output."""
        result = validate_hello_world("Hello, world!", "[core_hello_world] ")
        assert result is None

    def test_fails_with_trailing_whitespace(self) -> None:
        """Test validation fails when output has trailing whitespace.

        Note: strip_only parser should be used before validator to strip
        whitespace. Validator requires exact match.
        """
        result = validate_hello_world("Hello, world!  ", "[core_hello_world] ")
        assert result is not None
        assert isinstance(result, ValueError)

    def test_fails_with_leading_whitespace(self) -> None:
        """Test validation fails when output has leading whitespace.

        Note: strip_only parser should be used before validator to strip
        whitespace. Validator requires exact match.
        """
        result = validate_hello_world("  Hello, world!", "[core_hello_world] ")
        assert result is not None
        assert isinstance(result, ValueError)

    def test_invalid_output_wrong_text(self) -> None:
        """Test validation fails for incorrect text."""
        result = validate_hello_world("Hello, World!", "[core_hello_world] ")
        assert result is not None
        assert isinstance(result, ValueError)
        assert "[core_hello_world]" in str(result)
        assert "Bad output" in str(result)

    def test_invalid_output_empty(self) -> None:
        """Test validation fails for empty output."""
        result = validate_hello_world("", "[core_hello_world] ")
        assert result is not None
        assert isinstance(result, ValueError)

    def test_invalid_output_partial(self) -> None:
        """Test validation fails for partial output."""
        result = validate_hello_world("Hello", "[core_hello_world] ")
        assert result is not None
        assert isinstance(result, ValueError)

    def test_error_prefix_in_message(self) -> None:
        """Test that error prefix is included in error message."""
        result = validate_hello_world("wrong", "[test_prefix] ")
        assert result is not None
        assert "[test_prefix]" in str(result)

    def test_type_error_on_non_string_output(self) -> None:
        """Test TypeCheckError raised when output is not a string."""
        with pytest.raises(TypeCheckError):
            validate_hello_world(123, "[core_hello_world] ")  # type: ignore

    def test_type_error_on_non_string_prefix(self) -> None:
        """Test TypeCheckError raised when prefix is not a string."""
        with pytest.raises(TypeCheckError):
            validate_hello_world("Hello, world!", 123)  # type: ignore
