#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later

import ast
import json
import re
import string
import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = REPOSITORY_ROOT / "locales"
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
IGNORED_DIRECTORIES = {".git", ".venv", "build", "dist", "tests"}


def flatten_catalog(values, prefix=""):
    flattened = {}
    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flattened.update(flatten_catalog(value, full_key))
        else:
            flattened[full_key] = value
    return flattened


def load_catalog(locale_code):
    path = LOCALES_DIR / f"{locale_code}.json"
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise AssertionError(f"Catalog root must be an object: {path}")
    return flatten_catalog(data)


def named_placeholders(template):
    names = set()
    for _, field_name, _, _ in string.Formatter().parse(template):
        if field_name:
            names.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return names


def iter_python_files():
    for path in REPOSITORY_ROOT.rglob("*.py"):
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue
        yield path


def collect_translation_calls():
    used_keys = set()
    invalid_calls = []
    for path in iter_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "tr":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                invalid_calls.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
                continue
            key = node.args[0].value
            if not isinstance(key, str):
                invalid_calls.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
                continue
            used_keys.add(key)
    return used_keys, invalid_calls


def assignment_dict_keys(tree, assignment_name):
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == assignment_name for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            raise AssertionError(f"{assignment_name} must remain a dictionary literal")
        return {
            key.value
            for key in node.value.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
    raise AssertionError(f"Assignment not found: {assignment_name}")


class CatalogQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = load_catalog("en_US")
        cls.chinese = load_catalog("zh_CN")

    def test_catalogs_have_exactly_the_same_keys(self):
        self.assertEqual(set(self.english), set(self.chinese))

    def test_named_placeholders_match_for_every_key(self):
        mismatches = {
            key: (
                named_placeholders(self.english[key]),
                named_placeholders(self.chinese[key]),
            )
            for key in self.english
            if named_placeholders(self.english[key])
            != named_placeholders(self.chinese[key])
        }
        self.assertEqual({}, mismatches)

    def test_catalog_files_are_valid_utf8_json(self):
        for locale_code in ("en_US", "zh_CN"):
            with self.subTest(locale=locale_code):
                path = LOCALES_DIR / f"{locale_code}.json"
                text = path.read_bytes().decode("utf-8")
                self.assertIsInstance(json.loads(text), dict)

    def test_all_literal_translation_keys_exist_and_are_used(self):
        used_keys, invalid_calls = collect_translation_calls()
        self.assertEqual([], invalid_calls, "tr() keys must be string literals")
        self.assertEqual(set(), used_keys - set(self.english), "Unknown tr() keys")
        self.assertEqual(set(), set(self.english) - used_keys, "Unused catalog keys")


class HardcodedChineseTests(unittest.TestCase):
    def test_core_python_does_not_embed_user_visible_chinese(self):
        violations = []
        for path in iter_python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if CJK_PATTERN.search(node.value):
                    violations.append(
                        f"{path.relative_to(REPOSITORY_ROOT)}:{getattr(node, 'lineno', '?')}"
                    )
        self.assertEqual([], violations, "Move user-visible Chinese strings to zh_CN.json")


class StableConfigurationValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_path = REPOSITORY_ROOT / "configure.py"
        cls.configure_tree = ast.parse(
            configure_path.read_text(encoding="utf-8"),
            filename=str(configure_path),
        )

    def test_configurator_maps_keep_stable_internal_keys(self):
        self.assertEqual(
            {"AUTO", "LHM", "PYTHON", "STUB", "STATIC"},
            assignment_dict_keys(self.configure_tree, "hw_lib_map"),
        )
        self.assertEqual(
            {"metric", "imperial", "standard"},
            assignment_dict_keys(self.configure_tree, "weather_unit_map"),
        )
        self.assertEqual(
            {"auto", "en_US", "zh_CN"},
            assignment_dict_keys(self.configure_tree, "interface_language_map"),
        )

    def test_default_config_keeps_protocol_values(self):
        config_path = REPOSITORY_ROOT / "config.yaml"
        config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

        self.assertEqual("auto", config_data["config"]["LANGUAGE"])
        self.assertEqual("AUTO", config_data["config"]["COM_PORT"])
        self.assertEqual("AUTO", config_data["config"]["HW_SENSORS"])
        self.assertEqual("metric", config_data["config"]["WEATHER_UNITS"])
        self.assertEqual("A", config_data["display"]["REVISION"])
        self.assertIs(False, config_data["display"]["DISPLAY_REVERSE"])


if __name__ == "__main__":
    unittest.main()
