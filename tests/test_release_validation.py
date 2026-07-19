#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_release_bundle import BundleValidationError, validate_bundle


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ReleaseBundleValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bundle_root = Path(self.temp_dir.name) / "turing-system-monitor"
        self.bundle_root.mkdir()

        shutil.copytree(
            REPOSITORY_ROOT / "locales",
            self.bundle_root / "locales",
        )
        shutil.copytree(
            REPOSITORY_ROOT / "res" / "themes" / "3.5inchTheme2-zh-CN",
            self.bundle_root / "res" / "themes" / "3.5inchTheme2-zh-CN",
        )

        fallback_font = (
            self.bundle_root
            / "res"
            / "fonts"
            / "roboto-mono"
            / "RobotoMono-Regular.ttf"
        )
        fallback_font.parent.mkdir(parents=True)
        fallback_font.write_bytes(b"packaged fallback font")

        (self.bundle_root / "config.yaml").write_text("config: {}\n", encoding="utf-8")
        (self.bundle_root / "external").mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _add_windows_executables(self):
        for filename in ("configure.exe", "main.exe", "theme-editor.exe"):
            (self.bundle_root / filename).write_bytes(b"test executable")

    def _add_linux_executables(self):
        for filename in ("configure", "main", "theme-editor"):
            executable = self.bundle_root / filename
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o755)
        (self.bundle_root / "turing-smart-screen").symlink_to("configure")

    def test_windows_release_bundle_is_accepted(self):
        self._add_windows_executables()
        validate_bundle(self.bundle_root, "windows")

    def test_linux_release_bundle_is_accepted(self):
        self._add_linux_executables()
        validate_bundle(self.bundle_root, "linux")

    def test_missing_chinese_catalog_is_rejected(self):
        self._add_windows_executables()
        (self.bundle_root / "locales" / "zh_CN.json").unlink()

        with self.assertRaisesRegex(BundleValidationError, "zh_CN.json"):
            validate_bundle(self.bundle_root, "windows")

    def test_missing_chinese_theme_asset_is_rejected(self):
        self._add_windows_executables()
        (
            self.bundle_root
            / "res"
            / "themes"
            / "3.5inchTheme2-zh-CN"
            / "preview.png"
        ).unlink()

        with self.assertRaisesRegex(BundleValidationError, "preview.png"):
            validate_bundle(self.bundle_root, "windows")

    def test_missing_bundled_font_fallback_is_rejected(self):
        self._add_windows_executables()
        (
            self.bundle_root
            / "res"
            / "fonts"
            / "roboto-mono"
            / "RobotoMono-Regular.ttf"
        ).unlink()

        with self.assertRaisesRegex(BundleValidationError, "fallback font"):
            validate_bundle(self.bundle_root, "windows")


class ReleaseWorkflowIntegrationTests(unittest.TestCase):
    def test_release_workflows_validate_generated_bundles_before_archiving(self):
        workflows = {
            ".github/workflows/generate-windows-packages.yml": (
                "--platform windows",
                "Create portable zip archive",
            ),
            ".github/workflows/generate-windows-packages-debug.yml": (
                "--platform windows",
                "Create portable zip archive",
            ),
            ".github/workflows/generate-linux-packages.yml": (
                "--platform linux",
                "Create archive from generated binaries",
            ),
        }

        for filename, (platform_argument, archive_marker) in workflows.items():
            with self.subTest(filename=filename):
                source = (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
                validator = "tools/validate_release_bundle.py"
                self.assertIn(validator, source)
                self.assertIn(platform_argument, source)
                self.assertLess(source.index("pyinstaller"), source.index(validator))
                self.assertLess(source.index(validator), source.index(archive_marker))

    def test_pull_request_validation_builds_release_debug_and_linux_bundles(self):
        path = REPOSITORY_ROOT / ".github/workflows/release-bundle-validation.yml"
        source = path.read_text(encoding="utf-8")

        self.assertIn("turing-system-monitor.spec", source)
        self.assertIn("turing-system-monitor-debug.spec", source)
        self.assertIn("windows-latest", source)
        self.assertIn("ubuntu-latest", source)
        self.assertIn("validate_release_bundle.py", source)
        self.assertIn("Inno-Setup-Action", source)
        self.assertIn("cancel-in-progress: true", source)

    def test_windows_installer_offers_simplified_chinese(self):
        path = REPOSITORY_ROOT / "tools/windows-installer/turing-system-monitor.iss"
        source = path.read_text(encoding="utf-8")

        self.assertIn('Name: "chinesesimplified"', source)
        self.assertIn("ChineseSimplified.isl", source)
        self.assertIn("chinesesimplified.PawnIOPageTitle", source)
        self.assertIn("{cm:PawnIOPageTitle}", source)
        self.assertNotIn("PagePawnIO := CreateCustomPage(\n    wpInstalling,\n    'Install", source)

    def test_chinese_installation_guide_documents_packaged_language_override(self):
        path = REPOSITORY_ROOT / "docs/zh-CN/installation.md"
        source = path.read_text(encoding="utf-8")

        self.assertIn("TURING_LANGUAGE", source)
        self.assertIn("portable", source.lower())
        self.assertIn("locales/zh_CN.json", source)
        self.assertIn("3.5inchTheme2-zh-CN", source)


if __name__ == "__main__":
    unittest.main()
