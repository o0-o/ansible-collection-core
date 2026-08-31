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

from __future__ import annotations

DOCUMENTATION = r"""
---
name: var
short_description: Look up variable with optional default and host parameters
version_added: "1.1.0"
description:
  - Look up a variable from the current host or another host's hostvars.
  - Supports optional default value if variable is not found.
  - Extends the built-in vars lookup with convenient default and host
    parameters.
options:
  _terms:
    description:
      - Variable name to look up.
    required: true
    type: list
    elements: str
  host:
    description:
      - Hostname to look up variables for.
      - If not specified, uses current host's variables.
      - If specified, looks up variables from hostvars[host].
    type: str
    required: false
  default:
    description:
      - Default value to return if variable is not found.
      - If not specified, raises an error when variable is not found.
      - Can be any value including None, dict, list, etc.
    type: raw
    required: false
notes:
  - When C(host) is specified, the variable is looked up from that host's
    hostvars.
  - When C(default) is specified, no error is raised if the variable is
    not found.
  - Can be used as a more flexible alternative to the built-in vars lookup.
seealso:
  - plugin: ansible.builtin.vars
    plugin_type: lookup
    description: Built-in vars lookup plugin
  - plugin: o0_o.posix.user
    plugin_type: lookup
    description: Look up user information by UID or username
  - plugin: o0_o.posix.group
    plugin_type: lookup
    description: Look up group information by GID or name
"""

EXAMPLES = r"""
- name: Look up current host's variable
  ansible.builtin.debug:
    msg: >-
      {{ lookup('o0_o.core.var', 'ansible_distribution') }}

- name: Look up variable with default if not found
  ansible.builtin.set_fact:
    app_version: >-
      {{ lookup('o0_o.core.var',
                'custom_app_version',
                default='1.0.0') }}

- name: Look up variable from another host
  ansible.builtin.debug:
    msg: >-
      {{ lookup('o0_o.core.var',
                'ansible_hostname',
                host='webserver1') }}

- name: Look up from another host with default
  ansible.builtin.set_fact:
    remote_value: >-
      {{ lookup('o0_o.core.var',
                'custom_var',
                host='appserver1',
                default='N/A') }}

- name: Check if variable exists on multiple hosts
  ansible.builtin.debug:
    msg: >-
      {{ item }}:
      {{ lookup('o0_o.core.var',
                'docker_installed',
                host=item,
                default=False) }}
  loop: "{{ groups['all'] }}"

- name: Use None as default
  ansible.builtin.set_fact:
    maybe_value: >-
      {{ lookup('o0_o.core.var',
                'optional_setting',
                default=None) }}

- name: Look up nested variable with default
  ansible.builtin.set_fact:
    db_host: >-
      {{ lookup('o0_o.core.var',
                'database',
                default={})['host']
         | default('localhost') }}

- name: Get variable from each host in a group
  ansible.builtin.debug:
    msg: >-
      {{ lookup('o0_o.core.var', 'service_port', host=item) }}
  loop: "{{ groups['webservers'] }}"
  when: >-
    lookup('o0_o.core.var',
           'service_port',
           host=item,
           default=None) is not none
"""

RETURN = r"""
_raw:
  description:
    - The variable value from the current host or specified host.
    - If variable is not found and default is provided, returns the
      default value.
    - If multiple variable names are provided, returns a list.
  type: raw
"""

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase

from ansible_collections.o0_o.core.plugins.module_utils import (
    VarsLookupBase,
)


class LookupModule(VarsLookupBase, LookupBase):
    """Look up variable with optional default and host parameters."""

    def run(self, terms, variables=None, **kwargs):
        """Perform the lookup.

        :param list terms: List of variable names to look up
        :param dict variables: Available Ansible variables
        :returns list: List of variable values or defaults
        """
        # Extract host and default parameters if provided
        host = kwargs.pop("host", None)
        has_default = "default" in kwargs
        default = kwargs.pop("default", None)

        ret = []
        for term in terms:
            # Template the term to resolve any Jinja2 expressions
            term = self._templar.template(term)

            # Look up the variable
            try:
                if has_default:
                    value = self.lookup_var(
                        term, host=host, default=default, **kwargs
                    )
                else:
                    value = self.lookup_var(term, host=host, **kwargs)
                ret.append(value)
            except (ValueError, KeyError, AttributeError, RuntimeError) as e:
                # Convert generic exceptions to AnsibleLookupError
                if has_default:
                    ret.append(default)
                else:
                    raise AnsibleLookupError(str(e)) from e

        return ret
