#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import unittest
from unittest import mock

from library.lcd.lcd_comm import LcdComm
from library.lcd.lcd_simulated import LcdSimulated


class SimulatedDisplayFallbackTests(unittest.TestCase):
    def test_empty_fallback_glyph_bitmap_is_skipped(self):
        lcd = LcdSimulated.__new__(LcdSimulated)
        LcdComm.__init__(lcd, display_width=320, display_height=480)
        empty_image = mock.Mock()
        empty_image.size = (1, 0)

        lcd.DisplayPILImage(empty_image, x=18, y=18)

        empty_image.crop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
