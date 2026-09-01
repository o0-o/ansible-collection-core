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

"""Unit tests for the connection fact and the platform table."""

from __future__ import annotations

from typing import Any

import pytest

from ansible_collections.o0_o.core.plugins.module_utils.connection import (
    CONNECTION_BY_PLATFORM,
    LOCAL_TRANSPORTS,
    compose_connection,
    option_of,
    platform_of,
)


class FakePlugin:
    """A plugin that declares exactly the options it was handed."""

    def __init__(self, **options: Any) -> None:
        self._options = options

    def get_option(self, name: str) -> Any:
        if name not in self._options:
            # What AnsiblePlugin raises for an undefined option
            raise KeyError(name)
        return self._options[name]


@pytest.mark.parametrize(
    ("name", "platform"),
    [
        ("ssh", "posix"),
        ("ansible.builtin.ssh", "posix"),
        ("local", "posix"),
        ("community.docker.docker", "posix"),
        ("winrm", "windows"),
        ("ansible.builtin.psrp", "windows"),
    ],
)
def test_a_plugin_is_placed_by_either_of_its_names(
    name: str, platform: str
) -> None:
    """Test the table answers by short name and by FQCN alike."""
    assert platform_of(name) == platform


def test_a_plugin_the_table_does_not_name_is_not_guessed() -> None:
    """Test an unplaced transport is None, and None itself is too."""
    assert platform_of("ansible.netcommon.network_cli") is None
    assert platform_of(None) is None


def test_the_table_names_every_local_spelling() -> None:
    """Test the local transports are in the table under posix, so the
    two constants cannot disagree about what local is."""
    assert LOCAL_TRANSPORTS <= CONNECTION_BY_PLATFORM["posix"]


def test_an_option_is_read_by_the_first_name_the_plugin_has() -> None:
    """Test transports that spell the address differently are read
    by whichever spelling they declare."""
    ssh = FakePlugin(host="192.0.2.10", port=22)
    winrm = FakePlugin(remote_addr="192.0.2.20", port=5986)

    assert option_of(ssh, "host", "remote_addr") == "192.0.2.10"
    assert option_of(winrm, "host", "remote_addr") == "192.0.2.20"


def test_an_option_the_plugin_lacks_is_null() -> None:
    """Test a setting the transport does not declare is None rather
    than an error, and so is one on a thing that is no plugin."""
    assert option_of(FakePlugin(), "host", "remote_addr") is None
    assert option_of(object(), "port") is None


def test_an_option_set_to_null_is_null_and_stops_the_search() -> None:
    """Test a declared option resolved to None is the answer, not a
    reason to try the next spelling."""
    plugin = FakePlugin(host=None, remote_addr="192.0.2.30")

    assert option_of(plugin, "host", "remote_addr") is None


def test_an_ssh_transport_is_described_as_it_resolved() -> None:
    """Test every field is what the plugin resolved to, the platform
    is read off the table, and a remote address is not local."""
    fact = compose_connection(
        plugin="ansible.builtin.ssh",
        transport="ssh",
        addr="192.0.2.10",
        port=2222,
        user="deploy",
        private_key_file="/home/me/.ssh/id_ed25519",
        become={
            "plugin": "ansible.builtin.sudo",
            "method": "sudo",
            "user": "root",
        },
        origin="o0_o.core.connection",
    )

    assert fact == {
        "plugin": "ansible.builtin.ssh",
        "transport": "ssh",
        "platform": "posix",
        "local": False,
        "addr": "192.0.2.10",
        "port": 2222,
        "user": "deploy",
        "private_key_file": "/home/me/.ssh/id_ed25519",
        "become": {
            "plugin": "ansible.builtin.sudo",
            "method": "sudo",
            "user": "root",
        },
        "evidence": {},
        "origins": ["o0_o.core.connection"],
    }


def test_the_local_transport_has_no_address_and_is_local() -> None:
    """Test the transport that runs on the controller says so, and the
    settings it does not declare are null rather than invented."""
    fact = compose_connection(
        plugin="ansible.builtin.local",
        transport="local",
        user="o0-o",
        origin="o0_o.core.connection",
    )

    assert fact["local"] is True
    assert fact["platform"] == "posix"
    assert fact["addr"] is None
    assert fact["port"] is None
    assert fact["private_key_file"] is None
    assert fact["user"] == "o0-o"


@pytest.mark.parametrize("addr", ["localhost", "127.0.0.1", "::1"])
def test_a_transport_pointed_at_the_loopback_is_local(addr: str) -> None:
    """Test ssh to the loopback lands on the controller as surely as
    the local transport does, and the fact says so."""
    fact = compose_connection(
        plugin="ansible.builtin.ssh", transport="ssh", addr=addr
    )

    assert fact["local"] is True


def test_a_transport_is_local_by_either_of_its_names() -> None:
    """Test a plugin whose resolved name is the local one is local
    even where the transport string is missing."""
    fact = compose_connection(plugin="ansible.builtin.local", transport=None)

    assert fact["local"] is True


def test_no_escalation_is_null_not_a_mapping_of_nulls() -> None:
    """Test a task running as the connecting user has no escalation to
    describe, and an empty mapping handed in is the same absence."""
    assert (
        compose_connection(plugin="ansible.builtin.ssh", transport="ssh")[
            "become"
        ]
        is None
    )
    assert (
        compose_connection(
            plugin="ansible.builtin.ssh", transport="ssh", become={}
        )["become"]
        is None
    )


def test_a_windows_transport_is_placed_and_not_local() -> None:
    """Test the table's other platform is reached the same way."""
    fact = compose_connection(
        plugin="ansible.builtin.winrm",
        transport="winrm",
        addr="192.0.2.20",
        port=5986,
        user="Administrator",
    )

    assert fact["platform"] == "windows"
    assert fact["local"] is False


def test_an_unplaced_transport_has_a_null_platform() -> None:
    """Test a plugin the table does not name is a fact with a null
    platform rather than a guess or an error."""
    fact = compose_connection(
        plugin="ansible.netcommon.network_cli", transport="network_cli"
    )

    assert fact["platform"] is None
    assert fact["local"] is False


def test_the_evidence_is_empty_and_still_names_its_producer() -> None:
    """Test nothing outside Ansible was consulted, the record says so,
    and origins attaches because the statement is one."""
    fact = compose_connection(
        plugin="ansible.builtin.ssh",
        transport="ssh",
        origin="o0_o.core.connection",
    )

    assert fact["evidence"] == {}
    assert fact["origins"] == ["o0_o.core.connection"]


def test_naming_nobody_leaves_the_record_unclaimed() -> None:
    """Test a composer with no origin to name names none."""
    fact = compose_connection(plugin="ansible.builtin.ssh", transport="ssh")

    assert fact["evidence"] == {}
    assert "origins" not in fact
