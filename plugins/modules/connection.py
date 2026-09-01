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

__metaclass__ = type

DOCUMENTATION = r"""
---
module: connection
short_description: Publish what the connection a task runs over resolved to
version_added: "1.2.0"
description:
  - Publishes C(o0_connection), a description of the transport Ansible
    chose for this host - the plugin by its full name and the transport
    it declares, the platform that transport reaches, whether it lands on
    the controller, the address, port, login and key it was pointed at,
    and the escalation in force.
  - Reads the connection plugin the executor built for this task, and
    the become plugin beside it where the task escalates, after every
    source of a setting has applied - inventory, play keywords, the
    command line, configuration, and the plugin's own defaults. So the
    fact says what will be used, not what any one variable says, and it
    says so before anything is used.
  - Runs entirely on the controller. Nothing is executed on the target
    host and no connection is opened to it, so the module answers for
    a host that is unreachable, and escalation is described without
    ever being invoked.
extends_documentation_fragment:
  - action_common_attributes
  - o0_o.core.evidence
attributes:
  check_mode:
    support: full
    description:
      - The module reads and never writes, so check mode publishes the
        same fact a run does.
  diff_mode:
    support: none
    description:
      - This module does not produce diff output.
  async:
    support: none
    description:
      - This module does not support asynchronous execution.
  platform:
    platforms: all
    description:
      - Runs on the controller against whatever transport the host has,
        Windows transports included, since it describes the transport
        rather than driving it.
author:
  - oØ.o (@o0-o)
seealso:
  - module: o0_o.core.controller
    description: Facts about the machine running Ansible.
notes:
  - This module must be executed via its action plugin.
  - A setting the transport does not declare is null. The local
    transport declares no address, port, login or key, so all four are
    null for it and C(local) is true; it runs as the user the CLI runs
    as, which C(user) records.
  - Retires M(o0_o.connection.facts), which read four inventory
    variables back and renamed them. This module reads the plugin those
    variables configured, so it also answers where none of them was
    set.
"""

EXAMPLES = r"""
- name: Describe the connection to every host
  o0_o.core.connection:

- name: Skip a step where the play is running against the controller
  ansible.builtin.debug:
    msg: This host is the controller
  when: o0_connection['local']

- name: Route on the platform the transport reaches
  ansible.builtin.include_tasks: "{{ o0_connection['platform'] }}.yml"

- name: Describe an ssh transport without opening it
  o0_o.core.connection:
  vars:
    ansible_connection: ssh
    ansible_host: 192.0.2.10
    ansible_user: deploy
  register: connection_reg
"""

RETURN = r"""
ansible_facts:
  description: Facts set on the host this task ran for.
  returned: always
  type: dict
  contains:
    o0_connection:
      description: >-
        What the transport resolved to for this host. One record for the
        whole fact, because one plugin was read for all of it.
      returned: always
      type: dict
      contains:
        plugin:
          description: >-
            The connection plugin, by the fully qualified name it
            resolved to. A short name in inventory resolves to the
            builtin collection's plugin and is named as such here.
          type: str
          sample: ansible.builtin.ssh
        transport:
          description: >-
            The transport the plugin declares of itself. Usually the
            plugin's short name, and the name the platform table and
            the executor's own diagnostics refer to it by.
          type: str
          sample: ssh
        platform:
          description: >-
            The platform the transport reaches - C(posix) or
            C(windows) - as this collection's platform table places it,
            and null where the table does not name the plugin. This is
            the same table M(o0_o.core.command) routes on.
          type: str
          sample: posix
        local:
          description: >-
            Whether the transport lands on the controller. True for the
            local transport, and true for any transport pointed at a
            loopback name - C(localhost), C(127.0.0.1) or C(::1) -
            because ssh to the loopback reaches the controller as surely
            as the local transport does.
          type: bool
          sample: false
        addr:
          description: >-
            The address the transport was pointed at, as the plugin
            resolved it - C(host) where the plugin calls it that,
            C(remote_addr) where it calls it that. Null for a transport
            with no address to point at, which the local transport is.
          type: str
          sample: 192.0.2.10
        port:
          description: >-
            The port, as the plugin resolved it, or null where the
            plugin declares none or left it to the transport's own
            default - an ssh plugin with no port set lets ssh choose,
            and says so with null rather than by asserting 22.
          type: int
          sample: 22
        user:
          description: >-
            The login the transport connects as, as the plugin resolved
            it - from inventory, the command line or configuration,
            whichever applied. Null where nothing named one and the
            transport falls back to its own default, which for ssh is
            whatever ssh decides. The local transport ignores every
            source and runs as the user the CLI runs as, which it
            records here.
          type: str
          sample: deploy
        private_key_file:
          description: >-
            The private key the transport authenticates with, as the
            plugin resolved it - a path, never the key. Null where the
            plugin declares no such setting or none was set.
          type: str
          sample: /home/deploy/.ssh/id_ed25519
        become:
          description: >-
            The escalation in force for this task, or null where the
            task runs as the connecting user. Described, never invoked;
            no password is asked for and none is recorded.
          type: dict
          sample:
            plugin: ansible.builtin.sudo
            method: sudo
            user: root
          contains:
            plugin:
              description: The become plugin, by its resolved FQCN.
              type: str
              sample: ansible.builtin.sudo
            method:
              description: >-
                The plugin's short name, which is what the
                C(become_method) keyword takes.
              type: str
              sample: sudo
            user:
              description: >-
                The user the escalation runs as, as the plugin resolved
                it. C(root) where nothing named one, which is the
                default every become plugin ships with.
              type: str
              sample: root
        evidence:
          description: >-
            What was consulted, in the one vocabulary the namespace
            speaks - see the C(evidence) notes on this module. Always
            empty here, and present because that is a statement: the
            plugin the executor built is the source, and it is not a
            file, a command or a configuration variable. Nothing outside
            Ansible was consulted.
          type: dict
          sample: {}
        origins:
          description: >-
            The modules that composed the fact, sorted. Travels with
            C(evidence) and names this module, because the record is a
            statement even when it is empty.
          type: list
          elements: str
          sample:
            - o0_o.core.connection
"""

from ansible.module_utils.basic import AnsibleModule


def main() -> None:
    """Fail if this module is run directly without the action plugin."""
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)
    module.fail_json(msg="This module must be run via its action plugin.")


if __name__ == "__main__":
    main()
