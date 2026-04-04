#!/usr/bin/env bash
# vim: ts=4:sw=4:sts=4:et:ft=sh
#
# GNU General Public License v3.0+
# SPDX-License-Identifier: GPL-3.0-or-later
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
#
# Copyright (c) 2025 oØ.o (@o0-o)
#
# This file is part of the o0_o.core Ansible Collection.
#
# Setup script to install platform-specific collections before running
# integration tests. Runs the o0_o.core.install role via ansible-playbook.
#
# This MUST run as a separate playbook invocation because Ansible's
# collection loader caches at startup - collections installed mid-play
# are not visible until the next ansible-playbook run.

set -eux

# Run the install role against localhost
ansible-playbook -i localhost, -c local "${BASH_SOURCE%/*}/install.yml"
