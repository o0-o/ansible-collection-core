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

"""Publish what the transport a task runs over resolved to.

The executor builds a connection plugin for every task and, where the
task escalates, a become plugin beside it, with every source of a
setting already applied: inventory, play keywords, the command line,
configuration, and the plugin's own defaults.  Those two objects are
the fact.  This plugin reads them and runs nothing on the host.
"""

from __future__ import annotations

from typing import Any, Optional

from ansible.plugins.action import ActionBase

from ansible_collections.o0_o.core.plugins.module_utils import (
    CoreActionBase,
)
from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    compose_connection,
    option_of,
)

FQCN = "o0_o.core.connection"


class ActionModule(CoreActionBase, ActionBase):
    """Describe the connection this task runs over."""

    TRANSFERS_FILES = False
    # The fact is the connection the executor built, so this plugin
    # wants the real one. The flag only matters to persistent
    # transports, which swap in a local connection for a plugin that
    # says it needs none - and that would describe the wrong thing.
    _requires_connection = True
    _supports_check_mode = True
    _supports_async = False

    def run(
        self,
        tmp: Optional[str] = None,
        task_vars: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Publish ``o0_connection`` for the host this task ran for.

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

        self.validate_argument_spec(argument_spec={})

        result["changed"] = False
        result["ansible_facts"] = {"o0_connection": self._compose()}

        return result

    def _compose(self) -> dict[str, Any]:
        """Read the connection and become plugins into the fact.

        Every setting is read off the plugin that will use it, by the
        option the plugin declares, so the fact says what the transport
        resolved to and not what any one variable said.  A setting the
        transport does not declare is null; the local transport
        declares none of them and runs as the user the CLI runs as,
        which it records for itself.

        :returns dict[str, Any]: The composed ``o0_connection``
        """
        connection = self._connection

        user = option_of(connection, "remote_user")
        if user is None:
            user = getattr(connection, "default_user", None) or None

        become = getattr(connection, "become", None)
        escalation: Optional[dict[str, Any]] = None
        if become is not None:
            escalation = {
                "plugin": getattr(become, "ansible_name", None),
                "method": getattr(become, "name", None),
                "user": self._become_user(become),
            }

        return compose_connection(
            plugin=(
                getattr(connection, "ansible_name", None)
                or self._get_connection_type()
            ),
            transport=getattr(connection, "transport", None),
            addr=option_of(connection, "host", "remote_addr"),
            port=option_of(connection, "port"),
            user=user,
            private_key_file=option_of(connection, "private_key_file"),
            become=escalation,
            origin=FQCN,
        )

    def _become_user(self, become: Any) -> Optional[str]:
        """The user the become plugin escalates to, as it resolved it.

        Become plugins fall back to the play context for the four
        options every one of them shares, so the plugin is asked with
        the context in hand and answers ``root`` where nothing named a
        user, which is the default every become plugin ships with.

        :param Any become: The become plugin in force
        :returns Optional[str]: The user, or None where the plugin
            could not say
        """
        try:
            return become.get_option(
                "become_user", playcontext=self._play_context
            )
        except (KeyError, AttributeError, TypeError):
            return getattr(self._play_context, "become_user", None)
