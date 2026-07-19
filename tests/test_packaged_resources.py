#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from library import resources
from library.i18n import Translator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ResourcePathTests(unittest.TestCase):
    def test_source_mode_uses_repository_root(self):
        with patch.object(resources.sys, "_MEIPASS", None, create=True):
            self.assertEqual(REPOSITORY_ROOT, resources.application_root())
            self.assertEqual(
                REPOSITORY_ROOT / "locales" / "zh_CN.json",
                resources.resource_path("locales", "zh_CN.json"),
            )

    def test_frozen_mode_uses_pyinstaller_extraction_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            frozen_root = Path(temp_dir)
            with patch.object(resources.sys, "_MEIPASS", str(frozen_root), create=True):
                self.assertEqual(frozen_root.resolve(), resources.application_root())
                self.assertEqual(
                    frozen_root.resolve() / "locales" / "en_US.json",
                    resources.resource_path("locales", "en_US.json"),
                )


class PackagedCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bundle_root = Path(self.temp_dir.name)
        self.locales_dir = self.bundle_root / "locales"
        self.locales_dir.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_catalog(self, locale_code, content):
        path = self.locales_dir / f"{locale_code}.json"
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    def test_chinese_catalog_loads_from_frozen_bundle(self):
        self._write_catalog("en_US", {"message": "English"})
        self._write_catalog("zh_CN", {"message": "中文"})

        with patch.object(resources.sys, "_MEIPASS", str(self.bundle_root), create=True):
            translator = Translator("zh_CN")

        self.assertEqual("中文", translator("message"))

    def test_missing_chinese_catalog_falls_back_to_packaged_english(self):
        self._write_catalog("en_US", {"message": "English fallback"})

        with patch.object(resources.sys, "_MEIPASS", str(self.bundle_root), create=True):
            translator = Translator("zh_CN")

        self.assertEqual("English fallback", translator("message"))

    def test_missing_catalogs_do_not_crash_translation(self):
        with patch.object(resources.sys, "_MEIPASS", str(self.bundle_root), create=True):
            translator = Translator("zh_CN")

        self.assertEqual("missing.key", translator("missing.key"))
        self.assertEqual("Readable fallback", translator("missing.key", default="Readable fallback"))


class PyInstallerSpecTests(unittest.TestCase):
    def test_every_bundle_spec_includes_locale_catalogs(self):
        for filename in ("turing-system-monitor.spec", "turing-system-monitor-debug.spec"):
            with self.subTest(filename=filename):
                source = (REPOSITORY_ROOT / filename).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=filename)
                common_datas = None
                for node in tree.body:
                    if isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == "COMMON_DATAS"
                        for target in node.targets
                    ):
                        common_datas = ast.literal_eval(node.value)
                        break

                self.assertIsNotNone(common_datas, "COMMON_DATAS must be declared")
                self.assertIn(("locales", "locales"), common_datas)


if __name__ == "__main__":
    unittest.main()
