#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the strict configurator migration with disambiguated rules."""

from pathlib import Path
import runpy


SCRIPT = Path(__file__).resolve().parent / "apply_configurator_localization.py"


def replace_source_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one migration-source occurrence, found {count}: {old[:100]!r}")
    return text.replace(old, new, 1)


def main() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    # Keep existing path constants at their original location. Language
    # detection only needs a direct config path before localized maps are built.
    inserted_path_constants = '''        "MAIN_DIRECTORY = Path(__file__).resolve().parent\n"
        "THEMES_DIR = MAIN_DIRECTORY / \\"res/themes\\"\n"
        "VERSION_FILE = MAIN_DIRECTORY / \\"version.txt\\"\n\n\n"
'''
    text = replace_source_once(text, inserted_path_constants, "")
    text = replace_source_once(
        text,
        '        "        with open(MAIN_DIRECTORY / \\"config.yaml\\", \\"rt\\", encoding=\\"utf8\\") as stream:\\n"',
        '        "        with open(Path(__file__).resolve().parent / \\"config.yaml\\", \\"rt\\", encoding=\\"utf8\\") as stream:\\n"',
    )

    duplicate_path_removal = '''    text = replace_once(
        text,
        "MAIN_DIRECTORY = Path(__file__).resolve().parent\n"
        "THEMES_DIR = MAIN_DIRECTORY / \\"res/themes\\"\n"
        "VERSION_FILE = MAIN_DIRECTORY / \\"version.txt\\"\n\n",
        "",
    )

'''
    text = replace_source_once(text, duplicate_path_removal, "")

    # "Save settings" occurs in both the main and weather windows. Match the
    # complete widget declarations so both remain strict and unambiguous.
    ambiguous_save = "        'text=\"Save settings\"': 'text=tr(\"common.save_settings\")',\n"
    text = replace_source_once(text, ambiguous_save, "")

    anchor = "    for old, new in replacements.items():\n        text = replace_once(text, old, new)\n\n"
    disambiguated_saves = anchor + '''    text = replace_once(
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
    text = replace_source_once(text, anchor, disambiguated_saves)

    SCRIPT.write_text(text, encoding="utf-8")
    runpy.run_path(str(SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
