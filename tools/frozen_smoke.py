#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a read-only Simplified Chinese smoke test inside a PyInstaller bundle."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from library.fonts import (
    DEFAULT_THEME_FONT,
    SYSTEM_CJK_BOLD,
    SYSTEM_CJK_REGULAR,
    find_cjk_font,
    resolve_theme_font,
)
from library.i18n import Translator, get_language, set_language
from library.resources import application_root, resource_path

CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
THEME_NAME = "3.5inchTheme2-zh-CN"
EXPECTED_SIZE = (320, 480)

CONFIGURATION_UI_KEYS: Mapping[str, str] = {
    "title": "app.configuration_title",
    "display_section": "config.display_section",
    "model": "config.smart_screen_model",
    "theme": "config.theme",
    "hardware": "config.hardware_monitoring",
    "language": "config.interface_language",
    "save": "common.save_settings",
    "save_and_run": "common.save_and_run",
}
THEME_EDITOR_UI_KEYS: Mapping[str, str] = {
    "title": "app.theme_editor_title",
    "zoom_in": "theme_editor.zoom_in",
    "zoom_out": "theme_editor.zoom_out",
    "coordinate_hint": "theme_editor.coordinate_hint",
    "reload_hint": "theme_editor.reload_hint",
}
LANGUAGE_INDEPENDENT_UI_VALUES: Mapping[str, str] = {
    "app.configuration_title": "DMC",
    "app.theme_editor_title": "DMC",
}

SOURCE_CONTRACTS: Mapping[str, Mapping[str, str]] = {
    "configure.py": CONFIGURATION_UI_KEYS,
    "theme-editor.py": THEME_EDITOR_UI_KEYS,
}


class FrozenSmokeError(RuntimeError):
    """Raised when the frozen localization smoke contract is not satisfied."""


def _contains_cjk(value: str) -> bool:
    return bool(CJK_PATTERN.search(value))


def _require_frozen_bundle() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if not bundle_root:
        raise FrozenSmokeError("The smoke executable is not running from PyInstaller")
    resolved = Path(bundle_root).resolve()
    if application_root() != resolved:
        raise FrozenSmokeError(
            "PyInstaller resource root does not match library.resources.application_root()"
        )
    return resolved


def _translated_contract(
    translator: Translator,
    keys: Mapping[str, str],
) -> Dict[str, str]:
    translated: Dict[str, str] = {}
    for name, key in keys.items():
        value = translator(key)
        if value == key:
            raise FrozenSmokeError(f"Missing Simplified Chinese translation key: {key}")

        expected_value = LANGUAGE_INDEPENDENT_UI_VALUES.get(key)
        if expected_value is not None:
            if value != expected_value:
                raise FrozenSmokeError(
                    "Language-independent UI value mismatch: "
                    f"{key}={value!r}, expected {expected_value!r}"
                )
        elif not _contains_cjk(value):
            raise FrozenSmokeError(
                f"Simplified Chinese UI value does not contain CJK text: {key}"
            )
        translated[name] = value
    return translated


def _verify_source_contracts() -> Dict[str, Dict[str, bool]]:
    results: Dict[str, Dict[str, bool]] = {}
    for filename, contract in SOURCE_CONTRACTS.items():
        source_path = resource_path(filename)
        try:
            source = source_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise FrozenSmokeError(
                f"Bundled UI source contract is unavailable: {source_path}"
            ) from exc

        file_results: Dict[str, bool] = {}
        for name, key in contract.items():
            double_quoted = f'tr("{key}")'
            single_quoted = f"tr('{key}')"
            present = double_quoted in source or single_quoted in source
            if not present:
                raise FrozenSmokeError(
                    f"{filename} no longer references required localization key {key}"
                )
            file_results[name] = present
        results[filename] = file_results
    return results


def _font_contract() -> Dict[str, Any]:
    regular_system = find_cjk_font(weight="regular")
    bold_system = find_cjk_font(weight="bold")
    regular_resolved = Path(resolve_theme_font(SYSTEM_CJK_REGULAR))
    bold_resolved = Path(resolve_theme_font(SYSTEM_CJK_BOLD))

    if regular_system and bold_system:
        if regular_resolved.resolve() != Path(regular_system).resolve():
            raise FrozenSmokeError("Regular system CJK font alias resolved unexpectedly")
        if bold_resolved.resolve() != Path(bold_system).resolve():
            raise FrozenSmokeError("Bold system CJK font alias resolved unexpectedly")
        return {
            "mode": "system",
            "regular_name": regular_resolved.name,
            "bold_name": bold_resolved.name,
            "notice": None,
        }

    expected_fallback = resource_path("res", "fonts", DEFAULT_THEME_FONT).resolve()
    if not regular_system and regular_resolved.resolve() != expected_fallback:
        raise FrozenSmokeError("Regular CJK alias did not fall back to Roboto Mono")
    if not bold_system and bold_resolved.resolve() != expected_fallback:
        raise FrozenSmokeError("Bold CJK alias did not fall back to Roboto Mono")

    translator = Translator(language="zh_CN")
    notice = translator("error.cjk_font_missing")
    print(f"[frozen-smoke] {notice}", file=sys.stderr)
    return {
        "mode": "fallback",
        "regular_name": regular_resolved.name,
        "bold_name": bold_resolved.name,
        "notice": notice,
    }


