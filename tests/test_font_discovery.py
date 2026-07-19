#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from library import config
from library import fonts


class FontDiscoveryTests(unittest.TestCase):
    def setUp(self):
        fonts.clear_font_cache()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.font_root = Path(self.temp_dir.name)

    def tearDown(self):
        fonts.clear_font_cache()
        self.temp_dir.cleanup()

    def _font_file(self, filename):
        path = self.font_root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"mock font")
        return path.resolve()

    def test_windows_prefers_microsoft_yahei_for_regular_text(self):
        simhei = self._font_file("simhei.ttf")
        yahei = self._font_file("msyh.ttc")

        result = fonts.find_cjk_font(
            platform_name="Windows",
            search_roots=[self.font_root],
        )

        self.assertEqual(str(yahei), result)
        self.assertNotEqual(str(simhei), result)

    def test_windows_uses_bold_font_when_requested(self):
        self._font_file("msyh.ttc")
        yahei_bold = self._font_file("msyhbd.ttc")

        result = fonts.find_cjk_font(
            weight="bold",
            platform_name="Windows",
            search_roots=[self.font_root],
        )

        self.assertEqual(str(yahei_bold), result)

    def test_macos_prefers_pingfang(self):
        self._font_file("NotoSansCJK-Regular.ttc")
        pingfang = self._font_file("PingFang.ttc")

        result = fonts.find_cjk_font(
            platform_name="Darwin",
            search_roots=[self.font_root],
        )

        self.assertEqual(str(pingfang), result)

    def test_linux_prefers_noto_sans_cjk_sc(self):
        self._font_file("wqy-microhei.ttc")
        noto = self._font_file("NotoSansCJK-Regular.ttc")

        result = fonts.find_cjk_font(
            platform_name="Linux",
            search_roots=[self.font_root],
        )

        self.assertEqual(str(noto), result)

    def test_directory_scan_is_cached(self):
        noto = self._font_file("NotoSansCJK-Regular.ttc")

        with patch("library.fonts._scan_font_files", wraps=fonts._scan_font_files) as scan:
            first = fonts.find_cjk_font(
                platform_name="Linux",
                search_roots=[self.font_root],
            )
            second = fonts.find_cjk_font(
                platform_name="Linux",
                search_roots=[self.font_root],
            )

        self.assertEqual(str(noto), first)
        self.assertEqual(first, second)
        self.assertEqual(1, scan.call_count)


class ThemeFontResolutionTests(unittest.TestCase):
    def test_relative_theme_font_stays_below_bundled_font_directory(self):
        fonts_dir = Path("/bundle/res/fonts")

        result = fonts.resolve_theme_font(
            "roboto/Roboto-Bold.ttf",
            fonts_dir=fonts_dir,
        )

        self.assertEqual(
            str(fonts_dir / "roboto/Roboto-Bold.ttf"),
            result,
        )

    def test_absolute_font_path_is_preserved(self):
        absolute_path = Path("/opt/fonts/custom-cjk.otf")

        self.assertEqual(
            str(absolute_path),
            fonts.resolve_theme_font(str(absolute_path)),
        )

    def test_regular_and_bold_aliases_request_matching_weight(self):
        with patch("library.fonts.find_cjk_font", return_value="/fonts/cjk.ttf") as find:
            self.assertEqual(
                "/fonts/cjk.ttf",
                fonts.resolve_theme_font(fonts.SYSTEM_CJK_REGULAR),
            )
            find.assert_called_once_with(weight="regular")

        with patch("library.fonts.find_cjk_font", return_value="/fonts/cjk-bold.ttf") as find:
            self.assertEqual(
                "/fonts/cjk-bold.ttf",
                fonts.resolve_theme_font(fonts.SYSTEM_CJK_BOLD),
            )
            find.assert_called_once_with(weight="bold")

    def test_legacy_prefixed_alias_is_still_detected(self):
        legacy_value = "/bundle/res/fonts/system:cjk"

        with patch("library.fonts.find_cjk_font", return_value="/fonts/cjk.ttf"):
            self.assertEqual(
                "/fonts/cjk.ttf",
                fonts.resolve_theme_font(legacy_value),
            )

    def test_missing_cjk_font_logs_guidance_and_uses_bundled_fallback(self):
        fonts_dir = Path("/bundle/res/fonts")

        with patch("library.fonts.find_cjk_font", return_value=None), patch(
            "library.fonts.logger.error"
        ) as log_error:
            result = fonts.resolve_theme_font(
                fonts.SYSTEM_CJK_REGULAR,
                fonts_dir=fonts_dir,
            )

        self.assertEqual(str(fonts_dir / fonts.DEFAULT_THEME_FONT), result)
        log_error.assert_called_once()
        self.assertNotIn("error.cjk_font_missing", log_error.call_args.args[0])

    def test_existing_font_directory_addition_uses_resolver(self):
        with patch(
            "library.config.resolve_theme_font",
            return_value="/fonts/resolved-cjk.ttf",
        ) as resolve:
            result = config.FONTS_DIR + fonts.SYSTEM_CJK_REGULAR

        self.assertEqual("/fonts/resolved-cjk.ttf", result)
        resolve.assert_called_once_with(
            fonts.SYSTEM_CJK_REGULAR,
            fonts_dir=config._FONT_DIRECTORY,
        )


if __name__ == "__main__":
    unittest.main()
