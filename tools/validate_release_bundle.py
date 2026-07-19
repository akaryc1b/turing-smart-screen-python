#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate that a generated release bundle contains usable localization assets."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from unittest.mock import patch

import yaml
from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
FONT_BINARY_SUFFIXES = {".ttf", ".ttc", ".otf", ".otc", ".woff", ".woff2"}
CHINESE_THEME = Path("res/themes/3.5inchTheme2-zh-CN")
COMMON_REQUIRED_FILES = (
    Path("config.yaml"),
    Path("locales/en_US.json"),
    Path("locales/zh_CN.json"),
    CHINESE_THEME / "theme.yaml",
    CHINESE_THEME / "background.png",
    CHINESE_THEME / "preview.png",
    Path("res/fonts/roboto-mono/RobotoMono-Regular.ttf"),
)
EXECUTABLES = {
    "windows": (Path("configure.exe"), Path("main.exe"), Path("theme-editor.exe")),
    "linux": (Path("configure"), Path("main"), Path("theme-editor"), Path("turing-smart-screen")),
}


class BundleValidationError(RuntimeError):
    """Raised when one or more release-bundle requirements are not met."""


def _flatten_catalog(values: Mapping[str, Any], prefix: str = "") -> Dict[str, str]:
    flattened: Dict[str, str] = {}
    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_catalog(value, full_key))
        elif isinstance(value, str):
            flattened[full_key] = value
        else:
            raise ValueError(f"Translation value for '{full_key}' must be a string")
    return flattened


