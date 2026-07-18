#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the strict configurator migration with disambiguated save buttons."""

from pathlib import Path
import runpy


SCRIPT = Path(__file__).resolve().parent / "apply_configurator_localization.py"


def main() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    ambiguous = "        'text=\"Save settings\"': 'text=tr(\"common.save_settings\")',\n"
    if text.count(ambiguous) != 1:
        raise RuntimeError("Cannot locate ambiguous Save settings migration rule")
    text = text.replace(ambiguous, "", 1)

    anchor = "    for old, new in replacements.items():\n        text = replace_once(text, old, new)\n\n"
    replacement = anchor + '''    text = replace_once(
        text,
        'self.save_btn = ttk.Button(self.window, text="Save settings", image=self.save_emoji, compound="left",',
        'self.save_btn = ttk.Button(self.window, text=tr("common.save_settings"), image=self.save_emoji, compound="left",',
    )
    text = replace_once(
        text,
        'self.save_btn = ttk.Button(self.window, text="Save settings", command=lambda: self.on_save_click())',
        'self.save_btn = ttk.Button(self.window, text=tr("common.save_settings"), command=lambda: self.on_save_click())',
    )

'''
    if text.count(anchor) != 1:
        raise RuntimeError("Cannot locate configurator replacement loop")
    SCRIPT.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
    runpy.run_path(str(SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
