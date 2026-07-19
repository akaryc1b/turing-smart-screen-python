#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHINESE_DOCS = REPOSITORY_ROOT / "docs" / "zh-CN"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class ChineseDocumentationIndexTests(unittest.TestCase):
    def test_root_and_directory_indexes_link_every_chinese_guide(self):
        root_readme = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(
            encoding="utf-8"
        )
        docs_index = (CHINESE_DOCS / "README.md").read_text(encoding="utf-8")
        guides = sorted(
            path.name
            for path in CHINESE_DOCS.glob("*.md")
            if path.name != "README.md"
        )

        for filename in guides:
            with self.subTest(filename=filename):
                self.assertIn(f"docs/zh-CN/{filename}", root_readme)
                self.assertIn(f"({filename})", docs_index)

    def test_local_markdown_links_resolve(self):
        documents = [REPOSITORY_ROOT / "README.zh-CN.md", *CHINESE_DOCS.glob("*.md")]
        failures = []

        for document in documents:
            source = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(source):
                target = raw_target.strip().strip("<>").split(maxsplit=1)[0]
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path_target = target.split("#", 1)[0]
                if not path_target or not path_target.endswith(".md"):
                    continue
                resolved = (document.parent / path_target).resolve()
                if not resolved.is_file():
                    failures.append(
                        f"{document.relative_to(REPOSITORY_ROOT)} -> {raw_target}"
                    )

        self.assertEqual([], failures, "Broken local Markdown links")

    def test_chinese_readme_preserves_required_attribution(self):
        source = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        for marker in (
            "GPL-3.0",
            "mathoudebine/turing-smart-screen-python",
            "不是 Turing",
            "商标均归其各自权利人所有",
            "akaryc1b/turing-smart-screen-python",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


class MaintenanceGuideContentTests(unittest.TestCase):
    def test_contribution_guide_protects_translation_contracts(self):
        source = (CHINESE_DOCS / "contributing.md").read_text(encoding="utf-8")

        for marker in (
            'tr("key")',
            "locales/en_US.json",
            "locales/zh_CN.json",
            "命名占位符",
            "AUTO",
            "SIMU",
            "DISPLAY_REVERSE",
            "system:cjk",
            "tools/validate_release_bundle.py",
            "tools/upstream_sync_report.py",
            "GPL-3.0",
            "Dependency Review",
            "CodeQL",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_glossary_preserves_stable_abbreviations_and_values(self):
        source = (CHINESE_DOCS / "glossary.md").read_text(encoding="utf-8")

        for marker in (
            "配置向导",
            "系统监控程序",
            "主题编辑器",
            "堆叠 PR",
            "共同基线",
            "CPU",
            "GPU",
            "RAM",
            "FPS",
            "TUR_USB",
            "metric",
            "imperial",
            "standard",
            "zh_CN",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_release_checklist_covers_required_workflows_and_artifacts(self):
        source = (CHINESE_DOCS / "release-checklist.md").read_text(
            encoding="utf-8"
        )

        for marker in (
            "Release bundle validation",
            "Localization",
            "Lint with flake8",
            "System Monitor",
            "Simple Program",
            "themes screenshot",
            "Dependency Review",
            "CodeQL",
            "Windows release bundle",
            "Windows Debug bundle",
            "Linux release bundle",
            "Inno Setup",
            "TURING_LANGUAGE=zh_CN",
            "python -m unittest discover -s tests -t . -v",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_upstream_sync_guide_documents_report_contract(self):
        source = (CHINESE_DOCS / "upstream-sync.md").read_text(encoding="utf-8")

        for marker in (
            "tools/upstream_sync_report.py",
            "--upstream-ref upstream/main",
            "--local-ref HEAD",
            "--format markdown",
            "--format json",
            "--fail-on-overlap",
            "路径级重叠",
            "agent/zh-cn-release-validation",
            "agent/zh-cn-maintenance",
            "agent/zh-cn-security-ci",
            "agent/zh-cn-integration-review",
            "agent/zh-cn-upstream-compat",
            "python -m unittest discover -s tests -t . -v",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_upstream_sync_guide_records_latest_verified_audit(self):
        source = (CHINESE_DOCS / "upstream-sync.md").read_text(encoding="utf-8")

        for marker in (
            "2026-07-19 上游兼容审计记录",
            "a3a375dbfe52ae8ee48349cb6ff476c4767a232a",
            "6fb4dc5f8cb5dfea02f47e3c8ac23e999f526e93",
            "上游变化路径：0",
            "汉化变化路径：57",
            "路径级重叠：0",
            "新增 35、修改 22",
            "没有上游新增用户可见文本",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_generated_maintenance_artifacts_are_ignored_and_not_committed(self):
        ignore_source = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
        ignored_paths = (
            "/upstream-sync-report.md",
            "/upstream-sync-report.json",
            "/localization-coverage.json",
            "/localization-coverage.md",
            "tools/windows-installer/languages/",
        )

        for ignored_path in ignored_paths:
            with self.subTest(ignored_path=ignored_path):
                self.assertIn(ignored_path, ignore_source)

        for relative_path in (
            "upstream-sync-report.md",
            "upstream-sync-report.json",
            "upstream-sync-metadata.json",
            "localization-coverage.json",
            "localization-coverage.md",
            "tools/windows-installer/languages/ChineseSimplified.isl",
            ".github/workflows/upstream-compat-audit-temporary.yml",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertFalse((REPOSITORY_ROOT / relative_path).exists())


class LocalizationWorkflowMaintenanceTests(unittest.TestCase):
    def test_localization_workflow_covers_maintenance_files(self):
        source = (
            REPOSITORY_ROOT / ".github" / "workflows" / "i18n.yml"
        ).read_text(encoding="utf-8")

        for marker in (
            "README.zh-CN.md",
            "docs/zh-CN/**",
            "tools/localization_coverage.py",
            "tools/localization-allowlist.json",
            "tests/test_localization_coverage.py",
            ".github/workflows/localization-coverage.yml",
            "tools/upstream_sync_report.py",
            "tests/test_upstream_sync_report.py",
            "tests/test_localization_maintenance.py",
            "Run localization maintenance tests",
            "cancel-in-progress: true",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        self.assertIn("python -m unittest discover -s tests -t . -v", source)


if __name__ == "__main__":
    unittest.main()