def _load_catalog(path: Path, errors: List[str]) -> Dict[str, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid translation catalog {path}: {exc}")
        return {}

    if not isinstance(data, Mapping):
        errors.append(f"Translation catalog root must be an object: {path}")
        return {}

    try:
        return _flatten_catalog(data)
    except ValueError as exc:
        errors.append(f"Invalid translation catalog {path}: {exc}")
        return {}


def _validate_required_paths(bundle_root: Path, platform_name: str, errors: List[str]) -> None:
    for relative_path in COMMON_REQUIRED_FILES:
        path = bundle_root / relative_path
        if not path.is_file():
            errors.append(f"Missing required release file: {relative_path}")

    for relative_path in EXECUTABLES[platform_name]:
        path = bundle_root / relative_path
        if not (path.is_file() or path.is_symlink()):
            errors.append(f"Missing packaged executable: {relative_path}")

    for relative_path in (Path("external"), Path("res/fonts"), Path("res/themes")):
        if not (bundle_root / relative_path).is_dir():
            errors.append(f"Missing required release directory: {relative_path}")


def _validate_catalogs(bundle_root: Path, errors: List[str]) -> None:
    english = _load_catalog(bundle_root / "locales/en_US.json", errors)
    chinese = _load_catalog(bundle_root / "locales/zh_CN.json", errors)
    if not english or not chinese:
        return

    missing_in_chinese = set(english) - set(chinese)
    missing_in_english = set(chinese) - set(english)
    if missing_in_chinese or missing_in_english:
        errors.append(
            "Packaged catalog keys differ: "
            f"missing in zh_CN={sorted(missing_in_chinese)}, "
            f"missing in en_US={sorted(missing_in_english)}"
        )

    if not any(CJK_PATTERN.search(value) for value in chinese.values()):
        errors.append("Packaged zh_CN catalog does not contain CJK text")

    from library import resources
    from library.i18n import Translator

    with patch.object(resources.sys, "_MEIPASS", str(bundle_root), create=True):
        translator = Translator("auto", environ={"TURING_LANGUAGE": "zh_CN"})

    if translator.locale != "zh_CN":
        errors.append("TURING_LANGUAGE=zh_CN did not select the packaged Chinese catalog")
    expected_title = chinese.get("app.configuration_title")
    if expected_title and translator("app.configuration_title") != expected_title:
        errors.append("Packaged translator did not return the Simplified Chinese title")


def _validate_png(path: Path, expected_size: Sequence[int], errors: List[str]) -> None:
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                errors.append(f"Theme image is not PNG: {path}")
            if image.size != tuple(expected_size):
                errors.append(
                    f"Theme image has unexpected dimensions {image.size}: {path}; "
                    f"expected {tuple(expected_size)}"
                )
            image.verify()
    except (OSError, ValueError) as exc:
        errors.append(f"Invalid theme image {path}: {exc}")


def _validate_chinese_theme(bundle_root: Path, errors: List[str]) -> None:
    theme_root = bundle_root / CHINESE_THEME
    theme_path = theme_root / "theme.yaml"
    try:
        theme = yaml.safe_load(theme_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        errors.append(f"Invalid packaged Chinese theme YAML: {exc}")
        return

    if not isinstance(theme, Mapping):
        errors.append("Packaged Chinese theme root must be a mapping")
        return

    display = theme.get("display", {})
    if display.get("DISPLAY_SIZE") != '3.5"':
        errors.append("Packaged Chinese theme no longer targets the 3.5-inch display")
    if display.get("DISPLAY_ORIENTATION") != "portrait":
        errors.append("Packaged Chinese theme no longer targets portrait orientation")

    _validate_png(theme_root / "background.png", (320, 480), errors)
    _validate_png(theme_root / "preview.png", (320, 480), errors)

    labels = theme.get("static_text", {})
    if not isinstance(labels, Mapping):
        errors.append("Packaged Chinese theme static_text must be a mapping")
        return

    chinese_labels = [
        data
        for data in labels.values()
        if isinstance(data, Mapping) and CJK_PATTERN.search(str(data.get("TEXT", "")))
    ]
    if len(chinese_labels) < 10:
        errors.append("Packaged Chinese theme contains too few Chinese labels")
    for data in chinese_labels:
        if data.get("FONT") not in {"system:cjk", "system:cjk-bold"}:
            errors.append(
                f"Chinese label does not use a CJK system-font alias: {data.get('TEXT', '')}"
            )

    font_binaries = [
        path.relative_to(theme_root)
        for path in theme_root.rglob("*")
        if path.is_file() and path.suffix.lower() in FONT_BINARY_SUFFIXES
    ]
    if font_binaries:
        errors.append(f"Chinese theme unexpectedly vendors font binaries: {font_binaries}")


def _validate_cjk_font_fallback(bundle_root: Path, errors: List[str]) -> None:
    from library.fonts import DEFAULT_THEME_FONT, resolve_theme_font

    fonts_root = bundle_root / "res/fonts"
    expected = (fonts_root / DEFAULT_THEME_FONT).resolve()
    with patch("library.fonts.find_cjk_font", return_value=None):
        resolved = Path(resolve_theme_font("system:cjk", fonts_dir=fonts_root)).resolve()

    if resolved != expected:
        errors.append(
            f"Missing-CJK-font fallback resolved to {resolved}, expected bundled font {expected}"
        )
    if not resolved.is_file():
        errors.append(f"Bundled fallback font is missing from the release: {resolved}")


def validate_bundle(bundle_root: Path, platform_name: str) -> None:
    """Validate a built release directory and raise with all detected failures."""

    root = Path(bundle_root).resolve()
    normalized_platform = platform_name.strip().lower()
    if normalized_platform not in EXECUTABLES:
        raise ValueError(f"Unsupported bundle platform: {platform_name}")
    if not root.is_dir():
        raise BundleValidationError(f"Release bundle directory does not exist: {root}")

    errors: List[str] = []
    _validate_required_paths(root, normalized_platform, errors)
    _validate_catalogs(root, errors)
    _validate_chinese_theme(root, errors)
    _validate_cjk_font_fallback(root, errors)

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise BundleValidationError(f"Release bundle validation failed:\n{details}")


def _default_platform() -> str:
    return "windows" if sys.platform.startswith("win") else "linux"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_root", type=Path, help="Generated turing-system-monitor directory")
    parser.add_argument(
        "--platform",
        choices=sorted(EXECUTABLES),
        default=_default_platform(),
        help="Expected executable layout",
    )
    args = parser.parse_args(argv)

    try:
        validate_bundle(args.bundle_root, args.platform)
    except (BundleValidationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Validated {args.platform} release bundle: {args.bundle_root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
