#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_release_set import (
    ReleaseSetError,
    expected_filenames,
    validate_release_set,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEST_VERSION = "3.10.0"
TEST_COMMIT = "1" * 40


class LocalizedReleaseSetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.artifact_names = sorted(
            expected_filenames(TEST_VERSION) - {"release-manifest.json"}
        )
        artifacts = []
        for index, filename in enumerate(self.artifact_names):
            path = self.root / filename
            path.write_bytes(f"artifact-{index}".encode("utf-8"))
            artifacts.append(
                {
                    "kind": f"kind-{index}",
                    "filename": filename,
                    "platform": "windows" if "windows" in filename else "linux",
                    "python_version": "3.13.0",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size_bytes": path.stat().st_size,
                }
            )
        manifest = {
            "schema_version": 1,
            "project": "turing-system-monitor",
            "version": TEST_VERSION,
            "commit": TEST_COMMIT,
            "artifacts": artifacts,
            "catalogs": {},
            "theme": {},
        }
        self.manifest_path = self.root / "release-manifest.json"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _read_manifest(self):
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_complete_release_set_is_accepted(self):
        manifest = validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)
        self.assertEqual(TEST_VERSION, manifest["version"])
        self.assertEqual(5, len(manifest["artifacts"]))

    def test_tampered_artifact_is_rejected(self):
        (self.root / self.artifact_names[0]).write_bytes(b"tampered")
        with self.assertRaisesRegex(ReleaseSetError, "mismatch"):
            validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)

    def test_missing_or_extra_files_are_rejected(self):
        (self.root / self.artifact_names[0]).unlink()
        with self.assertRaisesRegex(ReleaseSetError, "missing"):
            validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)

        (self.root / self.artifact_names[0]).write_bytes(b"restored")
        (self.root / "unexpected.log").write_text("no", encoding="utf-8")
        with self.assertRaisesRegex(ReleaseSetError, "unexpected"):
            validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)

    def test_manifest_version_and_commit_must_match_request(self):
        manifest = self._read_manifest()
        manifest["version"] = "3.10.1"
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ReleaseSetError, "version mismatch"):
            validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)

        manifest["version"] = TEST_VERSION
        manifest["commit"] = "2" * 40
        self._write_manifest(manifest)
        with self.assertRaisesRegex(ReleaseSetError, "commit mismatch"):
            validate_release_set(self.root, TEST_VERSION, TEST_COMMIT)


class LocalizedReleaseWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (
            REPOSITORY_ROOT / ".github/workflows/publish-localized-release.yml"
        ).read_text(encoding="utf-8")

    def test_workflow_is_manual_and_has_minimal_required_permissions(self):
        trigger = self.source.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("\n  push:", trigger)
        self.assertNotIn("\n  pull_request:", trigger)
        self.assertIn("actions: read", self.source)
        self.assertIn("contents: write", self.source)
        self.assertNotIn("actions: write", self.source)

    def test_workflow_publishes_only_a_successful_main_rc_run(self):
        for marker in (
            'expected_name="Release candidate dry run"',
            'expected_event="workflow_dispatch"',
            'expected_conclusion="success"',
            'expected_branch="main"',
            "git merge-base --is-ancestor",
            "actions/download-artifact@v5",
            "github-token: ${{ github.token }}",
            "run-id: ${{ inputs.run_id }}",
            "python tools/validate_release_set.py",
            "gh release create",
            '--target "$RC_SHA"',
            "--latest",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)

    def test_workflow_uses_workflow_identity_not_dynamic_run_name(self):
        for marker in (
            'run_workflow_id="$(jq -r \'.workflow_id\'',
            "actions/workflows/release-candidate.yml",
            'expected_workflow_id="$(jq -r \'.id\'',
            'expected_workflow_name="$(jq -r \'.name\'',
            '[[ "$run_workflow_id" == "$expected_workflow_id" ]]',
            '[[ "$expected_workflow_name" == "$expected_name" ]]',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.source)
        self.assertNotIn('run_name="$(jq -r \'.name\'', self.source)
        self.assertNotIn('[[ "$run_name" == "$expected_name" ]]', self.source)

    def test_workflow_normalizes_api_path_ref_suffix(self):
        self.assertIn("run_path=\"$(jq -r '.path // \"\"'", self.source)
        self.assertIn('run_workflow_path="${run_path%%@*}"', self.source)
        self.assertIn(
            '[[ "$run_workflow_path" == "$expected_path" ]]',
            self.source,
        )
        self.assertNotIn('[[ "$run_path" == "$expected_path" ]]', self.source)

    def test_workflow_does_not_rebuild_or_publish_upstream_tag(self):
        for forbidden in (
            "pyinstaller",
            "choco install",
            "ISCC.exe",
            "refs/tags/3.10.0\"",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)
        self.assertIn("-zh-cn.", self.source)


if __name__ == "__main__":
    unittest.main()
