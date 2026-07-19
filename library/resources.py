#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve application resources in source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Union

PathPart = Union[str, Path]


def application_root() -> Path:
    """Return the directory containing bundled application resources.

    PyInstaller extracts one-file applications into ``sys._MEIPASS`` and uses
    the same directory as the resource root for one-folder builds.  Source
    runs use the repository root above the ``library`` package.
    """

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: PathPart) -> Path:
    """Return an absolute path below the active application resource root."""

    return application_root().joinpath(*parts)
