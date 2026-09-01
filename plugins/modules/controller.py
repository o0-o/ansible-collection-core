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
module: controller
short_description: Publish facts about the machine running Ansible
version_added: "1.2.0"
description:
  - Publishes C(o0_controller), a description of the process executing
    the play - who it runs as, the Python interpreter it runs under and
    the pip beside it, and the configuration file Ansible loaded with
    what that file says. These are facts about the controller, not
    about the host a task addresses.
  - Reads the process's own effective identity, its interpreter and the
    configuration Ansible's own manager settled on. Nothing is executed
    on the target host and no connection is used, so the module answers
    for a host that is unreachable.
  - Every host in a play gets the same answer, since one controller
    runs it. C(run_once) sets the fact on every host at the price of one
    gather and suits the module; it is not required, and a single-host
    play loses nothing by omitting it.
options:
  gather_subset:
    description:
      - The subsets to gather, applied in the order given.
      - C(all) selects every subset and C(!all) clears the selection; a
        name adds its subset and the same name behind C(!) removes it,
        so C([all, '!config']) is the two subsets that read nothing.
      - Only the subsets selected appear in the fact, so a subset not
        gathered can be told from one that answered nothing.
    type: list
    elements: str
    default: [all]
    choices: [all, user, config, python, '!all', '!user', '!config', '!python']
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
      - Runs on the controller whatever the target is. The controller
        itself is POSIX-like, which is ansible-core's own requirement,
        and the identity is resolved through its user database.
author:
  - oØ.o (@o0-o)
seealso:
  - module: o0_o.core.connection
    description: Facts about the connection a task runs over.
  - module: ansible.builtin.setup
    description: Facts about the host a task addresses.
notes:
  - This module must be executed via its action plugin.
  - Retires M(o0_o.controller.facts), which ran C(id) for the identity,
    C(pip) for its version, and failed on a controller with no
    configuration file. This module asks the process, reads the version
    as metadata, and describes a missing file as missing.
"""

EXAMPLES = r"""
- name: Describe the controller once for the whole play
  o0_o.core.controller:
  run_once: true

- name: Describe only the identity the play runs as
  o0_o.core.controller:
    gather_subset:
      - user

- name: Describe everything but the configuration file
  o0_o.core.controller:
    gather_subset:
      - all
      - '!config'

- name: Refuse to run a play as root on the controller
  ansible.builtin.assert:
    that:
      - o0_controller['user']['uid'] != 0
    fail_msg: this play is not meant to be run as root
"""

RETURN = r"""
ansible_facts:
  description: Facts set on the host this task ran for.
  returned: always
  type: dict
  contains:
    o0_controller:
      description: >-
        What the process running Ansible is. One record of evidence for
        the whole fact, because one process was read for all of it, and
        only the subsets selected appear.
      returned: always
      type: dict
      contains:
        user:
          description: Who the controller process runs as.
          returned: when the user subset is selected
          type: dict
          contains:
            uid:
              description: The process's effective user id.
              type: int
              sample: 1000
            gid:
              description: The process's effective group id.
              type: int
              sample: 1000
            name:
              description: >-
                The name the controller's user database gives the id,
                or null where it has no entry for it - a container
                running as an unnamed id is described as one.
              type: str
              sample: deploy
            group:
              description: >-
                The name the controller's group database gives the
                group id, or null likewise.
              type: str
              sample: deploy
        python:
          description: The interpreter the controller process runs under.
          returned: when the python subset is selected
          type: dict
          contains:
            interpreter:
              description: The interpreter executing the play.
              type: dict
              contains:
                path:
                  description: >-
                    The interpreter's path, which is what
                    C(ansible_playbook_python) also names.
                  type: str
                  sample: /opt/ansible/.venv/bin/python3
                version:
                  description: The interpreter's version.
                  type: dict
                  contains:
                    id:
                      description: The version string.
                      type: str
                      sample: "3.12.9"
            pip:
              description: >-
                The pip installed in that interpreter, read as
                distribution metadata rather than run, or null where the
                interpreter has none - an environment built without pip
                is a fact, not a missing field.
              type: dict
              sample:
                version:
                  id: "25.2"
              contains:
                version:
                  description: pip's version.
                  type: dict
                  contains:
                    id:
                      description: The version string.
                      type: str
                      sample: "25.2"
        config:
          description: The configuration file Ansible loaded.
          returned: when the config subset is selected
          type: dict
          contains:
            path:
              description: >-
                The file Ansible's configuration manager settled on,
                which is what C(ansible_config_file) also names, or null
                where the run has no configuration file.
              type: str
              sample: /home/deploy/.ansible.cfg
            settings:
              description: >-
                What the file says, by section, values as written and
                uninterpolated. Empty where there is no file.
              type: dict
              sample:
                defaults:
                  forks: "20"
                  interpreter_python: auto_silent
        evidence:
          description: >-
            What was consulted, in the one vocabulary the namespace
            speaks - see the C(evidence) notes on this module. C(files)
            names the configuration file where the config subset read
            one, is empty where that subset ran and found no file, and
            is absent where the subset was not selected. The other two
            subsets consult nothing outside the process, so a gather
            without config is an empty record that still names its
            producer.
          type: dict
          sample:
            files:
              - /home/deploy/.ansible.cfg
        origins:
          description: >-
            The modules that composed the fact, sorted. Travels with
            C(evidence).
          type: list
          elements: str
          sample:
            - o0_o.core.controller
"""

from ansible.module_utils.basic import AnsibleModule


def main() -> None:
    """Fail if this module is run directly without the action plugin."""
    argument_spec = {
        "gather_subset": {
            "type": "list",
            "elements": "str",
            "default": ["all"],
            "choices": [
                "all",
                "user",
                "config",
                "python",
                "!all",
                "!user",
                "!config",
                "!python",
            ],
        }
    }

    module = AnsibleModule(
        argument_spec=argument_spec, supports_check_mode=True
    )
    module.fail_json(msg="This module must be run via its action plugin.")


if __name__ == "__main__":
    main()
