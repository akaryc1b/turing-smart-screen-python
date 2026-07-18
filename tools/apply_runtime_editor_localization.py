#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply the one-time runtime and theme-editor localization refactor."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "main.py"
EDITOR = ROOT / "theme-editor.py"


def replace_once(text: str, old: str, new: str, target: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{target}: expected one occurrence, found {count}: {old[:120]!r}")
    return text.replace(old, new, 1)


def localize_main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import os\nimport sys\n",
        "import os\nimport sys\n\nfrom library.i18n import set_language, tr\n",
        "main.py",
    )
    text = replace_once(
        text,
        '''    print("""Import error: %s
Please follow start guide to install required packages: https://github.com/mathoudebine/turing-smart-screen-python/wiki/System-monitor-:-how-to-start
Or the troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed""" % str(
        e))''',
        '''    print(tr("error.import", error=str(e)))
    print(tr("error.import_help"))''',
        "main.py",
    )
    text = replace_once(
        text,
        '''try:
    import pystray
except:
    # If pystray cannot be loaded do not stop the program, just ignore it. The tray icon will not be displayed.
    pass

MAIN_DIRECTORY = Path(__file__).resolve().parent
''',
        '''try:
    import pystray
except:
    # If pystray cannot be loaded do not stop the program, just ignore it. The tray icon will not be displayed.
    pass

from library import config as app_config

set_language(app_config.CONFIG_DATA.get("config", {}).get("LANGUAGE", "auto"))

MAIN_DIRECTORY = Path(__file__).resolve().parent
''',
        "main.py",
    )
    text = replace_once(text, "            name='Turing System Monitor',", '            name=tr("app.name"),', "main.py")
    text = replace_once(text, "            title='Turing System Monitor',", '            title=tr("app.name"),', "main.py")
    text = replace_once(text, "                    text='Configure',", '                    text=tr("common.configure"),', "main.py")
    text = replace_once(text, "                    text='Exit',", '                    text=tr("common.exit"),', "main.py")
    MAIN.write_text(text, encoding="utf-8")


def localize_editor() -> None:
    text = EDITOR.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "import sys\nimport time\n",
        "import sys\nimport time\n\nfrom library.i18n import set_language, tr\n",
        "theme-editor.py",
    )
    text = replace_once(
        text,
        '''except:
    print(
        "[ERROR] Tkinter dependency not installed. Please follow troubleshooting page: https://github.com/mathoudebine/turing-smart-screen-python/wiki/Troubleshooting#all-os-tkinter-dependency-not-installed")''',
        '''except:
    print(tr("error.tkinter_missing"))
    print(tr("error.tkinter_help"))''',
        "theme-editor.py",
    )
    text = replace_once(text, '    print("Usage :")', '    print(tr("theme_editor.usage"))', "theme-editor.py")
    text = replace_once(text, '    print("Examples : ")', '    print(tr("theme_editor.examples"))', "theme-editor.py")
    text = replace_once(
        text,
        "from library import config\n\nconfig.CONFIG_DATA",
        "from library import config\n\nset_language(config.CONFIG_DATA.get(\"config\", {}).get(\"LANGUAGE\", \"auto\"))\n\nconfig.CONFIG_DATA",
        "theme-editor.py",
    )
    text = replace_once(text, '        viewer.title("Turing SysMon Theme Editor")', '        viewer.title(tr("app.theme_editor_title"))', "theme-editor.py")
    text = replace_once(text, '        zoom_plus_btn = tkinter.Button(viewer, text="Zoom +", command=lambda: on_zoom_plus())', '        zoom_plus_btn = tkinter.Button(viewer, text=tr("theme_editor.zoom_in"), command=lambda: on_zoom_plus())', "theme-editor.py")
    text = replace_once(text, '        zoom_minus_btn = tkinter.Button(viewer, text="Zoom -", command=lambda: on_zoom_minus())', '        zoom_minus_btn = tkinter.Button(viewer, text=tr("theme_editor.zoom_out"), command=lambda: on_zoom_minus())', "theme-editor.py")
    text = replace_once(text, '        label_coord = tkinter.Label(viewer, text="Click or draw a zone to show coordinates")', '        label_coord = tkinter.Label(viewer, text=tr("theme_editor.coordinate_hint"))', "theme-editor.py")
    text = replace_once(text, '        label_info = tkinter.Label(viewer, text="This preview will reload when theme file is updated")', '        label_info = tkinter.Label(viewer, text=tr("theme_editor.reload_hint"))', "theme-editor.py")
    text = replace_once(
        text,
        '''        label_coord.config(text='Drawing zone from [{:0.0f},{:0.0f}] to [{:0.0f},{:0.0f}]'.format(x0 * RESIZE_FACTOR,
                                                                                                  y0 * RESIZE_FACTOR,
                                                                                                  x1 * RESIZE_FACTOR,
                                                                                                  y1 * RESIZE_FACTOR))''',
        '''        label_coord.config(text=tr("theme_editor.drawing_zone",
                                   x0=x0 * RESIZE_FACTOR,
                                   y0=y0 * RESIZE_FACTOR,
                                   x1=x1 * RESIZE_FACTOR,
                                   y1=y1 * RESIZE_FACTOR))''',
        "theme-editor.py",
    )
    text = replace_once(
        text,
        '''            label_coord.config(text='Zone: X={:0.0f}, Y={:0.0f}, width={:0.0f} height={:0.0f}'.format(x * RESIZE_FACTOR,
                                                                                                      y * RESIZE_FACTOR,
                                                                                                      width * RESIZE_FACTOR,
                                                                                                      height * RESIZE_FACTOR))''',
        '''            label_coord.config(text=tr("theme_editor.zone",
                                       x=x * RESIZE_FACTOR,
                                       y=y * RESIZE_FACTOR,
                                       width=width * RESIZE_FACTOR,
                                       height=height * RESIZE_FACTOR))''',
        "theme-editor.py",
    )
    text = replace_once(
        text,
        '''            label_coord.config(
                text='X={:0.0f}, Y={:0.0f} (click and drag to draw a zone)'.format(x0 * RESIZE_FACTOR,
                                                                                   y0 * RESIZE_FACTOR))''',
        '''            label_coord.config(text=tr("theme_editor.point",
                                       x=x0 * RESIZE_FACTOR,
                                       y=y0 * RESIZE_FACTOR))''',
        "theme-editor.py",
    )
    EDITOR.write_text(text, encoding="utf-8")


def main() -> None:
    localize_main()
    localize_editor()


if __name__ == "__main__":
    main()
