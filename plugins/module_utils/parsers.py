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

"""Validator functions for command specifications.

Validator functions receive (parsed_output, e_prefix) and return:
    Optional[Exception] - None if valid, exception if invalid
"""

from __future__ import annotations

from typing import Optional

from ansible_collections.o0_o.utils.plugins.module_utils.typeguard_compat import (  # noqa: E501
    typechecked,
)


@typechecked
def strip_only(
    rc: int,
    output: str,
    e_prefix: str,
) -> tuple[str, None]:
    """Strip whitespace from command output.

    Simple parser that strips leading/trailing whitespace from output.

    :param int rc: Command return code (unused)
    :param str output: Raw command output
    :param str e_prefix: Error prefix for error messages (unused)
    :returns tuple[str, None]: (stripped_output, None)
    """
    del rc, e_prefix  # unused
    return output.strip(), None


@typechecked
def validate_hello_world(
    parsed_output: str,
    e_prefix: str,
) -> Optional[ValueError]:
    """Validate hello_world command output.

    :param str parsed_output: Parsed command output to validate
    :param str e_prefix: Error prefix for error messages
    :returns Optional[ValueError]: Error if validation fails, None if ok
    """
    if parsed_output != "Hello, world!":
        return ValueError(f"{e_prefix}Bad output: {repr(parsed_output)}")
    return None
