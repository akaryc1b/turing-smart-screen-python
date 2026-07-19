#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.upstream_sync_report import (
    ChangedPath,
    build_report,
    classify_path,
    main,
    parse_name_status,
    render_json,
    render_markdown,
)


class UpstreamSyncReportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = Path(self.temp_dir.name) / "repository"
        self.repository.mkdir()
        self._git("init")
        self._git("config", "user.name", "Test Maintainer")
        self._git("config", "user.email", "maintainer@example.com")

        self._write("main.py", "print('base')\n")
        self._write("README.md", "base documentation\n")
        self._write("locales/en_US.json", '{"app": {"title": "Base"}}\n')
        self._git("add", ".")
        self._git("commit", "-m", "base")
        self.base_sha = self._git("rev-parse", "HEAD")

        self._git("branch", "upstream-main")
        self._git("branch", "local-feature")

        self._git("switch", "upstream-main")
        self._write("main.py", "print('upstream lifecycle change')\n")
        self._write("README.md", "upstream documentation\n")
        self._write("library/new_runtime.py", "UPSTREAM = True\n")
        self._git("add", ".")
        self._git("commit", "-m", "upstream changes")

        self._git("switch", "local-feature")
        self._write("main.py", "print('localized user message')\n")
        self._write("locales/zh_CN.json", '{"app": {"title": "配置"}}\n')
        self._write("docs/zh-CN/contributing.md", "# 贡献\n")
        self._git("add", ".")
        self._git("commit", "-m", "localization changes")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _git(self, *arguments):
        completed = subprocess.run(
            ["git", "-C", str(self.repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()

    def _write(self, relative_path, content):
        path = self.repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_report_detects_only_paths_changed_on_both_sides(self):
        report = build_report(
            repository=self.repository,
            upstream_ref="upstream-main",
            local_ref="local-feature",
        )

        self.assertEqual(self.base_sha, report.merge_base)
        self.assertEqual(["main.py"], [overlap.path for overlap in report.overlaps])
        self.assertEqual("runtime-and-ui", report.overlaps[0].category)
        self.assertEqual("high", report.overlaps[0].risk)
        self.assertIn("README.md", {change.path for change in report.upstream_changes})
        self.assertIn(
            "locales/zh_CN.json",
            {change.path for change in report.local_changes},
        )

    def test_explicit_merge_base_is_supported(self):
        report = build_report(
            repository=self.repository,
            upstream_ref="upstream-main",
            local_ref="local-feature",
            merge_base=self.base_sha,
        )

        self.assertEqual(self.base_sha, report.merge_base)
        self.assertEqual(1, len(report.overlaps))

    def test_markdown_and_json_outputs_are_machine_readable(self):
        report = build_report(
            repository=self.repository,
            upstream_ref="upstream-main",
            local_ref="local-feature",
        )

        markdown = render_markdown(report)
        self.assertIn("Paths requiring manual review", markdown)
        self.assertIn("`main.py`", markdown)
        self.assertIn("path overlap, not semantic merge conflicts", markdown)

        data = json.loads(render_json(report))
        self.assertEqual("main.py", data["overlaps"][0]["path"])
        self.assertEqual("high", data["overlaps"][0]["risk"])

    def test_cli_can_write_report_and_fail_on_overlap(self):
        output = Path(self.temp_dir.name) / "sync-report.md"
        status = main(
            [
                "--repository",
                str(self.repository),
                "--upstream-ref",
                "upstream-main",
                "--local-ref",
                "local-feature",
                "--output",
                str(output),
                "--fail-on-overlap",
            ]
        )

        self.assertEqual(2, status)
        self.assertIn("`main.py`", output.read_text(encoding="utf-8"))

    def test_name_status_parser_preserves_renames(self):
        changes = parse_name_status(
            "M\tmain.py\nR098\tdocs/old.md\tdocs/new.md\nA\tlocales/zh_CN.json\n"
        )

        self.assertEqual(
            [
                ChangedPath(status="M", path="main.py"),
                ChangedPath(
                    status="R098",
                    path="docs/new.md",
                    previous_path="docs/old.md",
                ),
                ChangedPath(status="A", path="locales/zh_CN.json"),
            ],
            changes,
        )
        self.assertEqual({"docs/old.md", "docs/new.md"}, changes[1].aliases())

    def test_path_classification_covers_localization_maintenance_areas(self):
        expected = {
            "locales/zh_CN.json": "catalog-and-i18n",
            "library/i18n.py": "catalog-and-i18n",
            "configure.py": "runtime-and-ui",
            "library/fonts.py": "runtime-library",
            "library/resources.py": "packaging-and-release",
            "res/themes/example/theme.yaml": "themes-and-fonts",
            "turing-system-monitor.spec": "packaging-and-release",
            ".github/workflows/i18n.yml": "packaging-and-release",
            "docs/zh-CN/upstream-sync.md": "documentation",
            "tests/test_i18n.py": "tests",
        }

        for path, category in expected.items():
            with self.subTest(path=path):
                self.assertEqual(category, classify_path(path))


if __name__ == "__main__":
    unittest.main()
