#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = REPOSITORY_ROOT / ".github" / "workflows"

FORBIDDEN_DIRECTORIES = {
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "frozen-smoke-artifacts",
}
FORBIDDEN_ROOT_PATHS = {
    Path("release-manifest.json"),
    Path("localization-coverage.json"),
    Path("localization-coverage.md"),
    Path("upstream-sync-report.md"),
    Path("upstream-sync-report.json"),
    Path("upstream-sync-metadata.json"),
}
FORBIDDEN_SUFFIXES = (".exe", ".zip", ".tar.gz", ".log", ".isl")
TEMPORARY_WORKFLOW_MARKERS = (
    "temporary",
    "diagnostic",
    "bootstrap",
    "stage14",
    "stage15-apply",
    "stale-run",
    "cleanup",
)
WRITE_PERMISSION_ALLOWLIST = {
    "codeql.yml": {"security-events"},
    "generate-linux-packages.yml": {"contents"},
    "generate-windows-packages.yml": {"contents"},
    "generate-windows-packages-debug.yml": {"contents"},
    "themes-screenshot-on-push.yml": {"contents"},
}


def tracked_files() -> list[Path]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return sorted(
            path.relative_to(REPOSITORY_ROOT)
            for path in REPOSITORY_ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and not ({part.lower() for part in path.parts} & FORBIDDEN_DIRECTORIES)
        )

    return [
        Path(raw.decode("utf-8"))
        for raw in completed.stdout.split(b"\0")
        if raw
    ]


def workflow_sources() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(WORKFLOWS_DIR.glob("*.yml"))
    }


def upload_blocks(source: str) -> list[str]:
    blocks = []
    marker = "uses: actions/upload-artifact@v7"
    for tail in source.split(marker)[1:]:
        blocks.append(tail.split("\n      - name:", 1)[0])
    return blocks


UPSTREAM_TRACKED_BINARY_EXCEPTIONS = {
    "external/PawnIO/PawnIO_setup.exe",
}


class RepositoryArtifactHygieneTests(unittest.TestCase):
    def test_generated_outputs_and_temporary_workflows_are_not_tracked(self):
        violations = []
        for path in tracked_files():
            path_text = path.as_posix()
            # Required upstream release input, not a generated output.
            if path_text in UPSTREAM_TRACKED_BINARY_EXCEPTIONS:
                continue
            lowered_parts = {part.lower() for part in path.parts}
            lowered_name = path.name.lower()

            if lowered_parts & FORBIDDEN_DIRECTORIES:
                violations.append(path_text)
                continue
            if path in FORBIDDEN_ROOT_PATHS or path.name == "ChineseSimplified.isl":
                violations.append(path_text)
                continue
            if lowered_name.endswith(FORBIDDEN_SUFFIXES):
                violations.append(path_text)
                continue
            if path.parts[:2] == (".github", "workflows"):
                if any(marker in lowered_name for marker in TEMPORARY_WORKFLOW_MARKERS):
                    violations.append(path_text)

        self.assertEqual([], violations, "Generated or temporary files are tracked")

    def test_font_binaries_remain_confined_to_upstream_font_resources(self):
        violations = []
        for path in tracked_files():
            if path.suffix.lower() not in {".ttf", ".ttc", ".otf", ".otc"}:
                continue
            if path.parts[:2] != ("res", "fonts"):
                violations.append(path.as_posix())

        self.assertEqual([], violations, "Unexpected font binary location")


class WorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = workflow_sources()

    def test_every_workflow_has_explicit_permissions_concurrency_and_timeouts(self):
        failures = []
        for name, source in self.sources.items():
            with self.subTest(workflow=name):
                if "permissions:" not in source:
                    failures.append(f"{name}: permissions")
                if "concurrency:" not in source:
                    failures.append(f"{name}: concurrency")

                data = yaml.safe_load(source)
                jobs = data.get("jobs", {})
                for job_name, job in jobs.items():
                    if "timeout-minutes" not in job:
                        failures.append(f"{name}:{job_name}: timeout")

        self.assertEqual([], failures, "Workflow policy fields are missing")

    def test_write_permissions_are_limited_to_required_release_or_security_jobs(self):
        failures = []
        permission_line = re.compile(r"^\s*([a-z-]+):\s*write\s*$", re.MULTILINE)
        for name, source in self.sources.items():
            granted = set(permission_line.findall(source))
            allowed = WRITE_PERMISSION_ALLOWLIST.get(name, set())
            unexpected = granted - allowed
            if unexpected:
                failures.append(f"{name}: {sorted(unexpected)}")
            if "write-all" in source:
                failures.append(f"{name}: write-all")
            if "actions: write" in source:
                failures.append(f"{name}: actions: write")

        self.assertEqual([], failures, "Unexpected workflow write permission")

    def test_workflows_do_not_weaken_failures_or_upload_logs(self):
        forbidden_markers = (
            "continue-on-error",
            "warn-only: true",
            "paths-ignore:",
            "if: false",
        )
        failures = []
        for name, source in self.sources.items():
            for marker in forbidden_markers:
                if marker in source:
                    failures.append(f"{name}: {marker}")
            for block in upload_blocks(source):
                if ".log" in block or "output.log" in block or "error.log" in block:
                    failures.append(f"{name}: log artifact")

        self.assertEqual([], failures, "Workflow failure policy was weakened")

    def test_dependency_review_policy_remains_strict(self):
        source = self.sources["dependency-review.yml"]
        self.assertIn("actions/dependency-review-action@v5", source)
        self.assertIn("contents: read", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("continue-on-error", source)
        self.assertNotIn("warn-only", source)
        self.assertNotIn("paths-ignore", source)

    def test_release_candidate_remains_manual_and_does_not_publish_releases(self):
        source = self.sources["release-candidate.yml"]
        trigger = source.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("\n  push:", trigger)
        self.assertNotIn("\n  pull_request:", trigger)
        self.assertNotIn("\n  release:", trigger)

        for marker in (
            "gh release create",
            "actions/create-release",
            "softprops/action-gh-release",
            "upload-release-asset",
        ):
            self.assertNotIn(marker, source)

    def test_release_validation_does_not_create_a_github_release(self):
        source = self.sources["release-bundle-validation.yml"]
        for marker in (
            "gh release create",
            "actions/create-release",
            "softprops/action-gh-release",
            "upload-release-asset",
        ):
            self.assertNotIn(marker, source)
        self.assertNotIn("inno-setup.log", source)
        self.assertNotIn("Archive failed installer compiler log", source)

    def test_frozen_smoke_artifacts_are_evidence_only(self):
        source = self.sources["frozen-smoke.yml"]
        blocks = upload_blocks(source)
        self.assertEqual(2, len(blocks))
        for block in blocks:
            self.assertIn("frozen-smoke.png", block)
            self.assertIn("frozen-smoke-report.json", block)
            for forbidden in ("dist/", "build/", ".exe", ".log"):
                self.assertNotIn(forbidden, block)

    def test_localization_coverage_uploads_only_reports(self):
        source = self.sources["localization-coverage.yml"]
        blocks = upload_blocks(source)
        self.assertEqual(1, len(blocks))
        block = blocks[0]
        self.assertIn("localization-coverage.json", block)
        self.assertIn("localization-coverage.md", block)
        for forbidden in ("dist/", "build/", ".exe", ".log", "locales/"):
            self.assertNotIn(forbidden, block)


class FinalMaintenanceDocumentationTests(unittest.TestCase):
    def test_final_branch_chain_and_stable_values_are_documented(self):
        guide = (REPOSITORY_ROOT / "docs" / "zh-CN" / "final-maintenance.md").read_text(
            encoding="utf-8"
        )
        upstream = (REPOSITORY_ROOT / "docs" / "zh-CN" / "upstream-sync.md").read_text(
            encoding="utf-8"
        )
        for branch in (
            "agent/zh-cn-release-candidate",
            "agent/zh-cn-frozen-smoke",
            "agent/zh-cn-coverage-audit",
            "agent/zh-cn-final-maintenance",
        ):
            with self.subTest(branch=branch):
                self.assertIn(branch, guide)
                self.assertIn(branch, upstream)

        for value in ("AUTO", "STATIC", "SIMU", "TUR_USB", "metric"):
            with self.subTest(value=value):
                self.assertIn(value, guide)

    def test_final_maintenance_guide_is_in_both_indexes(self):
        root_index = (REPOSITORY_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        docs_index = (REPOSITORY_ROOT / "docs" / "zh-CN" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("docs/zh-CN/final-maintenance.md", root_index)
        self.assertIn("(final-maintenance.md)", docs_index)
        self.assertIn("docs/zh-CN/localization-coverage.md", root_index)
        self.assertIn("(localization-coverage.md)", docs_index)


if __name__ == "__main__":
    unittest.main()
