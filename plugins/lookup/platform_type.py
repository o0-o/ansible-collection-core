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

"""Lookup plugin to determine platform type from connection plugin.

Returns 'posix' or 'windows' based on the ansible_connection variable.
Can be used in playbooks, roles, or invoked from action plugins.

Examples:
    # In a playbook
    - debug:
        msg: "Platform is {{ lookup('o0_o.core.platform_type') }}"

    # In a conditional
    - name: Run POSIX-specific task
      command: uname -a
      when: lookup('o0_o.core.platform_type') == 'posix'

    # From an action plugin
    platform = self._templar.template(
        "{{ lookup('o0_o.core.platform_type') }}"
    )
"""

from __future__ import annotations

DOCUMENTATION = r"""
---
name: platform_type
author: oØ.o (@o0-o)
version_added: "0.1.0"
short_description: Get platform type from connection plugin
description:
  - Returns the platform type ('posix' or 'windows') based on the
    current host's C(ansible_connection) variable.
  - Uses the CONNECTION_TYPES mapping from o0_o.core to determine
    platform category.
  - Useful for conditional logic in playbooks or for action plugins
    that need to route to platform-specific modules.
options: {}
notes:
  - This lookup runs on the Ansible controller.
  - The connection type is determined from C(ansible_connection) in
    the current host's variables.
  - Default connection type is 'ssh' if not specified.
seealso:
  - module: ansible.builtin.debug
    description: Print statements during execution
"""

EXAMPLES = r"""
- name: Show current platform type
  ansible.builtin.debug:
    msg: "Running on {{ lookup('o0_o.core.platform_type') }}"

- name: Run platform-specific command
  ansible.builtin.command:
    cmd: uname -a
  when: lookup('o0_o.core.platform_type') == 'posix'

- name: Run Windows-specific command
  ansible.windows.win_command:
    cmd: whoami
  when: lookup('o0_o.core.platform_type') == 'windows'
"""

RETURN = r"""
_raw:
  description: The platform type string.
  type: str
  choices:
    - posix
    - windows
"""

from typing import Any, Optional

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

from ansible_collections.o0_o.core.plugins.module_utils.connection_types import (
    CONNECTION_TYPES,
)


class LookupModule(LookupBase):
    """Lookup plugin to determine platform type from connection."""

    def run(
        self,
        terms: list[Any],
        variables: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> list[str]:
        """Determine platform type from ansible_connection.

        :param list[Any] terms: Unused lookup terms
        :param Optional[dict[str, Any]] variables: Ansible variables
        :param Any kwargs: Additional keyword arguments
        :returns list[str]: Single-element list with platform type
        :raises AnsibleLookupError: If connection type is not recognized
        """
        del terms, kwargs  # unused
        variables = variables or {}

        # Get connection type from hostvars or direct variable
        inventory_hostname = variables.get("inventory_hostname")
        hostvars = variables.get("hostvars", {})
        host_vars = (
            hostvars.get(inventory_hostname, {}) if inventory_hostname else {}
        )

        connection = host_vars.get("ansible_connection") or variables.get(
            "ansible_connection", "ssh"
        )

        # Find matching platform
        for platform, connections in CONNECTION_TYPES.items():
            if connection in connections:
                return [platform]

        # Build error message with all known platforms
        known = ", ".join(
            f"{p} ({', '.join(sorted(c))})"
            for p, c in CONNECTION_TYPES.items()
        )
        raise AnsibleLookupError(
            f"Connection '{connection}' is not recognized. "
            f"Known platforms: {known}"
        )
