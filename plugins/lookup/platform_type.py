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
    host's C(ansible_connection) variable.
  - Uses the CONNECTION_TYPES mapping from o0_o.core to determine
    platform category.
  - Useful for conditional logic in playbooks or for action plugins
    that need to route to platform-specific modules.
options:
  host:
    description:
      - Inventory hostname to check platform type for.
      - If not specified, uses the current C(inventory_hostname).
      - Mutually exclusive with C(connection).
    type: str
    default: null
  connection:
    description:
      - Connection plugin name to check directly.
      - Bypasses host variable lookup entirely.
      - Mutually exclusive with C(host).
    type: str
    default: null
notes:
  - This lookup runs on the Ansible controller.
  - The connection type is determined from C(ansible_connection) in
    the host's variables.
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

- name: Check platform type of a different host
  ansible.builtin.debug:
    msg: >-
      webserver1 is {{ lookup('o0_o.core.platform_type', host='webserver1') }}

- name: Check platform type for a specific connection
  ansible.builtin.debug:
    msg: "winrm is {{ lookup('o0_o.core.platform_type', connection='winrm') }}"
"""

RETURN = r"""
_raw:
  description: The platform type string.
  type: str
  choices:
    - posix
    - windows
"""

from typing import Any

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    CONNECTION_BY_PLATFORM,
)
from ansible_collections.o0_o.core.plugins.module_utils.localhost import (
    LOCALHOST_NAMES,
)


class LookupModule(LookupBase):
    """Lookup plugin to determine platform type from connection."""

    def run(self, terms: list[Any], **kwargs: Any) -> list[str]:
        """Determine platform type from ansible_connection.

        Accesses variables directly via self._templar rather than
        accepting a variables parameter.

        :param list[Any] terms: Unused lookup terms
        :param Any kwargs: host or connection options
        :returns list[str]: Single-element list with platform type
        :raises AnsibleLookupError: If connection type is not recognized
        """
        del terms  # unused

        self.set_options(direct=kwargs)
        host = self.get_option("host")
        connection = self.get_option("connection")

        # Validate mutual exclusivity
        if host and connection:
            raise AnsibleLookupError(
                "Options 'host' and 'connection' are mutually exclusive"
            )

        # If connection specified directly, use it
        if connection:
            conn_type = connection
        else:
            # Access variables directly from templar
            variables = self._templar.available_variables
            hostvars = variables.get("hostvars", {})

            # Use specified host or current inventory_hostname
            # Default to localhost if not available
            target_host = (
                host or variables.get("inventory_hostname") or "localhost"
            )
            host_vars = hostvars.get(target_host, {}) if target_host else {}

            conn_type = host_vars.get("ansible_connection") or variables.get(
                "ansible_connection"
            )

            # Default to local for localhost, ssh otherwise
            if not conn_type:
                conn_type = (
                    "local" if target_host in LOCALHOST_NAMES else "ssh"
                )

        # Find matching platform
        for platform, connections in CONNECTION_BY_PLATFORM.items():
            if conn_type in connections:
                return [platform]

        # Build error message with all known platforms
        known = ", ".join(
            f"{p} ({', '.join(sorted(c))})"
            for p, c in CONNECTION_BY_PLATFORM.items()
        )
        raise AnsibleLookupError(
            f"Connection '{conn_type}' is not recognized. "
            f"Known platforms: {known}"
        )
