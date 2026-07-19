#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import localization_coverage  # noqa: E402


class CoverageFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "locales").mkdir(parents=True)
        (root / "library").mkdir()
        (root / "tools" / "windows-installer").mkdir(parents=True)
        self.write_catalogs(
            {"ui": {"save": "Save {name}"}},
            {"ui": {"save": "保存 {name}"}},
        )
        self.write("configure.py", 'from library.i18n import tr\ntr("ui.save", name="x")\n')
        self.write("theme-editor.py", "")
        self.write("main.py", "")
        self.write("library/i18n.py", "")
        self.write_allowlist([])

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_catalogs(self, english: object, chinese: object) -> None:
        self.write("locales/en_US.json", json.dumps(english, ensure_ascii=False))
        self.write("locales/zh_CN.json", json.dumps(chinese, ensure_ascii=False))

    def write_allowlist(self, entries: list[dict[str, str]]) -> None:
        self.write(
            "tools/localization-allowlist.json",
            json.dumps({"version": 1, "entries": entries}, ensure_ascii=False),
        )

    def audit(self) -> dict[str, object]:
        return localization_coverage.audit_repository(
            self.root,
            self.root / "tools" / "localization-allowlist.json",
        )


class LocalizationCoverageTests(unittest.TestCase):
    def with_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        return CoverageFixture(root)

    @staticmethod
    def rules(report, severity=None):
        return {
            issue["rule"]
            for issue in report["issues"]
            if severity is None or issue["severity"] == severity
        }

    def test_matching_catalogs_and_placeholders_have_no_errors(self):
        fixture = self.with_fixture()
        report = fixture.audit()
        self.assertEqual(report["summary"]["errors"], 0)

    def test_catalog_key_mismatch_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write_catalogs(
            {"ui": {"save": "Save", "cancel": "Cancel"}},
            {"ui": {"save": "保存", "extra": "额外"}},
        )
        report = fixture.audit()
        self.assertIn("catalog-key-missing", self.rules(report, "error"))
        self.assertIn("catalog-key-extra", self.rules(report, "error"))

    def test_placeholder_mismatch_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write_catalogs(
            {"ui": {"save": "Save {name} at {x:.0f}"}},
            {"ui": {"save": "保存 {name} 于 {x}"}},
        )
        report = fixture.audit()
        self.assertIn("placeholder-mismatch", self.rules(report, "error"))

    def test_nested_placeholder_fields_are_compared(self):
        fixture = self.with_fixture()
        fixture.write_catalogs(
            {"ui": {"save": "Save {value:{width}}"}},
            {"ui": {"save": "保存 {value:{size}}"}},
        )
        report = fixture.audit()
        self.assertIn("placeholder-mismatch", self.rules(report, "error"))

    def test_missing_referenced_key_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write("configure.py", 'from library.i18n import tr\ntr("ui.missing")\n')
        report = fixture.audit()
        self.assertIn("translation-key-missing-en", self.rules(report, "error"))
        self.assertIn("translation-key-missing-zh", self.rules(report, "error"))

    def test_hardcoded_user_visible_english_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write("configure.py", 'Label(text="Save settings")\n')
        report = fixture.audit()
        findings = [
            issue
            for issue in report["issues"]
            if issue["rule"] == "hardcoded-user-visible"
        ]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "error")

    def test_internal_enums_are_not_reported_outside_ui(self):
        fixture = self.with_fixture()
        fixture.write(
            "configure.py",
            'REVISION = "SIMU"\nMODE = "STATIC"\nUNITS = "metric"\n',
        )
        report = fixture.audit()
        self.assertNotIn("hardcoded-user-visible", self.rules(report))
        self.assertNotIn("internal-value-in-ui", self.rules(report))

    def test_internal_enum_used_as_ui_text_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write("configure.py", 'Label(text="AUTO")\n')
        report = fixture.audit()
        self.assertIn("internal-value-in-ui", self.rules(report, "error"))

    def test_urls_paths_and_protocol_constants_are_not_reported(self):
        fixture = self.with_fixture()
        fixture.write(
            "configure.py",
            'print("https://github.com/example/repo")\n'
            'logger.warning("C:\\\\Windows\\\\Fonts\\\\msyh.ttc")\n'
            'PROTOCOL = "TUR_USB"\n',
        )
        report = fixture.audit()
        self.assertNotIn("hardcoded-user-visible", self.rules(report))
        self.assertNotIn("possible-user-visible-output", self.rules(report))

    def test_dynamic_translation_key_is_a_warning(self):
        fixture = self.with_fixture()
        fixture.write(
            "configure.py",
            "from library.i18n import tr\nkey_name = 'ui.save'\ntr(key_name)\n",
        )
        report = fixture.audit()
        self.assertIn("dynamic-translation-key", self.rules(report, "warning"))

    def test_translator_instance_and_direct_call_are_analyzed(self):
        fixture = self.with_fixture()
        fixture.write(
            "configure.py",
            "from library.i18n import Translator\n"
            "translator = Translator()\n"
            "translator('ui.save', name='x')\n"
            "Translator()('ui.save', name='x')\n",
        )
        report = fixture.audit()
        self.assertNotIn("translation-key-unused", self.rules(report))

    def test_no_cjk_entry_requires_precise_allowlist(self):
        fixture = self.with_fixture()
        fixture.write_catalogs(
            {"model": {"name": "UsbPCMonitor"}},
            {"model": {"name": "UsbPCMonitor"}},
        )
        fixture.write("configure.py", 'from library.i18n import tr\ntr("model.name")\n')
        report = fixture.audit()
        self.assertIn("zh-entry-without-cjk", self.rules(report, "error"))

        fixture.write_allowlist(
            [
                {
                    "path": "locales/zh_CN.json",
                    "rule": "zh-entry-without-cjk",
                    "key": "model.name",
                    "category": "product-name",
                    "reason": "UsbPCMonitor is the unchanged product name.",
                }
            ]
        )
        report = fixture.audit()
        self.assertNotIn("zh-entry-without-cjk", self.rules(report, "error"))
        self.assertIn("allowlisted", self.rules(report, "info"))

    def test_allowlist_wildcard_is_rejected(self):
        fixture = self.with_fixture()
        fixture.write_allowlist(
            [
                {
                    "path": "library/**/*.py",
                    "rule": "hardcoded-user-visible",
                    "value": "Save settings",
                    "category": "technical-term",
                    "reason": "This intentionally broad rule must be rejected.",
                }
            ]
        )
        report = fixture.audit()
        self.assertIn("allowlist-invalid", self.rules(report, "error"))

    def test_unused_allowlist_entry_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write_allowlist(
            [
                {
                    "path": "configure.py",
                    "rule": "hardcoded-user-visible",
                    "value": "No longer present",
                    "category": "technical-term",
                    "reason": "The exact historical exception is now stale.",
                }
            ]
        )
        report = fixture.audit()
        self.assertIn("allowlist-unused", self.rules(report, "error"))

    def test_malformed_chinese_placeholder_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write_catalogs(
            {"ui": {"save": "Save {name}"}},
            {"ui": {"save": "保存 {name"}},
        )
        report = fixture.audit()
        self.assertIn("placeholder-invalid-zh", self.rules(report, "error"))

    def test_installer_localized_messages_and_visible_descriptions(self):
        fixture = self.with_fixture()
        fixture.write(
            "tools/windows-installer/example.iss",
            "[Languages]\n"
            'Name: "english"; MessagesFile: "compiler:Default.isl"\n'
            "[CustomMessages]\n"
            "english.InstallType=Default installation\n"
            "chinesesimplified.InstallType=默认安装\n"
            "[Types]\n"
            'Name: "default"; Description: "{cm:InstallType}"\n',
        )
        report = fixture.audit()
        self.assertNotIn("installer-hardcoded-user-visible", self.rules(report))
        self.assertNotIn("installer-translation-missing-zh", self.rules(report))

    def test_installer_hardcoded_description_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write(
            "tools/windows-installer/example.iss",
            "[Types]\n"
            'Name: "default"; Description: "Default installation"\n',
        )
        report = fixture.audit()
        self.assertIn(
            "installer-hardcoded-user-visible",
            self.rules(report, "error"),
        )

    def test_installer_missing_chinese_custom_message_is_an_error(self):
        fixture = self.with_fixture()
        fixture.write(
            "tools/windows-installer/example.iss",
            "[CustomMessages]\n"
            "english.InstallType=Default installation\n",
        )
        report = fixture.audit()
        self.assertIn("installer-translation-missing-zh", self.rules(report, "error"))

    def test_reports_are_stable_and_hide_absolute_paths(self):
        fixture = self.with_fixture()
        first = fixture.audit()
        second = fixture.audit()
        json_first = localization_coverage.render_json(first)
        json_second = localization_coverage.render_json(second)
        markdown = localization_coverage.render_markdown(first)
        self.assertEqual(json_first, json_second)
        self.assertNotIn(str(fixture.root), json_first)
        self.assertNotIn(str(fixture.root), markdown)
        self.assertIn("# Simplified Chinese localization coverage", markdown)

    def test_build_dist_and_cache_are_not_scanned(self):
        fixture = self.with_fixture()
        fixture.write("build/bad.py", 'Label(text="Build output")\n')
        fixture.write("dist/bad.py", 'Label(text="Dist output")\n')
        fixture.write("library/__pycache__/bad.py", 'Label(text="Cache output")\n')
        report = fixture.audit()
        scanned = report["scanned_files"]
        self.assertFalse(any(path.startswith("build/") for path in scanned))
        self.assertFalse(any(path.startswith("dist/") for path in scanned))
        self.assertFalse(any("__pycache__" in path for path in scanned))

    def test_json_and_markdown_cli_outputs(self):
        fixture = self.with_fixture()
        json_path = fixture.root / "report.json"
        markdown_path = fixture.root / "report.md"
        json_result = localization_coverage.main(
            [
                "--repository-root",
                str(fixture.root),
                "--format",
                "json",
                "--output",
                str(json_path),
                "--fail-on-errors",
            ]
        )
        markdown_result = localization_coverage.main(
            [
                "--repository-root",
                str(fixture.root),
                "--format",
                "markdown",
                "--output",
                str(markdown_path),
            ]
        )
        self.assertEqual(json_result, 0)
        self.assertEqual(markdown_result, 0)
        self.assertEqual(json.loads(json_path.read_text())["schema_version"], 1)
        self.assertIn("## Findings", markdown_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
