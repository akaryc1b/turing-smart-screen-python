#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply the configurator localization refactor.

This one-time migration is intentionally strict: every replacement must match
exactly once so upstream changes cannot be overwritten silently.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "configure.py"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one occurrence, found {count}: {old[:120]!r}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from library.sensors.sensors_python import sensors_fans, is_cpu_fan\n",
        "from library.sensors.sensors_python import sensors_fans, is_cpu_fan\n"
        "from library.i18n import get_language, set_language, tr\n\n"
        "MAIN_DIRECTORY = Path(__file__).resolve().parent\n"
        "THEMES_DIR = MAIN_DIRECTORY / \"res/themes\"\n"
        "VERSION_FILE = MAIN_DIRECTORY / \"version.txt\"\n\n\n"
        "def _load_interface_language():\n"
        "    try:\n"
        "        with open(MAIN_DIRECTORY / \"config.yaml\", \"rt\", encoding=\"utf8\") as stream:\n"
        "            config_data, _, _ = ruamel.yaml.util.load_yaml_guess_indent(stream)\n"
        "        return config_data.get(\"config\", {}).get(\"LANGUAGE\", \"auto\")\n"
        "    except Exception:\n"
        "        return \"auto\"\n\n\n"
        "set_language(_load_interface_language())\n",
    )

    text = replace_once(
        text,
        "MAIN_DIRECTORY = Path(__file__).resolve().parent\n"
        "THEMES_DIR = MAIN_DIRECTORY / \"res/themes\"\n"
        "VERSION_FILE = MAIN_DIRECTORY / \"version.txt\"\n\n",
        "",
    )

    text = replace_once(
        text,
        "size_list = (\n"
        "    SIZE_0_96_INCH,\n"
        "    SIZE_2_x_INCH,\n"
        "    SIZE_2_8_ROUND_USB,\n"
        "    SIZE_3_5_INCH,\n"
        "    SIZE_4_6_INCH,\n"
        "    SIZE_5_INCH,\n"
        "    SIZE_5_2_INCH,\n"
        "    SIZE_8_INCH,\n"
        "    SIZE_8_8_INCH,\n"
        "    SIZE_8_8_INCH_NEWREV,\n"
        "    SIZE_12_3_INCH,\n"
        ")\n",
        "size_list = (\n"
        "    SIZE_0_96_INCH,\n"
        "    SIZE_2_x_INCH,\n"
        "    SIZE_2_8_ROUND_USB,\n"
        "    SIZE_3_5_INCH,\n"
        "    SIZE_4_6_INCH,\n"
        "    SIZE_5_INCH,\n"
        "    SIZE_5_2_INCH,\n"
        "    SIZE_8_INCH,\n"
        "    SIZE_8_8_INCH,\n"
        "    SIZE_8_8_INCH_NEWREV,\n"
        "    SIZE_12_3_INCH,\n"
        ")\n\n"
        "model_label_map = {\n"
        "    TURING_MODEL: tr(\"model.turing\"),\n"
        "    USBPCMONITOR_MODEL: tr(\"model.usb_pc_monitor\"),\n"
        "    XUANFANG_MODEL: tr(\"model.xuanfang\"),\n"
        "    KIPYE_MODEL: tr(\"model.kipye\"),\n"
        "    WEACT_MODEL: tr(\"model.weact\"),\n"
        "    SIMULATED_MODEL: tr(\"model.simulated\"),\n"
        "}\n\n"
        "size_label_map = {\n"
        "    size: size for size in size_list\n"
        "}\n"
        "size_label_map[SIZE_8_8_INCH_NEWREV] = tr(\"size.new_revision\", size='8.8\\\" / 9.2\\\"')\n"
        "size_label_map[SIZE_2_8_ROUND_USB] = tr(\"size.round_new_revision\", size='2.8\\\"')\n",
    )

    old_options = '''hw_lib_map = {"AUTO": "Automatic", "LHM": "LibreHardwareMonitor (admin.)", "PYTHON": "Python libraries",
              "STUB": "Fake random data", "STATIC": "Fake static data"}
reverse_map = {False: "classic", True: "reverse"}
weather_unit_map = {"metric": "metric - °C", "imperial": "imperial - °F", "standard": "standard - °K"}
weather_lang_map = {"sq": "Albanian", "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque",
                    "be": "Belarusian", "bg": "Bulgarian", "ca": "Catalan", "zh_cn": "Chinese Simplified",
                    "zh_tw": "Chinese Traditional", "hr": "Croatian", "cz": "Czech", "da": "Danish", "nl": "Dutch",
                    "en": "English", "fi": "Finnish", "fr": "French", "gl": "Galician", "de": "German", "el": "Greek",
                    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian",
                    "it": "Italian", "ja": "Japanese", "kr": "Korean", "ku": "Kurmanji (Kurdish)", "la": "Latvian",
                    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "fa": "Persian (Farsi)", "pl": "Polish",
                    "pt": "Portuguese", "pt_br": "Português Brasil", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
                    "sk": "Slovak", "sl": "Slovenian", "sp": "Spanish", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
                    "ua": "Ukrainian", "vi": "Vietnamese", "zu": "Zulu"}
'''
    new_options = '''hw_lib_map = {
    "AUTO": tr("option.hardware_auto"),
    "LHM": tr("option.hardware_lhm"),
    "PYTHON": tr("option.hardware_python"),
    "STUB": tr("option.hardware_stub"),
    "STATIC": tr("option.hardware_static"),
}
reverse_map = {
    False: tr("option.orientation_classic"),
    True: tr("option.orientation_reverse"),
}
weather_unit_map = {
    "metric": tr("option.unit_metric"),
    "imperial": tr("option.unit_imperial"),
    "standard": tr("option.unit_standard"),
}
interface_language_map = {
    "auto": tr("language.auto"),
    "en_US": tr("language.english"),
    "zh_CN": tr("language.chinese_simplified"),
}
weather_lang_english_map = {"sq": "Albanian", "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "eu": "Basque",
                    "be": "Belarusian", "bg": "Bulgarian", "ca": "Catalan", "zh_cn": "Chinese Simplified",
                    "zh_tw": "Chinese Traditional", "hr": "Croatian", "cz": "Czech", "da": "Danish", "nl": "Dutch",
                    "en": "English", "fi": "Finnish", "fr": "French", "gl": "Galician", "de": "German", "el": "Greek",
                    "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian",
                    "it": "Italian", "ja": "Japanese", "kr": "Korean", "ku": "Kurmanji (Kurdish)", "la": "Latvian",
                    "lt": "Lithuanian", "mk": "Macedonian", "no": "Norwegian", "fa": "Persian (Farsi)", "pl": "Polish",
                    "pt": "Portuguese", "pt_br": "Português Brasil", "ro": "Romanian", "ru": "Russian", "sr": "Serbian",
                    "sk": "Slovak", "sl": "Slovenian", "sp": "Spanish", "sv": "Swedish", "th": "Thai", "tr": "Turkish",
                    "ua": "Ukrainian", "vi": "Vietnamese", "zu": "Zulu"}

_WEATHER_LANGUAGE_LOCALE_ALIASES = {
    "cz": "cs",
    "kr": "ko",
    "sp": "es",
    "ua": "uk",
    "pt_br": "pt_BR",
    "zh_cn": "zh_Hans",
    "zh_tw": "zh_Hant",
}


def _localize_weather_language(api_code, english_name):
    locale_code = _WEATHER_LANGUAGE_LOCALE_ALIASES.get(api_code, api_code)
    try:
        return babel.Locale.parse(locale_code, sep="_").get_display_name(get_language())
    except (ValueError, TypeError):
        return english_name


weather_lang_map = {
    code: _localize_weather_language(code, english_name)
    for code, english_name in weather_lang_english_map.items()
}
'''
    text = replace_once(text, old_options, new_options)

    text = replace_once(
        text,
        "def get_com_ports():\n",
        "def _display_value(mapping, internal_value):\n"
        "    return mapping.get(internal_value, internal_value)\n\n\n"
        "def _internal_value(mapping, display_value):\n"
        "    return next((key for key, value in mapping.items() if value == display_value), display_value)\n\n\n"
        "def get_com_ports():\n",
    )
    text = replace_once(text, '    com_ports_names = ["Automatic detection"]', '    com_ports_names = [tr("common.automatic_detection")]')
    text = replace_once(text, '    if_list.insert(0, "None")', '    if_list.insert(0, tr("common.none"))')
    text = replace_once(
        text,
        '''    auto_detected_cpu_fan = "None"
    for name, entries in sensors_fans().items():
        for entry in entries:
            fan_list.append("%s/%s (%d%% - %d RPM)" % (name, entry.label, entry.percent, entry.current))
            if (is_cpu_fan(entry.label) or is_cpu_fan(name)) and auto_detected_cpu_fan == "None":
                auto_detected_cpu_fan = "Auto-detected: %s/%s" % (name, entry.label)

    fan_list.insert(0, auto_detected_cpu_fan)''',
        '''    auto_detected_cpu_fan = None
    for name, entries in sensors_fans().items():
        for entry in entries:
            fan_list.append("%s/%s (%d%% - %d RPM)" % (name, entry.label, entry.percent, entry.current))
            if (is_cpu_fan(entry.label) or is_cpu_fan(name)) and auto_detected_cpu_fan is None:
                auto_detected_cpu_fan = tr("option.auto_detected_fan", fan=f"{name}/{entry.label}")

    fan_list.insert(0, auto_detected_cpu_fan or tr("common.none"))''',
    )

    replacements = {
        "self.window.title('Turing System Monitor configuration')": 'self.window.title(tr("app.configuration_title"))',
        'self.window.geometry("820x590")': 'self.window.geometry("820x640")',
        "text='Display configuration'": 'text=tr("config.display_section")',
        "text='Smart screen model'": 'text=tr("config.smart_screen_model")',
        "values=list(dict.fromkeys((revision_and_size_to_model_map.values())))": "values=list(dict.fromkeys(model_label_map.values()))",
        "text='Smart screen size'": 'text=tr("config.smart_screen_size")',
        "values=size_list": "values=[_display_value(size_label_map, size) for size in size_list]",
        "text='COM port'": 'text=tr("config.com_port")',
        "text='Orientation'": 'text=tr("config.orientation")',
        "text='Brightness'": 'text=tr("config.brightness")',
        'text="⚠ Turing 3.5\\" displays can get hot at high brightness!"': 'text=tr("config.brightness_warning")',
        "text='System Monitor Configuration'": 'text=tr("config.system_monitor_section")',
        "text='Theme'": 'text=tr("config.theme")',
        "text='Hardware monitoring'": 'text=tr("config.hardware_monitoring")',
        "text='Ethernet interface'": 'text=tr("config.ethernet_interface")',
        "text='Wi-Fi interface'": 'text=tr("config.wifi_interface")',
        'text="❌ Restart as admin. or select another Hardware monitoring"': 'text=tr("config.restart_as_admin")',
        "text='CPU fan (？)'": 'text=tr("config.cpu_fan")',
        'text="Weather\\n& Ping"': 'text=tr("config.weather_and_ping")',
        'text="Open themes\\nfolder"': 'text=tr("config.open_themes_folder")',
        'text="Edit theme"': 'text=tr("config.edit_theme")',
        'text="Save settings"': 'text=tr("common.save_settings")',
        'text="Save and run"': 'text=tr("common.save_and_run")',
    }
    for old, new in replacements.items():
        text = replace_once(text, old, new)

    text = replace_once(
        text,
        '''        self.tooltip = ToolTip(self.cpu_fan_label,
                               msg="If \\"None\\" is selected, CPU fan was not auto-detected.\\n"
                                   "Manually select your CPU fan from the list.\\n\\n"
                                   "Fans missing from the list? Install lm-sensors package\\n"
                                   "and run 'sudo sensors-detect' command, then reboot.")

        try:''',
        '''        self.tooltip = ToolTip(self.cpu_fan_label, msg=tr("config.fan_tooltip"))

        self.language_label = ttk.Label(self.window, text=tr("config.interface_language"))
        self.language_label.place(x=370, y=500)
        self.language_cb = ttk.Combobox(
            self.window,
            values=list(interface_language_map.values()),
            state='readonly',
        )
        self.language_cb.place(x=550, y=495, width=250)
        self.language_hint = ttk.Label(
            self.window,
            text=tr("language.restart_hint"),
            foreground=DISABLED_COLOR,
        )
        self.language_hint.place(x=550, y=525)

        try:''',
    )

    text = replace_once(text, "version_label.place(x=5, y=550)", "version_label.place(x=5, y=610)")
    for x in (80, 220, 360, 500, 640):
        text = replace_once(text, f".place(x={x}, y=520,", f".place(x={x}, y=560,")

    text = replace_once(
        text,
        "            author_name = theme_data.get('author', 'unknown')\n"
        "            self.theme_author.config(text=\"Author: \" + author_name)",
        "            author_name = (theme_data or {}).get('author', tr(\"common.unknown\"))\n"
        "            self.theme_author.config(text=tr(\"config.author\", name=author_name))",
    )

    text = replace_once(
        text,
        "        # Check if theme is valid\n",
        "        configured_language = self.config.get('config', {}).get('LANGUAGE', 'auto')\n"
        "        self.language_cb.set(_display_value(interface_language_map, configured_language))\n\n"
        "        # Check if theme is valid\n",
    )
    text = replace_once(text, "            self.size_cb.set(size)", "            self.size_cb.set(_display_value(size_label_map, size))")
    text = replace_once(
        text,
        "            self.model_cb.set(revision_and_size_to_model_map[(revision, size)])",
        "            model = revision_and_size_to_model_map[(revision, size)]\n"
        "            self.model_cb.set(_display_value(model_label_map, model))",
    )
    text = replace_once(
        text,
        "        self.config['config']['THEME'] = self.theme_cb.get()",
        "        self.config['config']['LANGUAGE'] = _internal_value(interface_language_map, self.language_cb.get())\n"
        "        self.config['config']['THEME'] = self.theme_cb.get()",
    )
    text = replace_once(
        text,
        "        self.config['display']['REVISION'] = model_and_size_to_revision_map[(self.model_cb.get(), self.size_cb.get())]",
        "        model = _internal_value(model_label_map, self.model_cb.get())\n"
        "        size = _internal_value(size_label_map, self.size_cb.get())\n"
        "        self.config['display']['REVISION'] = model_and_size_to_revision_map[(model, size)]",
    )
    text = replace_once(text, "        model = self.model_cb.get()", "        model = _internal_value(model_label_map, self.model_cb.get())")
    text = replace_once(text, "        size = self.size_cb.get()", "        size = _internal_value(size_label_map, self.size_cb.get())")
    text = replace_once(
        text,
        "        if int(self.brightness_slider.get()) > 50 and self.model_cb.get() == TURING_MODEL and self.size_cb.get() == SIZE_3_5_INCH:",
        "        model = _internal_value(model_label_map, self.model_cb.get())\n"
        "        size = _internal_value(size_label_map, self.size_cb.get())\n"
        "        if int(self.brightness_slider.get()) > 50 and model == TURING_MODEL and size == SIZE_3_5_INCH:",
    )

    weather_replacements = {
        "self.window.title('Configure weather & ping')": 'self.window.title(tr("weather.window_title"))',
        "text='Hostname / IP to ping'": 'text=tr("weather.ping_host")',
        "text='Weather forecast (OpenWeatherMap API)'": 'text=tr("weather.forecast_section")',
        'text="Click here to subscribe to OpenWeatherMap One Call API 3.0."': 'text=tr("weather.subscribe_link")',
        "text='OpenWeatherMap API key'": 'text=tr("weather.api_key")',
        "text='Latitude'": 'text=tr("weather.latitude")',
        "text='Longitude'": 'text=tr("weather.longitude")',
        "text='Units'": 'text=tr("weather.units")',
        "text='Language'": 'text=tr("weather.api_language")',
        "text='Location search'": 'text=tr("weather.location_search")',
        'text="Enter location"': 'text=tr("weather.enter_location")',
        'text="Search"': 'text=tr("common.search")',
        'text="Select location\\n(use after Search)"': 'text=tr("weather.select_location")',
        'text="Fill in lat/long"': 'text=tr("weather.fill_coordinates")',
    }
    for old, new in weather_replacements.items():
        text = replace_once(text, old, new)

    text = replace_once(
        text,
        '''        weather_info_label = ttk.Label(self.window,
                                       text="To display weather forecast on themes that support it, you need an OpenWeatherMap \\"One Call API 3.0\\" key.\\n"
                                            "You will get 1,000 API calls per day for free. This program is configured to stay under this threshold (~300 calls/day).")''',
        '''        weather_info_label = ttk.Label(self.window, text=tr("weather.api_description"))''',
    )
    text = replace_once(
        text,
        '''        latlong_label = ttk.Label(self.window,
                                  text="You can use online services to get your latitude/longitude e.g. latlong.net (click here)")''',
        '''        latlong_label = ttk.Label(self.window, text=tr("weather.coordinate_help"))''',
    )
    text = replace_once(
        text,
        '''        self.citysearch2_label = ttk.Label(self.window,
                                           text="Enter location to automatically get coordinates (latitude/longitude).\\n"
                                                "For example \\"Berlin\\" \\"London, GB\\", \\"London, Quebec\\".\\n"
                                                "Remember to set valid API key and pick language first!")''',
        '''        self.citysearch2_label = ttk.Label(self.window, text=tr("weather.location_search_help"))''',
    )

    text = replace_once(
        text,
        "            self.citysearch_show_warning(\"API key and city name cannot be empty.\")",
        "            self.citysearch_show_warning(tr(\"weather.error_empty_api_city\"))",
    )
    text = replace_once(
        text,
        "            self.citysearch_show_warning(\"Error fetching OpenWeatherMap Geo API\")",
        "            self.citysearch_show_warning(tr(\"weather.error_fetch\"))",
    )
    text = replace_once(
        text,
        "            self.citysearch_show_warning(\"Invalid OpenWeatherMap API key.\")",
        "            self.citysearch_show_warning(tr(\"weather.error_invalid_api_key\"))",
    )
    text = replace_once(
        text,
        "            self.citysearch_show_warning(f\"Error #{request.status_code} fetching OpenWeatherMap Geo API.\")",
        "            self.citysearch_show_warning(tr(\"weather.error_http\", status=request.status_code))",
    )
    text = replace_once(
        text,
        "            country = babel.Locale(lang).territories[country_code]",
        "            try:\n"
        "                country = babel.Locale.parse(get_language(), sep=\"_\").territories.get(country_code, country_code)\n"
        "            except (ValueError, TypeError):\n"
        "                country = country_code",
    )
    text = replace_once(
        text,
        "            self.citysearch_show_warning(\"No given city found.\")",
        "            self.citysearch_show_warning(tr(\"weather.no_city_found\"))",
    )
    text = replace_once(
        text,
        '            self.citysearch_show_warning("Select your city now from list and apply \\"Fill in lat/long\\".")',
        '            self.citysearch_show_warning(tr("weather.select_city_hint"))',
    )
    text = replace_once(
        text,
        "            self.citysearch_show_warning(\"No city selected or no search results.\")",
        "            self.citysearch_show_warning(tr(\"weather.no_city_selected\"))",
    )
    text = replace_once(
        text,
        '        self.citysearch_show_warning(f"Lat/long values filled for {city[\'full_name\']}")',
        '        self.citysearch_show_warning(tr("weather.coordinates_filled", location=city[\'full_name\']))',
    )

    TARGET.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
