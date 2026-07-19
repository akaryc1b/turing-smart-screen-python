#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve bundled theme fonts and optional system CJK font aliases."""

from __future__ import annotations

import os
import platform
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from library.i18n import tr
from library.log import logger
from library.resources import resource_path

SYSTEM_CJK_REGULAR = "system:cjk"
SYSTEM_CJK_BOLD = "system:cjk-bold"
DEFAULT_THEME_FONT = "roboto-mono/RobotoMono-Regular.ttf"

_FONT_EXTENSIONS = {".ttf", ".ttc", ".otf", ".otc"}
_WEIGHT_ALIASES = {
    "normal": "regular",
    "regular": "regular",
    "medium": "regular",
    "bold": "bold",
    "semibold": "bold",
    "demibold": "bold",
}

# Ordered by preference. Filenames cover common installations whose on-disk
# names do not resemble the user-facing font family name.
_FONT_CANDIDATES = {
    "Windows": (
        ("Microsoft YaHei", {
            "regular": ("msyh.ttc", "msyh.ttf", "msyhl.ttc"),
            "bold": ("msyhbd.ttc", "msyhbd.ttf", "msyh.ttc"),
        }),
        ("Microsoft YaHei UI", {
            "regular": ("msyh.ttc", "msyh.ttf"),
            "bold": ("msyhbd.ttc", "msyhbd.ttf", "msyh.ttc"),
        }),
        ("SimHei", {
            "regular": ("simhei.ttf", "simhei.ttc"),
            "bold": ("simhei.ttf", "simhei.ttc"),
        }),
        ("SimSun", {
            "regular": ("simsun.ttc", "simsun.ttf"),
            "bold": ("simsun.ttc", "simsun.ttf"),
        }),
        ("Noto Sans CJK SC", {
            "regular": ("NotoSansCJK-Regular.ttc", "NotoSansSC-Regular.otf"),
            "bold": ("NotoSansCJK-Bold.ttc", "NotoSansSC-Bold.otf"),
        }),
    ),
    "Darwin": (
        ("PingFang SC", {
            "regular": ("PingFang.ttc", "PingFang SC.ttf"),
            "bold": ("PingFang.ttc", "PingFang SC Bold.ttf"),
        }),
        ("Hiragino Sans GB", {
            "regular": ("Hiragino Sans GB.ttc", "HiraginoSansGB-W3.otf"),
            "bold": ("Hiragino Sans GB.ttc", "HiraginoSansGB-W6.otf"),
        }),
        ("Songti SC", {
            "regular": ("Songti.ttc", "Songti SC.ttc"),
            "bold": ("Songti.ttc", "Songti SC Bold.ttf"),
        }),
        ("Heiti SC", {
            "regular": ("STHeiti Light.ttc", "STHeiti Medium.ttc"),
            "bold": ("STHeiti Medium.ttc", "STHeiti Light.ttc"),
        }),
        ("Noto Sans CJK SC", {
            "regular": ("NotoSansCJK-Regular.ttc", "NotoSansSC-Regular.otf"),
            "bold": ("NotoSansCJK-Bold.ttc", "NotoSansSC-Bold.otf"),
        }),
    ),
    "Linux": (
        ("Noto Sans CJK SC", {
            "regular": ("NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf"),
            "bold": ("NotoSansCJK-Bold.ttc", "NotoSansCJKsc-Bold.otf"),
        }),
        ("Noto Sans SC", {
            "regular": ("NotoSansSC-Regular.otf", "NotoSansSC-Regular.ttf"),
            "bold": ("NotoSansSC-Bold.otf", "NotoSansSC-Bold.ttf"),
        }),
        ("WenQuanYi Micro Hei", {
            "regular": ("wqy-microhei.ttc", "wqy-microhei.ttf"),
            "bold": ("wqy-microhei.ttc", "wqy-microhei.ttf"),
        }),
        ("WenQuanYi Zen Hei", {
            "regular": ("wqy-zenhei.ttc", "wqy-zenhei.ttf"),
            "bold": ("wqy-zenhei.ttc", "wqy-zenhei.ttf"),
        }),
        ("Source Han Sans SC", {
            "regular": ("SourceHanSansSC-Regular.otf", "SourceHanSansCN-Regular.otf"),
            "bold": ("SourceHanSansSC-Bold.otf", "SourceHanSansCN-Bold.otf"),
        }),
    ),
}


def normalize_weight(weight: str = "regular") -> str:
    """Normalize a requested font weight to ``regular`` or ``bold``."""

    return _WEIGHT_ALIASES.get(str(weight).strip().lower(), "regular")


