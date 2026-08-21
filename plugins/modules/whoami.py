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
module: whoami
short_description: Get the current user via the whoami command
version_added: "0.2.0"
description:
  - Executes the C(whoami) command on the remote host using the
    COMMAND_SPEC pattern for cross-platform command execution.
  - Returns the username of the current user running the command.
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
"""

EXAMPLES = r"""
- name: Get current user
  o0_o.core.whoami:
  register: whoami_reg

- name: Display the current user
  ansible.builtin.debug:
    msg: "Running as {{ whoami_reg['user'] }}"
"""

RETURN = r"""
user:
  description: The username returned by the whoami command.
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
