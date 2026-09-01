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

"""Unit tests for the controller fact's composers."""

from __future__ import annotations

import configparser

import pytest

from ansible_collections.o0_o.core.plugins.module_utils.controller import (
    SUBSETS,
    compose_config,
    compose_controller,
    compose_python,
    compose_user,
    parse_config,
    select_subsets,
)

ORIGIN = "o0_o.core.controller"


def test_the_fact_has_three_subsets_in_a_stated_order() -> None:
    """Test the registry names every subset and the order they are
    published in, so a consumer reading the fact top to bottom reads
    the cheap answers first."""
    assert SUBSETS == ("user", "python", "config")


def test_all_selects_every_subset_in_publishing_order() -> None:
    """Test the default gathers everything, in the fact's order."""
    assert select_subsets(["all"]) == ["user", "python", "config"]


def test_a_selection_is_published_in_the_facts_order_not_the_tasks() -> None:
    """Test naming subsets out of order does not reorder the fact."""
    assert select_subsets(["config", "user"]) == ["user", "config"]


def test_a_negation_removes_what_all_selected() -> None:
    """Test all followed by a negation is everything but that one."""
    assert select_subsets(["all", "!config"]) == ["user", "python"]


def test_negating_all_then_naming_one_is_that_one() -> None:
    """Test the selection is applied in the order given, so a name
    after !all survives it."""
    assert select_subsets(["!all", "user"]) == ["user"]


def test_negating_all_alone_selects_nothing() -> None:
    """Test a gather of nothing is an empty selection, not an error;
    the fact still says who described it."""
    assert select_subsets(["!all"]) == []


@pytest.mark.parametrize("name", ["bogus", "!bogus", ""])
def test_a_name_that_is_no_subset_is_refused_by_name(name: str) -> None:
    """Test an unknown subset is refused rather than ignored, and the
    refusal names it."""
    with pytest.raises(ValueError, match=f"Invalid gather_subset: {name}"):
        select_subsets(["all", name])


def test_the_user_subset_is_ids_and_the_names_the_database_gave() -> None:
    """Test the ids are integers beside the names, flat."""
    assert compose_user(1000, 20, "o0-o", "staff") == {
        "uid": 1000,
        "gid": 20,
        "name": "o0-o",
        "group": "staff",
    }


def test_an_unnamed_id_is_described_with_null_names() -> None:
    """Test a process running as an id no database entry names is a
    controller and is described as one."""
    user = compose_user(65534, 65534, None, None)

    assert user["uid"] == 65534
    assert user["name"] is None
    assert user["group"] is None


def test_the_python_subset_names_the_interpreter_and_its_pip() -> None:
    """Test the interpreter and pip are each a path or a version."""
    assert compose_python("/venv/bin/python3", "3.12.9", "25.2") == {
        "interpreter": {
            "path": "/venv/bin/python3",
            "version": {"id": "3.12.9"},
        },
        "pip": {"version": {"id": "25.2"}},
    }


def test_an_interpreter_without_pip_says_so_with_null() -> None:
    """Test no pip is a fact and not a missing field."""
    assert compose_python("/venv/bin/python3", "3.12.9", None)["pip"] is None


def test_config_parses_into_sections_of_settings_as_written() -> None:
    """Test values are the text the file holds, uninterpolated, with
    inline comments stripped the way Ansible strips them."""
    text = (
        "[defaults]\n"
        "forks = 20 ; a comment\n"
        "callback_result_format = %(fmt)s\n"
        "\n"
        "[ssh_connection]\n"
        "pipelining = True\n"
    )

    assert parse_config(text) == {
        "defaults": {
            "forks": "20",
            "callback_result_format": "%(fmt)s",
        },
        "ssh_connection": {"pipelining": "True"},
    }


def test_an_empty_file_has_no_sections() -> None:
    """Test a configuration file with nothing in it parses to
    nothing."""
    assert parse_config("") == {}


def test_text_that_is_not_an_ini_file_is_refused() -> None:
    """Test a setting before any section is the parser's error, which
    the action turns into the run's failure."""
    with pytest.raises(configparser.Error):
        parse_config("forks = 20\n")


def test_a_controller_without_a_configuration_file_is_described() -> None:
    """Test no file is a null path and no settings, not a failure."""
    assert compose_config(None, None) == {"path": None, "settings": {}}


def test_a_configuration_file_is_its_path_and_what_it_says() -> None:
    """Test the subset joins the path to the settings read from it."""
    config = compose_config(
        "/etc/ansible/ansible.cfg", "[defaults]\nforks=5\n"
    )

    assert config == {
        "path": "/etc/ansible/ansible.cfg",
        "settings": {"defaults": {"forks": "5"}},
    }


def test_only_the_subsets_selected_appear() -> None:
    """Test a subset not gathered is absent, so it can be told from one
    that answered nothing."""
    fact = compose_controller(
        ["user"], user={"uid": 0, "gid": 0, "name": "root", "group": "root"}
    )

    assert list(fact) == ["user", "evidence"]


def test_the_evidence_names_the_file_the_config_subset_read() -> None:
    """Test one record for the section, naming the one file that was
    consulted for it, and the producer that read it."""
    fact = compose_controller(
        ["user", "python", "config"],
        user={"uid": 1000, "gid": 20, "name": "o0-o", "group": "staff"},
        python={"interpreter": {}, "pip": None},
        config={"path": "/Users/o0-o/.ansible.cfg", "settings": {}},
        origin=ORIGIN,
    )

    assert list(fact) == ["user", "python", "config", "evidence", "origins"]
    assert fact["evidence"] == {"files": ["/Users/o0-o/.ansible.cfg"]}
    assert fact["origins"] == [ORIGIN]


def test_a_config_subset_that_found_no_file_attempted_the_kind() -> None:
    """Test files is present and empty: the kind was attempted and
    answered for nothing, which is not the same as not attempted."""
    fact = compose_controller(
        ["config"], config={"path": None, "settings": {}}, origin=ORIGIN
    )

    assert fact["evidence"] == {"files": []}


def test_a_gather_without_config_consulted_nothing_and_says_so() -> None:
    """Test the subsets that read the process carry no kind at all, so
    the record is empty and still names its producer."""
    fact = compose_controller(
        ["user", "python"],
        user={"uid": 1000, "gid": 20, "name": "o0-o", "group": "staff"},
        python={"interpreter": {}, "pip": None},
        origin=ORIGIN,
    )

    assert fact["evidence"] == {}
    assert fact["origins"] == [ORIGIN]
    assert "config" not in fact


def test_a_gather_of_nothing_is_described_not_skipped() -> None:
    """Test an empty selection is a fact with provenance and no
    subsets, so the run that produced it is still on record."""
    fact = compose_controller([], origin=ORIGIN)

    assert fact == {"evidence": {}, "origins": [ORIGIN]}


def test_naming_nobody_leaves_the_record_unclaimed() -> None:
    """Test a composer with no origin to name names none."""
    fact = compose_controller(["user"], user={"uid": 0})

    assert "origins" not in fact