def _prepare_simulated_configuration() -> None:
    from library import config as app_config

    app_config.CONFIG_DATA.setdefault("config", {})
    app_config.CONFIG_DATA.setdefault("display", {})
    app_config.CONFIG_DATA["config"]["LANGUAGE"] = "zh_CN"
    app_config.CONFIG_DATA["config"]["HW_SENSORS"] = "STATIC"
    app_config.CONFIG_DATA["config"]["THEME"] = THEME_NAME
    app_config.CONFIG_DATA["display"]["REVISION"] = "SIMU"
    app_config.CONFIG_DATA["display"]["RESET_ON_STARTUP"] = False
    app_config.load_theme()

    if app_config.CONFIG_DATA["config"]["HW_SENSORS"] != "STATIC":
        raise FrozenSmokeError("Frozen smoke hardware mode is not STATIC")
    if app_config.CONFIG_DATA["display"]["REVISION"] != "SIMU":
        raise FrozenSmokeError("Frozen smoke display revision is not SIMU")
    if app_config.CONFIG_DATA["config"]["THEME"] != THEME_NAME:
        raise FrozenSmokeError("Frozen smoke did not select the Simplified Chinese theme")


def _render_theme(output: Path) -> Dict[str, Any]:
    from library.lcd import lcd_simulated

    lcd_simulated.WEBSERVER_PORT = 0
    _prepare_simulated_configuration()

    from library import config as app_config
    from library.display import display

    lcd = display.lcd
    if lcd is None:
        raise FrozenSmokeError("Simulated display was not created")

    try:
        display.initialize_display()
        display.display_static_images()
        display.display_static_text()
        image = lcd.screen_image.copy()
        if image.size != EXPECTED_SIZE:
            raise FrozenSmokeError(
                f"Unexpected rendered size: {image.size}, expected {EXPECTED_SIZE}"
            )

        extrema = image.getextrema()
        if not extrema or all(low == high for low, high in extrema):
            raise FrozenSmokeError("Rendered Simplified Chinese theme is blank")

        output.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, "PNG")
        if not output.is_file() or output.stat().st_size <= 0:
            raise FrozenSmokeError("Rendered PNG was not written")

        static_text = app_config.THEME_DATA.get("static_text", {})
        cjk_labels = sum(
            1
            for value in static_text.values()
            if isinstance(value, Mapping)
            and _contains_cjk(str(value.get("TEXT", "")))
        )
        if cjk_labels <= 0:
            raise FrozenSmokeError("Selected theme contains no Simplified Chinese labels")

        return {
            "revision": app_config.CONFIG_DATA["display"]["REVISION"],
            "hardware": app_config.CONFIG_DATA["config"]["HW_SENSORS"],
            "theme": app_config.CONFIG_DATA["config"]["THEME"],
            "size": list(image.size),
            "cjk_label_count": cjk_labels,
            "png_size_bytes": output.stat().st_size,
        }
    finally:
        if hasattr(lcd, "closeSerial"):
            try:
                lcd.closeSerial()
            except Exception:
                pass
        web_server = getattr(lcd, "webServer", None)
        if web_server is not None:
            try:
                web_server.server_close()
            except Exception:
                pass


def run_smoke(output: Path, report: Path) -> Dict[str, Any]:
    bundle_root = _require_frozen_bundle()
    if os.environ.get("TURING_LANGUAGE") != "zh_CN":
        raise FrozenSmokeError("TURING_LANGUAGE must be set to zh_CN")

    resolved_language = set_language("auto")
    if resolved_language != "zh_CN" or get_language() != "zh_CN":
        raise FrozenSmokeError("Frozen translator did not resolve zh_CN")

    translator = Translator(language="auto")
    configuration_ui = _translated_contract(translator, CONFIGURATION_UI_KEYS)
    theme_editor_ui = _translated_contract(translator, THEME_EDITOR_UI_KEYS)
    source_contracts = _verify_source_contracts()
    font = _font_contract()
    simulation = _render_theme(output)

    result: Dict[str, Any] = {
        "schema_version": 1,
        "frozen": True,
        "meipass_detected": True,
        "resource_root_matches": application_root() == bundle_root,
        "bundle_root_name": bundle_root.name,
        "language": resolved_language,
        "configuration_ui": configuration_ui,
        "theme_editor_ui": theme_editor_ui,
        "source_contracts": source_contracts,
        "font": font,
        "simulation": simulation,
    }

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = run_smoke(args.output.resolve(), args.report.resolve())
    except FrozenSmokeError as exc:
        print(f"[frozen-smoke] {exc}", file=sys.stderr)
        return 1

    print(
        "[frozen-smoke] "
        f"zh_CN {result['simulation']['theme']} "
        f"{result['simulation']['size'][0]}x{result['simulation']['size'][1]} "
        f"font={result['font']['mode']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
