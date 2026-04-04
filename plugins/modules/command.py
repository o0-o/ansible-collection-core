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
module: command
short_description: Execute commands on remote hosts across platforms
version_added: "0.1.0"
description:
  - Cross-platform command execution that automatically routes to the
    appropriate platform-specific module.
  - For POSIX systems (ssh, local), delegates to C(o0_o.posix.command).
  - For Windows systems (winrm, psrp), delegates to
    C(ansible.windows.win_command).
  - Only shared parameters are accepted. For platform-specific features,
    use the underlying modules directly.
options:
  cmd:
    description:
      - The command to run on the remote node.
      - Only one of C(cmd) or C(argv) may be specified.
    required: false
    type: str
  argv:
    description:
      - A list of command arguments to run. Cannot be used with C(cmd).
    required: false
    type: list
    elements: str
  chdir:
    description:
      - Change into this directory on the remote node before running the
        command.
    type: path
  creates:
    description:
      - If the specified path exists, the command will not be run.
    type: path
  removes:
    description:
      - If the specified path does not exist, the command will not be run.
    type: path
  stdin:
    description:
      - The string to pass on stdin before running the command.
    type: str
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
    platforms: posix, windows
    description:
      - Supported on POSIX and Windows systems.
author:
  - oØ.o (@o0-o)
seealso:
  - module: o0_o.posix.command
  - module: ansible.windows.win_command
notes:
  - Only one of C(cmd) or C(argv) may be used; supplying both will cause an
    error.
  - The module automatically detects the target platform based on the
    connection plugin.
"""

EXAMPLES = r"""
- name: Run a simple command using argv
  o0_o.core.command:
    argv: ['ls', '-l', '/etc']

- name: Run a command using cmd string
  o0_o.core.command:
    cmd: echo "Hello world"

- name: Skip command if file already exists
  o0_o.core.command:
    argv: ['echo', 'Hello world']
    creates: /tmp/already_exists.txt

- name: Run command with stdin
  o0_o.core.command:
    cmd: cat
    stdin: "Input text"
"""

RETURN = r"""
msg:
  description: Human-readable message about the task result.
  type: str
  returned: always
stdout:
  description: The standard output from the command.
  type: str
  returned: always
stderr:
  description: The standard error from the command.
  type: str
  returned: always
cmd:
  description: The command that was executed.
  type: list
  elements: str
  returned: always
rc:
  description: The return code of the command.
  type: int
  returned: always
module:
  description: The platform-specific module that was used.
  type: str
  returned: always
stdout_lines:
  description: The command standard output split in lines.
  returned: always
  type: list
stderr_lines:
  description: The command standard error split in lines.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule


def main() -> None:
    """Fail if this module is run directly without the action plugin."""
    module = AnsibleModule(
        argument_spec={
            "cmd": {"type": "str"},
            "argv": {"type": "list", "elements": "str"},
            "chdir": {"type": "path"},
            "creates": {"type": "path"},
            "removes": {"type": "path"},
            "stdin": {"type": "str"},
        },
        mutually_exclusive=[["cmd", "argv"]],
        required_one_of=[["cmd", "argv"]],
        supports_check_mode=True,
    )
    module.fail_json(msg="This module must be run via its action plugin.")


if __name__ == "__main__":
    main()
