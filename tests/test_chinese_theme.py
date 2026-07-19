#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import unittest
from pathlib import Path

import yaml
from PIL import Image


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
THEME_DIR = REPOSITORY_ROOT / "res" / "themes" / "3.5inchTheme2-zh-CN"
THEME_PATH = THEME_DIR / "theme.yaml"
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
FONT_BINARY_SUFFIXES = {".ttf", ".ttc", ".otf", ".otc", ".woff", ".woff2"}


def iter_positioned_entries(value, path="theme"):
    if isinstance(value, dict):
        if "X" in value and "Y" in value:
            yield path, value
        for key, nested in value.items():
            yield from iter_positioned_entries(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            yield from iter_positioned_entries(nested, f"{path}[{index}]")


class ChineseThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.theme = yaml.safe_load(THEME_PATH.read_text(encoding="utf-8"))
        cls.width = 320
        cls.height = 480

    def assert_valid_theme_png(self, filename):
        path = THEME_DIR / filename
        self.assertTrue(path.is_file(), f"Missing theme image: {filename}")
        self.assertGreater(
            path.stat().st_size,
            1000,
            f"Theme image is unexpectedly small: {filename}",
        )
        with Image.open(path) as image:
            self.assertEqual("PNG", image.format, filename)
            self.assertEqual((self.width, self.height), image.size, filename)
            image.verify()
        with Image.open(path) as image:
            image.load()

    def test_theme_is_independent_and_targets_35_inch_portrait(self):
        self.assertEqual('3.5"', self.theme["display"]["DISPLAY_SIZE"])
        self.assertEqual("portrait", self.theme["display"]["DISPLAY_ORIENTATION"])
        self.assertTrue((THEME_DIR.parent / "3.5inchTheme2" / "theme.yaml").is_file())

    def test_background_is_valid_320_by_480_png(self):
        self.assert_valid_theme_png("background.png")

    def test_preview_is_valid_320_by_480_png(self):
        self.assert_valid_theme_png("preview.png")

    def test_static_image_files_exist(self):
        for name, image_data in self.theme.get("static_images", {}).items():
            with self.subTest(image=name):
                self.assertTrue((THEME_DIR / image_data["PATH"]).is_file())

    def test_all_explicit_rectangles_stay_inside_display(self):
        violations = []
        for path, entry in iter_positioned_entries(self.theme):
            x = entry["X"]
            y = entry["Y"]
            width = entry.get("WIDTH", 0)
            height = entry.get("HEIGHT", 0)
            if x < 0 or y < 0 or x > self.width or y > self.height:
                violations.append(f"{path}: origin ({x}, {y})")
            if width < 0 or x + width > self.width:
                violations.append(f"{path}: horizontal extent {x + width}")
            if height < 0 or y + height > self.height:
                violations.append(f"{path}: vertical extent {y + height}")
        self.assertEqual([], violations)

    def test_chinese_static_labels_use_system_cjk_aliases(self):
        labels = self.theme["static_text"]
        chinese_labels = {
            name: data
            for name, data in labels.items()
            if CJK_PATTERN.search(str(data.get("TEXT", "")))
        }
        self.assertGreaterEqual(len(chinese_labels), 10)
        for name, data in chinese_labels.items():
            with self.subTest(label=name):
                self.assertIn(data.get("FONT"), {"system:cjk", "system:cjk-bold"})

    def test_required_chinese_labels_are_present(self):
        texts = {
            data.get("TEXT")
            for data in self.theme.get("static_text", {}).values()
        }
        required = {
            "日期",
            "温度",
            "内存",
            "磁盘",
            "网络",
            "上传",
            "下载",
            "运行时间",
        }
        self.assertEqual(set(), required - texts)

    def test_common_metric_abbreviations_remain_stable(self):
        texts = {
            data.get("TEXT")
            for data in self.theme.get("static_text", {}).values()
        }
        self.assertTrue({"CPU", "GPU", "FPS"}.issubset(texts))

    def test_theme_does_not_vendor_font_binaries(self):
        font_files = [
            path.relative_to(THEME_DIR)
            for path in THEME_DIR.rglob("*")
            if path.is_file() and path.suffix.lower() in FONT_BINARY_SUFFIXES
        ]
        self.assertEqual([], font_files)


if __name__ == "__main__":
    unittest.main()
