#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply the one-time baseline fix required before localization work."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIGURE = ROOT / "configure.py"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one occurrence of {old!r}, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    content = CONFIGURE.read_text(encoding="utf-8")
    content = replace_once(
        content,
        'SIZE_2_8_INCH_NEWREV = "2.8\\" round (V1.X new HW rev.)"',
        'SIZE_2_8_ROUND_USB = "2.8\\" round (V1.X new HW rev.)"',
    )
    CONFIGURE.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
