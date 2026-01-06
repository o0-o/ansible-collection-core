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

"""Lookup plugin to determine platform from connection plugin.

Returns 'posix' or 'windows' based on the ansible_connection variable.
Can be used in playbooks, roles, or invoked from action plugins.

Examples:
    # In a playbook
    - debug:
        msg: "Platform is {{ lookup('o0_o.core.platform') }}"

    # In a conditional
    - name: Run POSIX-specific task
      command: uname -a
      when: lookup('o0_o.core.platform') == 'posix'

    # From an action plugin
    platform = self._templar.template(
        "{{ lookup('o0_o.core.platform') }}"
    )
"""

from __future__ import annotations

DOCUMENTATION = r"""
---
name: platform
author: oØ.o (@o0-o)
version_added: "0.1.0"
short_description: Get platform from connection plugin
description:
  - Returns the platform ('posix' or 'windows') based on the
    host's C(ansible_connection) variable.
  - Uses the CONNECTION_BY_PLATFORM mapping from o0_o.core to determine
    platform category.
  - Useful for conditional logic in playbooks or for action plugins
    that need to route to platform-specific modules.
options:
  host:
    description:
      - Inventory hostname to check platform for.
      - Can be combined with C(hosts), C(group), and C(groups).
      - Mutually exclusive with C(connection).
    type: str
    default: null
  hosts:
    description:
      - List of inventory hostnames to check platforms for.
      - Can be combined with C(host), C(group), and C(groups).
      - Mutually exclusive with C(connection).
    type: list
    elements: str
    default: []
  group:
    description:
      - Inventory group name to check platforms for.
      - Can be combined with C(host), C(hosts), and C(groups).
      - Mutually exclusive with C(connection).
    type: str
    default: null
  groups:
    description:
      - List of inventory group names to check platforms for.
      - Can be combined with C(host), C(hosts), and C(group).
      - Mutually exclusive with C(connection).
    type: list
    elements: str
    default: []
  connection:
    description:
      - Connection plugin name to check directly.
      - Bypasses host variable lookup entirely.
      - Mutually exclusive with C(host), C(hosts), C(group), and C(groups).
    type: str
    default: null
  wantlist:
    description:
      - Control whether to return a list or single value.
      - When C(true), always returns a list.
      - When C(false), returns a single string if only one platform,
        otherwise returns a list.
      - Default is C(true) for consistency with C(query()).
    type: bool
    default: true
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
- name: Show current platform
  ansible.builtin.debug:
    msg: "Running on {{ lookup('o0_o.core.platform') }}"

- name: Run platform-specific command
  ansible.builtin.command:
    cmd: uname -a
  when: lookup('o0_o.core.platform') == 'posix'

- name: Run Windows-specific command
  ansible.windows.win_command:
    cmd: whoami
  when: lookup('o0_o.core.platform') == 'windows'

- name: Check platform of a different host
  ansible.builtin.debug:
    msg: >-
      webserver1 is {{ lookup('o0_o.core.platform', host='webserver1') }}

- name: Check platform for a specific connection
  ansible.builtin.debug:
    msg: "winrm is {{ lookup('o0_o.core.platform', connection='winrm') }}"

- name: Check platforms for all hosts in a group
  ansible.builtin.debug:
    msg: >-
      webservers platforms:
      {{ lookup('o0_o.core.platform', group='webservers') }}

- name: Check platforms for multiple groups
  ansible.builtin.debug:
    msg: >-
      {{ lookup('o0_o.core.platform', groups=['webservers', 'databases']) }}

- name: Check platforms for multiple hosts
  ansible.builtin.debug:
    msg: "{{ lookup('o0_o.core.platform', hosts=['web1', 'web2', 'db1']) }}"

- name: Combine hosts and groups (additive)
  ansible.builtin.debug:
    msg: >-
      {{ lookup('o0_o.core.platform',
                host='special-server',
                groups=['webservers', 'databases']) }}

- name: Conditionally include tasks if group has Windows hosts
  ansible.builtin.include_tasks: windows_setup.yml
  when: "'windows' in lookup('o0_o.core.platform', group='all')"
"""

RETURN = r"""
_raw:
  description:
    - A list of unique platform strings by default.
    - A single platform string when C(wantlist=false) and only one
      platform is found.
  type: list
  elements: str
  choices:
    - posix
    - windows
"""

