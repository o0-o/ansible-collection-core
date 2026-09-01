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

"""Connection type to platform mappings, and the connection fact.

This module provides the single source of truth for mapping Ansible
connection plugins to platform types (POSIX or Windows), and composes
``o0_connection``: what the transport a task runs over resolved to,
read off the plugin the executor built rather than off the variables
that went into building it.
"""

from __future__ import annotations

from typing import Any, Optional

from ansible_collections.o0_o.core.plugins.module_utils.evidence_utils import (  # noqa: E501
    EVIDENCE,
    compose_evidence,
    name_origins,
)
from ansible_collections.o0_o.core.plugins.module_utils.localhost import (
    LOCALHOST_NAMES,
)

CONNECTION_BY_PLATFORM: dict[str, frozenset[str]] = {
    "posix": frozenset(
        {
            # Core Ansible connections
            "local",
            "ssh",
            "ansible.builtin.local",
            "ansible.builtin.ssh",
            # Container runtimes
            "docker",
            "podman",
            "buildah",
            "community.docker.docker",
            "community.docker.docker_api",
            "containers.podman.podman",
            "containers.podman.buildah",
            # Orchestration (Kubernetes/OpenShift)
            "kubectl",
            "oc",
            "kubernetes.core.kubectl",
            "community.okd.oc",
            # Jails/Zones (BSD/Solaris)
            "jail",
            "zone",
            "community.general.jail",
            "community.general.zone",
            # Other POSIX-compatible
            "lxc",
            "lxd",
            "chroot",
            "community.general.lxc",
            "community.general.lxd",
            "community.general.chroot",
        }
    ),
    "windows": frozenset(
        {
            "winrm",
            "psrp",
            "ansible.builtin.winrm",
            "ansible.builtin.psrp",
        }
    ),
}

# The one transport that runs on the controller, by both names it
# answers to
LOCAL_TRANSPORTS: frozenset[str] = frozenset(
    {"local", "ansible.builtin.local"}
)


def platform_of(connection: Optional[str]) -> Optional[str]:
    """The platform a connection plugin reaches, or None.

    The table names a plugin by its short name and by its FQCN, so a
    caller may ask by whichever it holds.  A plugin the table names
    under neither is None rather than a guess: the caller decides
    whether an unplaced transport is an error or a fact.

    :param Optional[str] connection: A connection plugin's name
    :returns Optional[str]: ``posix``, ``windows`` or None
    """
    for platform, connections in CONNECTION_BY_PLATFORM.items():
        if connection in connections:
            return platform
    return None


def option_of(plugin: Any, *names: str) -> Any:
    """The first of the named options a plugin declares, or None.

    Transports do not agree on what to call the address they are
    pointed at - ssh says ``host``, winrm and psrp say ``remote_addr``
    - so a caller names every spelling it knows and takes the first
    one the plugin has.  A plugin with none of them, which is what the
    local transport is for every connection setting there is, answers
    None: a field the transport does not have is null, not an error.

    ``get_option`` raises KeyError for an option the plugin does not
    define, by contract, and that is the one failure read as absence.
    Anything else the plugin raises is its own and propagates.

    :param Any plugin: A loaded plugin with ``get_option``
    :param str names: Option names, best first
    :returns Any: The resolved value, or None
    """
    for name in names:
        try:
            return plugin.get_option(name)
        except (KeyError, AttributeError):
            continue
    return None


def compose_connection(
    *,
    plugin: Optional[str],
    transport: Optional[str],
    addr: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    private_key_file: Optional[str] = None,
    become: Optional[dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> dict[str, Any]:
    """Compose ``o0_connection`` from what the transport resolved to.

    ``platform`` is read off the table by the plugin's resolved name
    first and its declared transport second, so a plugin the table
    names under either spelling is placed and one it names under
    neither is null rather than guessed.  ``local`` is true where the
    transport is the local one or where whatever transport was chosen
    is pointed at a loopback name, because ssh to 127.0.0.1 lands on
    the controller as surely as the local transport does.

    ``become`` is the escalation in force or None: a task that runs as
    the connecting user has no escalation to describe, and null says
    that where a mapping of nulls would say something was configured
    and not filled in.

    Nothing outside Ansible is consulted, so the evidence is an empty
    record, and origins names the producer that said so.

    :param Optional[str] plugin: The connection plugin's resolved FQCN
    :param Optional[str] transport: The transport the plugin declares
    :param Optional[str] addr: The address the transport was pointed
        at, or None where it has no such setting
    :param Optional[int] port: The port, or None where it has none
    :param Optional[str] user: The login the transport connects as,
        or None where the transport left that to its own default
    :param Optional[str] private_key_file: The key the transport
        authenticates with, or None where it names none
    :param Optional[dict[str, Any]] become: The escalation in force -
        ``plugin``, ``method`` and ``user`` - or None where there is
        none
    :param Optional[str] origin: The FQCN of the module composing
        this, or None to name nobody
    :returns dict[str, Any]: The fact
    """
    fact: dict[str, Any] = {
        "plugin": plugin,
        "transport": transport,
        "platform": platform_of(plugin) or platform_of(transport),
        "local": (
            transport in LOCAL_TRANSPORTS
            or plugin in LOCAL_TRANSPORTS
            or addr in LOCALHOST_NAMES
        ),
        "addr": addr,
        "port": port,
        "user": user,
        "private_key_file": private_key_file,
        "become": dict(become) if become else None,
        EVIDENCE: compose_evidence(),
    }

    return name_origins(fact, origin)


__all__ = [
    "CONNECTION_BY_PLATFORM",
    "LOCAL_TRANSPORTS",
    "compose_connection",
    "option_of",
    "platform_of",
]
