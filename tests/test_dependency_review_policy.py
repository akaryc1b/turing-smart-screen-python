#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "dependency-review.yml"
)
GUIDE = REPOSITORY_ROOT / "docs" / "zh-CN" / "dependency-review.md"


class DependencyReviewWorkflowPolicyTests(unittest.TestCase):
    def test_dependency_review_action_remains_enforced(self):
        source = WORKFLOW.read_text(encoding="utf-8")

        for marker in (
            "on: [pull_request]",
            "contents: read",
            "actions/dependency-review-action@v5",
            "cancel-in-progress: true",
            "timeout-minutes: 10",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        for forbidden in (
            "continue-on-error:",
            "paths-ignore:",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        self.assertIsNone(
            re.search(r"warn-only:\s*['\"]?true", source, re.IGNORECASE)
        )
        self.assertIsNone(
            re.search(
                r"if:\s*(?:false|\$\{\{\s*false\s*\}\})",
                source,
                re.IGNORECASE,
            )
        )

    def test_fork_limitation_evidence_and_manual_boundary_are_documented(self):
        source = GUIDE.read_text(encoding="utf-8")

        for marker in (
            "29678127959",
            "88169245045",
            "29676836107",
            "88165649248",
            "actions/dependency-review-action@v5",
            "a1d282b36b6f3519aa1f3fc636f609c47dddb294",
            "Dependency review is not supported on this repository",
            "used against a fork",
            "Settings → General → Danger Zone → Leave fork network",
            "Settings → Security → Advanced Security",
            "不能通过工作流代码修复",
            "不得",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
