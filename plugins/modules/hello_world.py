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
module: hello_world
short_description: Echo 'Hello, world!' and validate the output
version_added: "0.2.0"
description:
  - Executes the C(echo "Hello, world!") command on the remote host
    using the COMMAND_SPEC pattern for cross-platform command execution.
  - Validates that the output matches the expected message.
  - Serves as an example of command specification with parsing and
    validation.
extends_documentation_fragment:
  - action_common_attributes
attributes:
  check_mode:
    support: full
    description:
      - This module fully supports check mode.
  diff_mode:
    support: none
    description:
      - This module does not produce diff output.
  async:
    support: none
    description:
      - This module does not support asynchronous execution.
  platform:
    platforms: posix
    description:
      - Only supported on POSIX-compatible systems.
author:
  - oØ.o (@o0-o)
notes:
  - This module must be executed via its action plugin.
  - This module is primarily for testing and demonstration purposes.
"""

EXAMPLES = r"""
- name: Run hello world
  o0_o.core.hello_world:
  register: hello_reg

- name: Display the message
  ansible.builtin.debug:
    msg: "{{ hello_reg['message'] }}"
"""

RETURN = r"""
message:
  description: The validated output message from the command.
  type: str
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule


def main() -> None:
    """Fail if this module is run directly without the action plugin."""
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)
    module.fail_json(msg="This module must be run via its action plugin.")


if __name__ == "__main__":
    main()
