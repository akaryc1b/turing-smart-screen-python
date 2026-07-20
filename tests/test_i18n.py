#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from library.i18n import (
    DEFAULT_LOCALE,
    Translator,
    normalize_locale,
    resolve_locale,
)


REAL_LOCALES_DIR = Path(__file__).resolve().parents[1] / "locales"


def flatten_keys(values, prefix=""):
    keys = set()
    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(flatten_keys(value, full_key))
        else:
            keys.add(full_key)
    return keys


class NormalizeLocaleTests(unittest.TestCase):
    def test_normalizes_simplified_chinese_aliases(self):
        for value in ("zh", "zh-CN", "zh_CN.UTF-8", "zh-Hans", "Chinese"):
            with self.subTest(value=value):
                self.assertEqual("zh_CN", normalize_locale(value))

    def test_normalizes_english_aliases(self):
        for value in ("en", "en-US", "en_US.UTF-8", "English"):
            with self.subTest(value=value):
                self.assertEqual("en_US", normalize_locale(value))

    def test_auto_and_unknown_values_are_not_persisted(self):
        self.assertIsNone(normalize_locale("auto"))
        self.assertIsNone(normalize_locale("fr_FR"))


class ResolveLocaleTests(unittest.TestCase):
    def test_explicit_language_has_priority(self):
        environ = {"TURING_LANGUAGE": "en_US", "LANG": "en_US.UTF-8"}
        self.assertEqual("zh_CN", resolve_locale("zh_CN", environ=environ))

    def test_turing_language_environment_override(self):
        environ = {"TURING_LANGUAGE": "zh-CN", "LANG": "en_US.UTF-8"}
        self.assertEqual("zh_CN", resolve_locale("auto", environ=environ))

    def test_language_environment_fallback(self):
        self.assertEqual("zh_CN", resolve_locale("auto", environ={"LANG": "zh_CN.UTF-8"}))

    @patch("library.i18n.system_locale.getlocale", return_value=(None, None))
    def test_english_is_the_final_fallback(self, _mock_getlocale):
        self.assertEqual(DEFAULT_LOCALE, resolve_locale("auto", environ={}))


class TranslatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.locales_dir = Path(self.temp_dir.name)
        self._write_catalog(
            "en_US",
            {
                "common": {"save": "Save"},
                "message": {"welcome": "Welcome, {name}!"},
                "fallback": "English fallback",
            },
        )
        self._write_catalog(
            "zh_CN",
            {
                "common": {"save": "保存"},
                "message": {"welcome": "欢迎，{name}！"},
            },
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_catalog(self, locale_code, content):
        path = self.locales_dir / f"{locale_code}.json"
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    def test_translates_nested_keys(self):
        translator = Translator("zh_CN", locales_dir=self.locales_dir)
        self.assertEqual("保存", translator("common.save"))

    def test_formats_named_placeholders(self):
        translator = Translator("zh_CN", locales_dir=self.locales_dir)
        self.assertEqual("欢迎，测试用户！", translator("message.welcome", name="测试用户"))

    def test_missing_chinese_value_falls_back_to_english(self):
        translator = Translator("zh_CN", locales_dir=self.locales_dir)
        self.assertEqual("English fallback", translator("fallback"))

    def test_missing_key_returns_key_or_explicit_default(self):
        translator = Translator("en_US", locales_dir=self.locales_dir)
        self.assertEqual("missing.key", translator("missing.key"))
        self.assertEqual("Default text", translator("missing.key", default="Default text"))

    def test_environment_can_select_chinese(self):
        translator = Translator(
            "auto",
            locales_dir=self.locales_dir,
            environ={"TURING_LANGUAGE": "zh_CN"},
        )
        self.assertEqual("zh_CN", translator.locale)
        self.assertEqual("保存", translator("common.save"))

    def test_invalid_format_arguments_do_not_crash_the_ui(self):
        translator = Translator("en_US", locales_dir=self.locales_dir)
        self.assertEqual("Welcome, {name}!", translator("message.welcome", unexpected="value"))


class RealCatalogTests(unittest.TestCase):
    def load_catalog(self, locale_code):
        path = REAL_LOCALES_DIR / f"{locale_code}.json"
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)

    def test_chinese_catalog_covers_every_english_key(self):
        english_keys = flatten_keys(self.load_catalog("en_US"))
        chinese_keys = flatten_keys(self.load_catalog("zh_CN"))
        self.assertEqual(english_keys, chinese_keys)

    def test_configurator_core_labels_are_translated(self):
        translator = Translator("zh_CN", locales_dir=REAL_LOCALES_DIR)
        self.assertEqual("显示屏配置", translator("config.display_section"))
        self.assertEqual("硬件监控方式", translator("config.hardware_monitoring"))
        self.assertEqual("天气与 Ping 配置", translator("weather.window_title"))
        self.assertEqual("简体中文", translator("language.chinese_simplified"))

    def test_real_catalog_named_placeholders_render(self):
        translator = Translator("zh_CN", locales_dir=REAL_LOCALES_DIR)
        self.assertEqual("作者：@tester", translator("config.author", name="@tester"))
        self.assertIn("401", translator("weather.error_http", status=401))


if __name__ == "__main__":
    unittest.main()
