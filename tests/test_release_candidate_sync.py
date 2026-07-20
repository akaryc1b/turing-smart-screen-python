#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github/workflows/release-candidate.yml"
UPSTREAM_RELEASE_PATH = REPOSITORY_ROOT / "tools/upstream-release.json"


class ReleaseCandidateUpstreamSyncTests(unittest.TestCase):
    def test_upstream_release_metadata_matches_localized_mainline(self):
        metadata = json.loads(UPSTREAM_RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            metadata,
            {
                "repository": "mathoudebine/turing-smart-screen-python",
                "version": "3.10.0",
                "tag": "3.10.0",
                "commit": "cf0f1dbe14f9c71e0b3050bf9505eef6145234ae",
            },
        )
        self.assertRegex(metadata["version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(metadata["commit"], r"^[0-9a-f]{40}$")

    def test_workflow_uses_upstream_version_without_manual_override(self):
        source = WORKFLOW_PATH.read_text(encoding="utf-8")
        trigger = source.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("inputs:", trigger)
        self.assertNotIn("default: 0.0.0", source)
        self.assertIn("RC_VERSION: 3.10.0", source)
        self.assertIn("tools/upstream-release.json", source)
        self.assertNotIn("inputs.version", source)

    def test_windows_jobs_disable_line_ending_conversion_before_checkout(self):
        source = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("- name: Disable Windows line-ending conversion"),
            2,
        )
        for job_name in ("windows-release", "windows-debug"):
            with self.subTest(job_name=job_name):
                block = source.split(f"  {job_name}:\n", 1)[1]
                normalize_at = block.index(
                    "- name: Disable Windows line-ending conversion"
                )
                checkout_at = block.index("- name: Check out repository")
                self.assertLess(normalize_at, checkout_at)
                self.assertIn("git config --global core.autocrlf false", block)

    def test_all_candidate_names_use_synchronized_environment_version(self):
        source = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertNotRegex(source, re.compile(r"\$\{\{\s*inputs\.version\s*\}\}"))
        for marker in (
            "rc-windows-release-${{ env.RC_VERSION }}",
            "rc-windows-debug-${{ env.RC_VERSION }}",
            "rc-linux-release-${{ env.RC_VERSION }}",
            "turing-system-monitor-${{ env.RC_VERSION }}-release-candidate",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
