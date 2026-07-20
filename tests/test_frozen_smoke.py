#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from library.i18n import Translator
from tools import frozen_smoke
from tools.run_frozen_smoke import (
    FrozenSmokeRunnerError,
    isolated_environment,
    validate_report,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class FrozenSmokeContractTests(unittest.TestCase):
    def test_required_ui_contracts_resolve_expected_localized_values(self):
        translator = Translator(
            language="zh_CN",
            locales_dir=REPOSITORY_ROOT / "locales",
        )
        for contract in (
            frozen_smoke.CONFIGURATION_UI_KEYS,
            frozen_smoke.THEME_EDITOR_UI_KEYS,
        ):
            translated = frozen_smoke._translated_contract(translator, contract)
            self.assertEqual(set(translated), set(contract))
            self.assertEqual("DMC", translated["title"])
            for name, value in translated.items():
                if name != "title":
                    self.assertRegex(value, frozen_smoke.CJK_PATTERN)

    def test_language_independent_title_rejects_unexpected_brand(self):
        translator = mock.Mock(return_value="Unexpected brand")
        with self.assertRaisesRegex(
            frozen_smoke.FrozenSmokeError,
            "Language-independent UI value mismatch",
        ):
            frozen_smoke._translated_contract(
                translator,
                {"title": "app.configuration_title"},
            )

    def test_actual_ui_sources_reference_the_frozen_contract_keys(self):
        with mock.patch.object(
            frozen_smoke,
            "resource_path",
            side_effect=lambda *parts: REPOSITORY_ROOT.joinpath(*parts),
        ):
            results = frozen_smoke._verify_source_contracts()
        self.assertTrue(all(all(values.values()) for values in results.values()))

    def test_meipass_must_match_application_resource_root(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name).resolve()
            with mock.patch.object(sys, "_MEIPASS", str(root), create=True):
                with mock.patch.object(
                    frozen_smoke,
                    "application_root",
                    return_value=root,
                ):
                    self.assertEqual(frozen_smoke._require_frozen_bundle(), root)

                with mock.patch.object(
                    frozen_smoke,
                    "application_root",
                    return_value=root / "other",
                ):
                    with self.assertRaisesRegex(
                        frozen_smoke.FrozenSmokeError,
                        "resource root",
                    ):
                        frozen_smoke._require_frozen_bundle()

    def test_font_contract_reports_roboto_fallback_and_notice(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            fallback = root / frozen_smoke.DEFAULT_THEME_FONT
            fallback.parent.mkdir(parents=True)
            fallback.write_bytes(b"font")

            with mock.patch.object(
                frozen_smoke,
                "find_cjk_font",
                return_value=None,
            ):
                with mock.patch.object(
                    frozen_smoke,
                    "resolve_theme_font",
                    return_value=str(fallback),
                ):
                    with mock.patch.object(
                        frozen_smoke,
                        "resource_path",
                        return_value=fallback,
                    ):
                        contract = frozen_smoke._font_contract()

            self.assertEqual(contract["mode"], "fallback")
            self.assertEqual(contract["regular_name"], fallback.name)
            self.assertIn("中文字体", contract["notice"])


class FrozenSmokeRunnerTests(unittest.TestCase):
    def _valid_report(self):
        translator = Translator(
            language="zh_CN",
            locales_dir=REPOSITORY_ROOT / "locales",
        )
        return {
            "schema_version": 1,
            "frozen": True,
            "meipass_detected": True,
            "resource_root_matches": True,
            "language": "zh_CN",
            "configuration_ui": frozen_smoke._translated_contract(
                translator,
                frozen_smoke.CONFIGURATION_UI_KEYS,
            ),
            "theme_editor_ui": frozen_smoke._translated_contract(
                translator,
                frozen_smoke.THEME_EDITOR_UI_KEYS,
            ),
            "font": {
                "mode": "fallback",
                "notice": translator("error.cjk_font_missing"),
            },
            "simulation": {
                "revision": "SIMU",
                "hardware": "STATIC",
                "theme": frozen_smoke.THEME_NAME,
                "size": [320, 480],
                "cjk_label_count": 12,
            },
        }

    def test_report_and_png_validation_accept_expected_contract(self):
        with tempfile.TemporaryDirectory() as temp_name:
            screenshot = Path(temp_name) / "smoke.png"
            image = Image.new("RGB", (320, 480), "white")
            image.putpixel((10, 10), (0, 0, 0))
            image.save(screenshot)
            validate_report(self._valid_report(), screenshot)

    def test_report_validation_rejects_non_frozen_execution(self):
        with tempfile.TemporaryDirectory() as temp_name:
            screenshot = Path(temp_name) / "smoke.png"
            image = Image.new("RGB", (320, 480), "white")
            image.putpixel((10, 10), (0, 0, 0))
            image.save(screenshot)
            report = self._valid_report()
            report["frozen"] = False
            with self.assertRaisesRegex(FrozenSmokeRunnerError, "PyInstaller"):
                validate_report(report, screenshot)

    def test_report_validation_rejects_unexpected_brand(self):
        with tempfile.TemporaryDirectory() as temp_name:
            screenshot = Path(temp_name) / "smoke.png"
            image = Image.new("RGB", (320, 480), "white")
            image.putpixel((10, 10), (0, 0, 0))
            image.save(screenshot)
            report = self._valid_report()
            report["configuration_ui"]["title"] = "Turing System Monitor"
            with self.assertRaisesRegex(
                FrozenSmokeRunnerError,
                "configuration_ui.title",
            ):
                validate_report(report, screenshot)

    def test_isolated_environment_redirects_user_and_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            env = isolated_environment(root)
            self.assertEqual(env["TURING_LANGUAGE"], "zh_CN")
            for variable in (
                "HOME",
                "USERPROFILE",
                "XDG_CONFIG_HOME",
                "TMPDIR",
                "TMP",
                "TEMP",
            ):
                self.assertTrue(Path(env[variable]).is_relative_to(root))
                self.assertTrue(Path(env[variable]).is_dir())


class FrozenSmokePolicyTests(unittest.TestCase):
    def test_frozen_spec_is_isolated_from_release_specs(self):
        smoke_spec = (REPOSITORY_ROOT / "frozen-smoke.spec").read_text(
            encoding="utf-8"
        )
        for marker in (
            "tools/frozen_smoke.py",
            "configure.py",
            "theme-editor.py",
            "locales",
            "3.5inchTheme2-zh-CN",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, smoke_spec)

        for release_spec in (
            "turing-system-monitor.spec",
            "turing-system-monitor-debug.spec",
        ):
            source = (REPOSITORY_ROOT / release_spec).read_text(encoding="utf-8")
            self.assertNotIn("frozen-smoke", source)
            self.assertNotIn("tools/frozen_smoke.py", source)

    def test_workflow_builds_real_frozen_smokes_with_timeout_and_cleanup(self):
        source = (
            REPOSITORY_ROOT / ".github/workflows/frozen-smoke.yml"
        ).read_text(encoding="utf-8")

        for marker in (
            "pull_request:",
            "contents: read",
            "cancel-in-progress: true",
            "pyinstaller.exe --noconfirm --clean frozen-smoke.spec",
            "pyinstaller --noconfirm --clean frozen-smoke.spec",
            "tools\\run_frozen_smoke.py",
            "tools/run_frozen_smoke.py",
            "--timeout-seconds 90",
            "frozen-zh-cn-smoke-windows",
            "frozen-zh-cn-smoke-linux",
            "actions/upload-artifact@v7",
            "if-no-files-found: error",
            "retention-days: 14",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        self.assertNotIn("continue-on-error", source)
        self.assertNotIn("*.log", source)
        self.assertNotIn(".isl", source)
        self.assertNotIn("apt install", source)
        self.assertNotIn("fonts-", source)

    def test_workflow_artifacts_are_only_png_and_json_evidence(self):
        source = (
            REPOSITORY_ROOT / ".github/workflows/frozen-smoke.yml"
        ).read_text(encoding="utf-8")
        upload_sections = source.split("uses: actions/upload-artifact@v7")[1:]
        self.assertEqual(len(upload_sections), 2)
        for section in upload_sections:
            block = section.split("\n\n", 1)[0]
            self.assertIn("frozen-smoke.png", block)
            self.assertIn("frozen-smoke-report.json", block)
            self.assertNotIn("dist/", block)
            self.assertNotIn("build/", block)


if __name__ == "__main__":
    unittest.main()