def system_font_roots(
    platform_name: Optional[str] = None,
    environ: Optional[Mapping[str, str]] = None,
    home: Optional[Path] = None,
) -> Tuple[Path, ...]:
    """Return conventional per-platform font directories in priority order."""

    current_platform = platform_name or platform.system()
    env = os.environ if environ is None else environ
    user_home = Path.home() if home is None else Path(home)

    if current_platform == "Windows":
        windows_dir = Path(env.get("WINDIR", r"C:\Windows"))
        roots = [windows_dir / "Fonts"]
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data:
            roots.append(Path(local_app_data) / "Microsoft" / "Windows" / "Fonts")
        return tuple(roots)

    if current_platform == "Darwin":
        return (
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            user_home / "Library" / "Fonts",
        )

    return (
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        user_home / ".local" / "share" / "fonts",
        user_home / ".fonts",
    )


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _scan_font_files(roots: Sequence[Path]) -> Tuple[Path, ...]:
    files = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            files.extend(
                path for path in root.rglob("*")
                if path.is_file() and path.suffix.lower() in _FONT_EXTENSIONS
            )
        except OSError:
            logger.debug("Unable to scan font directory %s", root, exc_info=True)
    return tuple(files)


@lru_cache(maxsize=32)
def _cached_font_files(roots: Tuple[str, ...]) -> Tuple[Path, ...]:
    return _scan_font_files(tuple(Path(root) for root in roots))


def _filename_lookup(font_files: Iterable[Path]) -> Mapping[str, Path]:
    return {path.name.lower(): path for path in font_files}


def _match_family_fallback(
    font_files: Sequence[Path],
    family_name: str,
    weight: str,
) -> Optional[Path]:
    family_token = _normalize_name(family_name)
    weight_tokens = ("bold", "semibold", "demibold", "black")
    matches = [
        path for path in font_files
        if family_token in _normalize_name(path.stem)
    ]
    if weight == "bold":
        weighted = [
            path for path in matches
            if any(token in path.stem.lower() for token in weight_tokens)
        ]
        if weighted:
            return sorted(weighted, key=lambda path: str(path).lower())[0]
    else:
        regular = [
            path for path in matches
            if not any(token in path.stem.lower() for token in weight_tokens)
        ]
        if regular:
            return sorted(regular, key=lambda path: str(path).lower())[0]
    return sorted(matches, key=lambda path: str(path).lower())[0] if matches else None


def find_cjk_font(
    weight: str = "regular",
    platform_name: Optional[str] = None,
    search_roots: Optional[Sequence[Path]] = None,
) -> Optional[str]:
    """Return a real system font path suitable for Pillow, or ``None``.

    Search results are cached by platform, weight, and root list so rendering
    loops never rescan system font directories on every frame.
    """

    current_platform = platform_name or platform.system()
    normalized_weight = normalize_weight(weight)
    roots = tuple(search_roots or system_font_roots(current_platform))
    cache_key = tuple(str(Path(root).expanduser()) for root in roots)
    font_files = _cached_font_files(cache_key)
    by_filename = _filename_lookup(font_files)

    candidates = _FONT_CANDIDATES.get(current_platform, _FONT_CANDIDATES["Linux"])
    for family_name, filenames_by_weight in candidates:
        for filename in filenames_by_weight[normalized_weight]:
            match = by_filename.get(filename.lower())
            if match and match.is_file():
                return str(match.resolve())

        match = _match_family_fallback(font_files, family_name, normalized_weight)
        if match and match.is_file():
            return str(match.resolve())

    return None


def clear_font_cache() -> None:
    """Clear cached directory scans, primarily for tests and font installs."""

    _cached_font_files.cache_clear()


def is_system_font_alias(font_config: str) -> bool:
    return str(font_config).strip().lower() in {SYSTEM_CJK_REGULAR, SYSTEM_CJK_BOLD}


def resolve_theme_font(
    font_config: Optional[str],
    fonts_dir: Optional[Path] = None,
) -> str:
    """Resolve a theme ``FONT`` value to a Pillow-compatible path.

    Existing relative theme paths keep their original meaning below
    ``res/fonts``. Only the explicit ``system:cjk`` aliases trigger system font
    discovery, which keeps all existing community themes backward compatible.
    """

    configured = str(font_config or DEFAULT_THEME_FONT).strip()
    path = Path(configured).expanduser()
    if path.is_absolute():
        return str(path)

    alias = configured.lower()
    if alias in {SYSTEM_CJK_REGULAR, SYSTEM_CJK_BOLD}:
        weight = "bold" if alias == SYSTEM_CJK_BOLD else "regular"
        system_path = find_cjk_font(weight=weight)
        if system_path:
            return system_path

        logger.error(tr("error.cjk_font_missing"))
        configured = DEFAULT_THEME_FONT

    bundled_root = Path(fonts_dir) if fonts_dir is not None else resource_path("res", "fonts")
    return str(bundled_root / configured)
