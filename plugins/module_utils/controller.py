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

"""The controller fact: what the process running Ansible is.

``o0_controller`` describes the machine executing the play rather than
the host a task addresses - who the process runs as, the interpreter
it runs under, and the configuration file it loaded.  The action
plugin reads those off the process; this module selects the subsets
and composes what was read into the fact, so the shaping can be held
to its promises without a process to read.
"""

from __future__ import annotations

import configparser

from typing import Any, Iterable, Optional

from ansible_collections.o0_o.core.plugins.module_utils.evidence_utils import (  # noqa: E501
    EVIDENCE,
    compose_evidence,
    name_origins,
)

# Every subset the fact has, in the order the fact publishes them
SUBSETS = ("user", "python", "config")


def select_subsets(gather_subset: Iterable[str]) -> list[str]:
    """The subsets a ``gather_subset`` selects, in publishing order.

    ``all`` selects every subset and ``!all`` clears the selection; a
    name adds its subset and the same name behind ``!`` removes it,
    each applied in the order given, so ``[all, '!config']`` is the
    two cheap subsets and ``['!all', user]`` is one.  A name that is
    no subset of this fact is refused rather than ignored.

    :param Iterable[str] gather_subset: The names as the task gave
        them
    :returns list[str]: The subsets selected, in publishing order
    :raises ValueError: On a name that is no subset
    """
    chosen: set[str] = set()

    for item in gather_subset:
        if item == "all":
            chosen = set(SUBSETS)
        elif item == "!all":
            chosen = set()
        elif item.startswith("!") and item[1:] in SUBSETS:
            chosen.discard(item[1:])
        elif item in SUBSETS:
            chosen.add(item)
        else:
            raise ValueError(f"Invalid gather_subset: {item}")

    return [subset for subset in SUBSETS if subset in chosen]


def compose_user(
    uid: int, gid: int, name: Optional[str], group: Optional[str]
) -> dict[str, Any]:
    """Compose who the controller process runs as.

    The ids are the process's effective ids and are always known; the
    names are what the controller's user database says of them, and
    null where it says nothing, which a container that runs as an id
    no passwd entry names will do.

    :param int uid: The effective user id
    :param int gid: The effective group id
    :param Optional[str] name: The user's name, or None where the
        database has no entry for the id
    :param Optional[str] group: The group's name, or None likewise
    :returns dict[str, Any]: The ``user`` subset
    """
    return {"uid": uid, "gid": gid, "name": name, "group": group}


def compose_python(
    path: str, version: str, pip: Optional[str]
) -> dict[str, Any]:
    """Compose the interpreter the controller runs under.

    pip is described where the interpreter has it and null where it
    does not - a uv-built environment ships without it - because an
    interpreter with no pip is a fact and not a missing field.

    :param str path: The interpreter's path
    :param str version: The interpreter's version
    :param Optional[str] pip: pip's version, or None where the
        interpreter has no pip
    :returns dict[str, Any]: The ``python`` subset
    """
    return {
        "interpreter": {"path": path, "version": {"id": version}},
        "pip": {"version": {"id": pip}} if pip else None,
    }


def parse_config(text: str) -> dict[str, dict[str, str]]:
    """Parse an ini configuration into sections of settings.

    Values are the text the file holds, uninterpolated, so what the
    fact says the file says is what the file says.  Inline comments
    are stripped the way Ansible's own reader strips them.

    :param str text: The file's content
    :returns dict[str, dict[str, str]]: Settings by section
    :raises configparser.Error: Where the text is not an ini file
    """
    parser = configparser.ConfigParser(
        interpolation=None, inline_comment_prefixes=(";",)
    )
    parser.read_string(text)

    return {
        section: dict(parser.items(section)) for section in parser.sections()
    }


def compose_config(path: Optional[str], text: Optional[str]) -> dict[str, Any]:
    """Compose the configuration file Ansible loaded.

    A controller running with no configuration file is described as
    one - a null path and no settings - rather than failed, because
    that is a state a controller can be in and a consumer may want to
    know it is.

    :param Optional[str] path: The file Ansible loaded, or None
    :param Optional[str] text: Its content, or None where there is no
        file
    :returns dict[str, Any]: The ``config`` subset
    :raises configparser.Error: Where the content is not an ini file
    """
    settings: dict[str, dict[str, str]] = {}
    if path is not None and text is not None:
        settings = parse_config(text)

    return {"path": path, "settings": settings}


def compose_controller(
    subsets: Iterable[str],
    *,
    user: Optional[dict[str, Any]] = None,
    python: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
    origin: Optional[str] = None,
) -> dict[str, Any]:
    """Compose ``o0_controller`` from the subsets that were read.

    Only the subsets selected appear, so a consumer can tell a subset
    not gathered from one that answered nothing.  The evidence is one
    record for the section, because one process was read for all of
    it: ``files`` names the configuration file where the config subset
    read one and is empty where that subset ran and found none, and is
    absent where the subset did not run, since a kind a producer did
    not attempt is not one it carries.  The other two subsets consult
    nothing outside the process, so a gather without config is an
    empty record that still names its producer.

    :param Iterable[str] subsets: The subsets selected, as
        ``select_subsets`` returns them
    :param Optional[dict[str, Any]] user: The ``user`` subset
    :param Optional[dict[str, Any]] python: The ``python`` subset
    :param Optional[dict[str, Any]] config: The ``config`` subset
    :param Optional[str] origin: The FQCN of the module composing
        this, or None to name nobody
    :returns dict[str, Any]: The fact
    """
    selected = set(subsets)
    fact: dict[str, Any] = {}
    files: Optional[list[str]] = None

    if "user" in selected:
        fact["user"] = user
    if "python" in selected:
        fact["python"] = python
    if "config" in selected:
        fact["config"] = config
        path = config.get("path") if isinstance(config, dict) else None
        files = [path] if path else []

    fact[EVIDENCE] = compose_evidence(files=files)

    return name_origins(fact, origin)


__all__ = [
    "SUBSETS",
    "compose_config",
    "compose_controller",
    "compose_python",
    "compose_user",
    "parse_config",
    "select_subsets",
]