from typing import Any, Union

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    CONNECTION_BY_PLATFORM,
)
from ansible_collections.o0_o.core.plugins.module_utils.localhost import (
    LOCALHOST_NAMES,
)


class LookupModule(LookupBase):
    """Lookup plugin to determine platform from connection."""

    def _get_platform_for_connection(self, conn_type: str) -> str:
        """Get platform for a connection type.

        :param str conn_type: Connection plugin name
        :returns str: Platform ('posix' or 'windows')
        :raises AnsibleLookupError: If connection type is not recognized
        """
        for platform, connections in CONNECTION_BY_PLATFORM.items():
            if conn_type in connections:
                return platform

        known = ", ".join(
            f"{p} ({', '.join(sorted(c))})"
            for p, c in CONNECTION_BY_PLATFORM.items()
        )
        raise AnsibleLookupError(
            f"Connection '{conn_type}' is not recognized. "
            f"Known platforms: {known}"
        )

    def _get_connection_for_host(
        self,
        target_host: str,
        hostvars: dict[str, Any],
        variables: dict[str, Any],
    ) -> str:
        """Get connection type for a host.

        :param str target_host: Inventory hostname
        :param dict[str, Any] hostvars: Host variables mapping
        :param dict[str, Any] variables: Task variables
        :returns str: Connection plugin name
        """
        host_vars = hostvars.get(target_host, {})

        conn_type = host_vars.get("ansible_connection") or variables.get(
            "ansible_connection"
        )

        if not conn_type:
            conn_type = (
                "local" if target_host in LOCALHOST_NAMES else "ssh"
            )

        return conn_type

    def run(
        self, terms: list[Any], **kwargs: Any
    ) -> Union[list[str], str]:
        """Determine platform from ansible_connection.

        Accesses variables directly via self._templar rather than
        accepting a variables parameter.

        :param list[Any] terms: Unused lookup terms
        :param Any kwargs: host, hosts, group, groups, connection, or
            wantlist options
        :returns Union[list[str], str]: List of platforms, or single
            platform string when wantlist=False and one result
        :raises AnsibleLookupError: If connection type is not recognized
        """
        del terms  # unused

        self.set_options(direct=kwargs)
        host = self.get_option("host")
        hosts = self.get_option("hosts") or []
        group = self.get_option("group")
        groups = self.get_option("groups") or []
        connection = self.get_option("connection")
        wantlist = self.get_option("wantlist")

        # connection is mutually exclusive with host/hosts/group/groups
        host_or_group_specified = host or hosts or group or groups
        if connection and host_or_group_specified:
            raise AnsibleLookupError(
                "Option 'connection' is mutually exclusive with "
                "'host', 'hosts', 'group', and 'groups'"
            )

        # If connection specified directly, use it
        if connection:
            return [self._get_platform_for_connection(connection)]

        # Access variables directly from templar
        variables = self._templar.available_variables
        hostvars = variables.get("hostvars", {})
        inventory_groups = variables.get("groups", {})

        # Collect all target hosts from host, hosts, group, and groups
        target_hosts: set[str] = set()

        if host:
            target_hosts.add(host)

        if hosts:
            target_hosts.update(hosts)

        if group:
            hosts_in_group = inventory_groups.get(group, [])
            if not hosts_in_group:
                raise AnsibleLookupError(
                    f"Group '{group}' not found or empty"
                )
            target_hosts.update(hosts_in_group)

        if groups:
            for grp in groups:
                hosts_in_group = inventory_groups.get(grp, [])
                if not hosts_in_group:
                    raise AnsibleLookupError(
                        f"Group '{grp}' not found or empty"
                    )
                target_hosts.update(hosts_in_group)

        # If no hosts/groups specified, use current inventory_hostname
        if not target_hosts:
            target_hosts.add(
                variables.get("inventory_hostname") or "localhost"
            )

        # Get unique platforms for all target hosts
        platforms = set()
        for target_host in target_hosts:
            conn_type = self._get_connection_for_host(
                target_host, hostvars, variables
            )
            platforms.add(self._get_platform_for_connection(conn_type))

        result = sorted(platforms)

        # wantlist=False: return single value if only one platform
        if not wantlist and len(result) == 1:
            return result[0]

        return result
