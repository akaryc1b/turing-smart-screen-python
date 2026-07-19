#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import shutil
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

import yaml

from tools.build_release_manifest import (
    ARTIFACT_KINDS,
    ReleaseManifestError,
    build_entry,
    combine_metadata,
    validate_version,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TEST_COMMIT = "1" * 40
TEST_VERSION = "1.2.3"


class ReleaseCandidateManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.catalog_dir = self.root / "bundle" / "locales"
        self.theme_dir = (
            self.root
            / "bundle"
            / "res"
            / "themes"
            / "3.5inchTheme2-zh-CN"
        )
        self.catalog_dir.mkdir(parents=True)
        self.theme_dir.mkdir(parents=True)

        (self.catalog_dir / "en_US.json").write_text(
            json.dumps({"app": {"title": "Title"}}),
            encoding="utf-8",
        )
        (self.catalog_dir / "zh_CN.json").write_text(
            json.dumps({"app": {"title": "标题"}}, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.theme_dir / "theme.yaml").write_text(
            yaml.safe_dump(
                {
                    "display": {
                        "DISPLAY_SIZE": '3.5"',
                        "DISPLAY_ORIENTATION": "portrait",
                    },
                    "static_text": {"CPU": {"TEXT": "处理器"}},
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        for filename in ("background.png", "preview.png"):
            (self.theme_dir / filename).write_bytes(b"png")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _required_paths(self, platform_name):
        common = (
            "version.txt",
            "locales/en_US.json",
            "locales/zh_CN.json",
            "res/themes/3.5inchTheme2-zh-CN/theme.yaml",
        )
        if platform_name == "windows":
            return ("configure.exe", "main.exe", "theme-editor.exe", *common)
        return (
            "configure",
            "main",
            "theme-editor",
            "turing-smart-screen",
            *common,
        )

    def _create_archive(self, filename, archive_type, platform_name, extra=()):
        path = self.root / filename
        members = [
            f"turing-system-monitor/{relative_path}"
            for relative_path in self._required_paths(platform_name)
        ]
        members.extend(extra)
        if archive_type == "zip":
            with zipfile.ZipFile(path, "w") as archive:
                for member in members:
                    archive.writestr(member, b"payload")
        else:
            source = self.root / "tar-source"
            shutil.rmtree(source, ignore_errors=True)
            for member in members:
                target = source / member
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"payload")
            with tarfile.open(path, "w:gz") as archive:
                archive.add(source / "turing-system-monitor", arcname="turing-system-monitor")
        return path

    def _build_entry(self, kind):
        contract = ARTIFACT_KINDS[kind]
        filename = contract["filename"].format(version=TEST_VERSION)
        archive_type = contract.get("archive")
        if archive_type:
            artifact = self._create_archive(
                filename,
                archive_type,
                contract["platform"],
            )
        else:
            artifact = self.root / filename
            artifact.write_bytes(b"installer")
        return build_entry(
            artifact=artifact,
            kind=kind,
            version=TEST_VERSION,
            commit=TEST_COMMIT,
            python_version="3.13.5",
            catalog_dir=self.catalog_dir,
            theme_path=self.theme_dir / "theme.yaml",
        )

    def test_numeric_three_part_version_is_required(self):
        self.assertEqual(validate_version(TEST_VERSION), TEST_VERSION)
        for invalid in ("v1.2.3", "1.2", "1.2.3-rc.1", "latest"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ReleaseManifestError):
                    validate_version(invalid)

    def test_valid_windows_portable_archive_records_contract_metadata(self):
        entry = self._build_entry("windows-release-portable")
        artifact = entry["artifact"]
        self.assertEqual(artifact["archive"]["root"], "turing-system-monitor")
        self.assertEqual(artifact["archive"]["format"], "zip")
        self.assertGreater(artifact["size_bytes"], 0)
        self.assertEqual(len(artifact["sha256"]), 64)
        self.assertTrue(entry["catalogs"]["zh_CN"]["contains_cjk"])
        self.assertEqual(entry["theme"]["cjk_label_count"], 1)

    def test_archive_with_forbidden_build_output_is_rejected(self):
        filename = ARTIFACT_KINDS["windows-release-portable"]["filename"].format(
            version=TEST_VERSION
        )
        artifact = self._create_archive(
            filename,
            "zip",
            "windows",
            extra=("turing-system-monitor/__pycache__/module.pyc",),
        )
        with self.assertRaisesRegex(ReleaseManifestError, "Forbidden archive"):
            build_entry(
                artifact=artifact,
                kind="windows-release-portable",
                version=TEST_VERSION,
                commit=TEST_COMMIT,
                python_version="3.13.5",
                catalog_dir=self.catalog_dir,
                theme_path=self.theme_dir / "theme.yaml",
            )

    def test_archive_without_single_project_root_is_rejected(self):
        filename = ARTIFACT_KINDS["windows-release-portable"]["filename"].format(
            version=TEST_VERSION
        )
        artifact = self.root / filename
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("main.exe", b"payload")
        with self.assertRaisesRegex(ReleaseManifestError, "top-level"):
            build_entry(
                artifact=artifact,
                kind="windows-release-portable",
                version=TEST_VERSION,
                commit=TEST_COMMIT,
                python_version="3.13.5",
                catalog_dir=self.catalog_dir,
                theme_path=self.theme_dir / "theme.yaml",
            )

    def test_combined_manifest_requires_all_five_artifact_kinds(self):
        metadata_paths = []
        for index, kind in enumerate(ARTIFACT_KINDS):
            entry = self._build_entry(kind)
            metadata = self.root / f"metadata-{index}.json"
            metadata.write_text(json.dumps(entry), encoding="utf-8")
            metadata_paths.append(metadata)

        manifest = combine_metadata(metadata_paths, self.root)
        self.assertEqual(manifest["version"], TEST_VERSION)
        self.assertEqual(manifest["commit"], TEST_COMMIT)
        self.assertEqual(
            {artifact["kind"] for artifact in manifest["artifacts"]},
            set(ARTIFACT_KINDS),
        )

        with self.assertRaisesRegex(ReleaseManifestError, "Artifact kinds"):
            combine_metadata(metadata_paths[:-1], self.root)

    def test_combined_manifest_rehashes_downloaded_artifacts(self):
        metadata_paths = []
        for index, kind in enumerate(ARTIFACT_KINDS):
            entry = self._build_entry(kind)
            metadata = self.root / f"metadata-{index}.json"
            metadata.write_text(json.dumps(entry), encoding="utf-8")
            metadata_paths.append(metadata)

        first_filename = json.loads(metadata_paths[0].read_text())["artifact"]["filename"]
        (self.root / first_filename).write_bytes(b"tampered")
        with self.assertRaisesRegex(ReleaseManifestError, "mismatch"):
            combine_metadata(metadata_paths, self.root)


class ReleaseCandidateWorkflowPolicyTests(unittest.TestCase):
    def test_workflow_is_manual_read_only_and_never_publishes_a_release(self):
        source = (
            REPOSITORY_ROOT / ".github/workflows/release-candidate.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", source)
        self.assertIn("contents: read", source)
        self.assertIn("cancel-in-progress: true", source)
        self.assertNotIn("contents: write", source)
        self.assertNotIn("gh release", source)
        self.assertNotIn("create-release", source.lower())

        trigger_block = source.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertNotIn("  release:\n", trigger_block)
        self.assertNotIn("  pull_request:\n", trigger_block)
        self.assertNotIn("  push:\n", trigger_block)

    def test_workflow_builds_and_catalogs_all_release_candidate_artifacts(self):
        source = (
            REPOSITORY_ROOT / ".github/workflows/release-candidate.yml"
        ).read_text(encoding="utf-8")
        for marker in (
            "turing-system-monitor.spec",
            "turing-system-monitor-debug.spec",
            "prepare-inno-languages.ps1",
            "ISCC.exe",
            "windows-release-installer",
            "windows-release-portable",
            "windows-debug-installer",
            "windows-debug-portable",
            "linux-release-archive",
            "release-manifest.json",
            "actions/upload-artifact@v7",
            "actions/download-artifact@v5",
            "if-no-files-found: error",
            "retention-days: 14",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_workflow_keeps_diagnostics_and_transient_files_out_of_artifacts(self):
        source = (
            REPOSITORY_ROOT / ".github/workflows/release-candidate.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("--Theme examples", source)
        self.assertNotIn("inno-setup.log", source)
        self.assertNotIn("*.log", source)
        self.assertNotIn("ChineseSimplified.isl\n", source)


if __name__ == "__main__":
    unittest.main()
