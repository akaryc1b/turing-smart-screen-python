#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, dependency-free localization helper for user-facing strings.

The application stores stable internal values (for example ``AUTO`` or
``metric``) in configuration files.  Only labels shown to users should pass
through this module, so changing language never changes persisted values.
"""

from __future__ import annotations

import json
import locale as system_locale
import logging
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from library.resources import resource_path

LOGGER = logging.getLogger(__name__)

DEFAULT_LOCALE = "en_US"
SUPPORTED_LOCALES = ("en_US", "zh_CN")
LANGUAGE_ENV = "TURING_LANGUAGE"

_LOCALE_ALIASES = {
    "en": "en_US",
    "en_us": "en_US",
    "english": "en_US",
    "zh": "zh_CN",
    "zh_cn": "zh_CN",
    "zh_hans": "zh_CN",
    "zh_chs": "zh_CN",
    "chinese": "zh_CN",
    "chinese_simplified": "zh_CN",
}


def _default_locales_dir() -> Path:
    return resource_path("locales")


def normalize_locale(value: Optional[str]) -> Optional[str]:
    """Normalize common locale spellings to a supported locale code.

    ``None`` is returned for ``auto`` and unsupported languages so callers can
    continue to the next detection source instead of silently persisting an
    invalid locale.
    """

    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized or normalized.lower() == "auto":
        return None

    normalized = normalized.split(".", 1)[0].split("@", 1)[0].replace("-", "_")
    lowered = normalized.lower()

    if lowered in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[lowered]
    if lowered.startswith("zh"):
        return "zh_CN"
    if lowered.startswith("en"):
        return "en_US"

    for supported in SUPPORTED_LOCALES:
        if supported.lower() == lowered:
            return supported
    return None


def resolve_locale(
    requested: Optional[str] = "auto",
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    """Resolve an explicit, environment, or operating-system locale.

    Resolution order is: explicit value, ``TURING_LANGUAGE``, locale-related
    environment variables, Python's active locale, then English fallback.
    """

    explicit = normalize_locale(requested)
    if explicit:
        return explicit

    env = os.environ if environ is None else environ
    for variable in (LANGUAGE_ENV, "LC_ALL", "LC_MESSAGES", "LANG"):
        detected = normalize_locale(env.get(variable))
        if detected:
            return detected

    try:
        detected = normalize_locale(system_locale.getlocale()[0])
        if detected:
            return detected
    except (ValueError, TypeError):
        LOGGER.debug("Unable to detect the active operating-system locale", exc_info=True)

    return DEFAULT_LOCALE


def _flatten_catalog(values: Mapping[str, Any], prefix: str = "") -> Dict[str, str]:
    flattened: Dict[str, str] = {}
    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_catalog(value, full_key))
        elif isinstance(value, str):
            flattened[full_key] = value
        else:
            raise ValueError(f"Translation value for '{full_key}' must be a string")
    return flattened


def _read_catalog(locale_code: str, locales_dir: Path) -> Dict[str, str]:
    path = locales_dir / f"{locale_code}.json"
    try:
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, Mapping):
            raise ValueError("Catalog root must be an object")
        return _flatten_catalog(data)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("Cannot load translation catalog %s: %s", path, exc)
        return {}


def load_catalog(
    locale_code: str,
    locales_dir: Optional[Path] = None,
) -> Dict[str, str]:
    """Load a catalog merged over the English fallback catalog."""

    directory = Path(locales_dir) if locales_dir is not None else _default_locales_dir()
    resolved = normalize_locale(locale_code) or DEFAULT_LOCALE
    catalog = _read_catalog(DEFAULT_LOCALE, directory)
    if resolved != DEFAULT_LOCALE:
        catalog.update(_read_catalog(resolved, directory))
    return catalog


class Translator:
    """Translate stable message keys without leaking translated values to config."""

    def __init__(
        self,
        language: Optional[str] = "auto",
        locales_dir: Optional[Path] = None,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.locale = resolve_locale(language, environ=environ)
        self.locales_dir = Path(locales_dir) if locales_dir is not None else _default_locales_dir()
        self.catalog = load_catalog(self.locale, self.locales_dir)

    def translate(self, key: str, default: Optional[str] = None, **values: Any) -> str:
        template = self.catalog.get(key, default if default is not None else key)
        if not values:
            return template
        try:
            return template.format(**values)
        except (KeyError, ValueError, IndexError):
            LOGGER.warning("Invalid translation formatting for key '%s'", key, exc_info=True)
            return template

    __call__ = translate


_translator = Translator()


def set_language(language: Optional[str] = "auto", locales_dir: Optional[Path] = None) -> str:
    """Replace the process-wide translator and return the resolved locale."""

    global _translator
    _translator = Translator(language=language, locales_dir=locales_dir)
    return _translator.locale


def get_language() -> str:
    return _translator.locale


def tr(key: str, default: Optional[str] = None, **values: Any) -> str:
    return _translator.translate(key, default=default, **values)
