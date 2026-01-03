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

"""Connection type to platform mappings.

This module provides the single source of truth for mapping Ansible
connection plugins to platform types (POSIX or Windows).
"""

from __future__ import annotations

from typing import Dict, FrozenSet


CONNECTION_BY_PLATFORM: Dict[str, FrozenSet[str]] = {
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
