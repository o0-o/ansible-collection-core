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

"""Publish facts about the process running Ansible.

The controller is the one host a play never has to reach: the process
already runs there.  This plugin reads its own effective identity, the
interpreter it runs under and the configuration file Ansible loaded,
and hands what it read to the composers in module_utils.  Nothing is
executed on the target host and no connection is used.
"""

from __future__ import annotations

import configparser
import grp
import os
import platform
import pwd
import sys

from importlib import metadata
from typing import Any, Optional

from ansible import constants as C
from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

from ansible_collections.o0_o.core.plugins.module_utils import (
    CoreActionBase,
)
from ansible_collections.o0_o.core.plugins.module_utils.controller import (
    compose_config,
    compose_controller,
    compose_python,
    compose_user,
    select_subsets,
)

FQCN = "o0_o.core.controller"

ARGUMENT_SPEC = {
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


class ActionModule(CoreActionBase, ActionBase):
    """Describe the machine running Ansible."""

    TRANSFERS_FILES = False
    _requires_connection = False
    _supports_check_mode = True
    _supports_async = False

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Publish ``o0_controller`` for the host this task ran for.

        :param Optional[str] tmp: Unused temporary directory path
        :param Optional[dict[str, Any]] task_vars: Available Ansible
            variables
        :returns dict[str, Any]: Result dictionary carrying
            ``ansible_facts``
        """
        task_vars = task_vars or {}
        self._def_inventory_hostname(task_vars)
        result = super().run(tmp, task_vars=task_vars)
        del tmp  # unused

        _validation, args = self.validate_argument_spec(
            argument_spec=ARGUMENT_SPEC
        )

        try:
            subsets = select_subsets(args["gather_subset"])
        except ValueError as e:
            raise AnsibleActionFail(str(e)) from e

        readings: dict[str, Any] = {}
        if "user" in subsets:
            readings["user"] = self._read_user()
        if "python" in subsets:
            readings["python"] = self._read_python()
        if "config" in subsets:
            readings["config"] = self._read_config()

        result["changed"] = False
        result["ansible_facts"] = {
            "o0_controller": compose_controller(
                subsets, origin=FQCN, **readings
            )
        }

        return result

    def _read_user(self) -> dict[str, Any]:
        """Read who this process runs as.

        The effective ids are the process's own.  The names are what
        the controller's user database says of them, asked through the
        same interfaces the C library uses, and null where it has no
        entry - a container running as an unnamed id is a real
        controller and is described as one.

        :returns dict[str, Any]: The ``user`` subset
        """
        uid = os.geteuid()
        gid = os.getegid()

        try:
            name: Optional[str] = pwd.getpwuid(uid).pw_name
        except KeyError:
            name = None

        try:
            group: Optional[str] = grp.getgrgid(gid).gr_name
        except KeyError:
            group = None

        return compose_user(uid, gid, name, group)

    def _read_python(self) -> dict[str, Any]:
        """Read the interpreter this process runs under.

        The interpreter is the one executing this plugin, which is the
        one running the play.  pip is looked up in that interpreter's
        installed distributions rather than run, because a version is
        metadata and running pip to read it would be a command where
        none is needed.

        :returns dict[str, Any]: The ``python`` subset
        """
        try:
            pip: Optional[str] = metadata.version("pip")
        except metadata.PackageNotFoundError:
            pip = None

        return compose_python(sys.executable, platform.python_version(), pip)

    def _read_config(self) -> dict[str, Any]:
        """Read the configuration file Ansible loaded.

        The path is the one Ansible's own configuration manager
        settled on, which is the file whose settings this run obeys.
        A run with no file is described as one.  A file Ansible loaded
        and this plugin cannot read back, or cannot parse, is a failure
        of the run rather than a fact about the controller.

        :returns dict[str, Any]: The ``config`` subset
        :raises AnsibleActionFail: Where the file cannot be read or
            parsed
        """
        path = getattr(C, "CONFIG_FILE", None)
        if not path:
            return compose_config(None, None)

        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as e:
            raise AnsibleActionFail(
                f"Ansible loaded {path} but it cannot be read back: {e}"
            ) from e

        try:
            return compose_config(path, text)
        except configparser.Error as e:
            raise AnsibleActionFail(
                f"{path} does not parse as an ini file: {e}"
            ) from e
