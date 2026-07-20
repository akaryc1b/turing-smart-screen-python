#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Audit Simplified Chinese localization catalogs and user-visible text."""

from __future__ import annotations

import argparse
import ast
import json
import re
import string
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA_VERSION = 1
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
ENGLISH_WORD_PATTERN = re.compile(r"[A-Za-z]{2,}")
URL_PATTERN = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
WINDOWS_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")
ENVIRONMENT_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
FORMATTER = string.Formatter()

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "frozen-smoke-artifacts",
}

PYTHON_ENTRYPOINTS = ("configure.py", "theme-editor.py", "main.py")
PYTHON_UI_KEYWORDS = {
    "caption",
    "detail",
    "label",
    "message",
    "prompt",
    "text",
    "title",
}
UI_METHODS = {
    "add_cascade",
    "add_checkbutton",
    "add_command",
    "add_radiobutton",
    "askokcancel",
    "askquestion",
    "askretrycancel",
    "askyesno",
    "askyesnocancel",
    "showerror",
    "showinfo",
    "showwarning",
    "title",
}
UI_CONSTRUCTORS = {
    "Button",
    "Checkbutton",
    "Label",
    "LabelFrame",
    "Menu",
    "Message",
    "OptionMenu",
    "Radiobutton",
    "Scale",
    "Text",
    "Toplevel",
}
INNO_VISIBLE_DIRECTIVES = {
    "[components]": {"description"},
    "[run]": {"description", "statusmsg"},
    "[tasks]": {"description"},
    "[types]": {"description"},
}
LOGGER_METHODS = {"critical", "error", "exception", "warning"}
TRANSLATOR_NAMES = {"tr", "translator", "_translator"}
ALLOWED_CATEGORIES = {
    "log-only",
    "path",
    "product-name",
    "protocol",
    "stable-internal-value",
    "technical-term",
    "url",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    rule: str
    path: str
    line: int
    message: str
    key: Optional[str] = None
    value: Optional[str] = None

    def sort_key(self) -> tuple[Any, ...]:
        return (
            SEVERITY_ORDER[self.severity],
            self.path,
            self.line,
            self.rule,
            self.key or "",
            self.value or "",
            self.message,
        )


@dataclass(frozen=True)
class TranslationReference:
    path: str
    line: int
    key: Optional[str]
    expression: str


@dataclass(frozen=True)
class AllowlistEntry:
    path: str
    rule: str
    category: str
    reason: str
    key: Optional[str] = None
    value: Optional[str] = None


class LocalizationCoverageError(RuntimeError):
    """Raised for invalid command-line configuration."""


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_excluded(path: Path, root: Path) -> bool:
    try:
        parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_PARTS for part in parts)


def discover_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for name in PYTHON_ENTRYPOINTS:
        path = root / name
        if path.is_file():
            candidates.append(path)

    library_root = root / "library"
    if library_root.is_dir():
        candidates.extend(library_root.rglob("*.py"))

    installer_root = root / "tools" / "windows-installer"
    if installer_root.is_dir():
        candidates.extend(installer_root.glob("*.iss"))

    return sorted(
        {path.resolve() for path in candidates if not is_excluded(path, root)},
        key=lambda item: relative_path(item, root),
    )


def flatten_catalog(values: Mapping[str, Any], prefix: str = "") -> dict[str, str]:
    flattened: dict[str, str] = {}
    for raw_key, value in values.items():
        key = str(raw_key)
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, Mapping):
            flattened.update(flatten_catalog(value, full_key))
        elif isinstance(value, str):
            flattened[full_key] = value
        else:
            raise ValueError(f"translation value for '{full_key}' must be a string")
    return flattened


def load_catalog(path: Path, root: Path, issues: list[Issue]) -> dict[str, str]:
    rel = relative_path(path, root)
    try:
        with path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
        if not isinstance(payload, Mapping):
            raise ValueError("catalog root must be an object")
        return flatten_catalog(payload)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues.append(
            Issue(
                severity="error",
                rule="catalog-invalid",
                path=rel,
                line=1,
                message=str(exc),
            )
        )
        return {}


def placeholder_signature(value: str) -> tuple[tuple[str, str, str], ...]:
    signature: list[tuple[str, str, str]] = []

    def collect(template: str) -> None:
        for _, field_name, format_spec, conversion in FORMATTER.parse(template):
            if field_name is None:
                continue
            normalized_spec = format_spec or ""
            signature.append((field_name, normalized_spec, conversion or ""))
            if "{" in normalized_spec or "}" in normalized_spec:
                collect(normalized_spec)

    collect(value)
    return tuple(sorted(signature))


def looks_like_url(value: str) -> bool:
    return bool(URL_PATTERN.search(value.strip()))


def looks_like_path(value: str) -> bool:
    stripped = value.strip()
    if WINDOWS_PATH_PATTERN.match(stripped):
        return True
    if stripped.startswith(("./", "../", "/")):
        return True
    if "/" in stripped or "\\" in stripped:
        suffix = Path(stripped.replace("\\", "/")).suffix.lower()
        return suffix in {
            ".ini",
            ".iss",
            ".json",
            ".md",
            ".png",
            ".py",
            ".spec",
            ".ttc",
            ".ttf",
            ".yaml",
            ".yml",
        }
    return False


def looks_like_filename(value: str) -> bool:
    stripped = value.strip()
    if any(character.isspace() for character in stripped):
        return False
    suffix = Path(stripped).suffix.lower()
    return suffix in {
        ".exe",
        ".ini",
        ".iss",
        ".json",
        ".log",
        ".md",
        ".png",
        ".py",
        ".spec",
        ".tar",
        ".ttc",
        ".ttf",
        ".yaml",
        ".yml",
        ".zip",
    }


def looks_like_stable_internal_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped or "\n" in stripped or " " in stripped:
        return False
    if ENVIRONMENT_PATTERN.fullmatch(stripped):
        return True
    if re.fullmatch(r"[A-Za-z0-9_.:+-]+", stripped):
        if stripped.lower() in {
            "auto",
            "classic",
            "imperial",
            "metric",
            "reverse",
            "standard",
            "static",
        }:
            return True
        if stripped.startswith(("TUR_", "WEACT_")):
            return True
        if re.fullmatch(r"(?:SIMU|LHM|STUB|PYTHON|AUTO|STATIC)", stripped):
            return True
        if re.fullmatch(r"[A-D]", stripped):
            return True
    return False


def looks_like_technical_text(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if looks_like_url(stripped) or looks_like_path(stripped):
        return True
    if looks_like_filename(stripped) or looks_like_stable_internal_value(stripped):
        return True
    if stripped.startswith(("sha256:", "--")):
        return True
    if re.fullmatch(r"[#%+\-./:0-9A-Fa-fxX]+", stripped):
        return True
    return False


def literal_string(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [part.value for part in node.values if isinstance(part, ast.Constant)]
        if parts and all(isinstance(part, str) for part in parts):
            return "{}".join(parts)
    return None


def call_name(node: ast.Call) -> str:
    target = node.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return ""


def is_translation_call(node: ast.Call, translator_names: set[str]) -> bool:
    func = node.func
    if isinstance(func, ast.Name) and func.id in translator_names:
        return True
    if isinstance(func, ast.Attribute) and func.attr == "translate":
        return True
    if isinstance(func, ast.Call):
        inner = func.func
        return isinstance(inner, ast.Name) and inner.id == "Translator"
    return False


def translator_assignments(tree: ast.AST) -> set[str]:
    names = set(TRANSLATOR_NAMES)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        func_name = call_name(value)
        if func_name != "Translator":
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def translation_references(
    tree: ast.AST,
    rel_path: str,
) -> list[TranslationReference]:
    references: list[TranslationReference] = []
    translator_names = translator_assignments(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not is_translation_call(node, translator_names):
            continue
        if not node.args:
            references.append(
                TranslationReference(
                    path=rel_path,
                    line=getattr(node, "lineno", 1),
                    key=None,
                    expression="<missing argument>",
                )
            )
            continue
        key = literal_string(node.args[0])
        expression = ast.unparse(node.args[0]) if hasattr(ast, "unparse") else "<dynamic>"
        references.append(
            TranslationReference(
                path=rel_path,
                line=getattr(node, "lineno", 1),
                key=key,
                expression=expression,
            )
        )
    return references


def english_candidate(value: str) -> bool:
    return bool(ENGLISH_WORD_PATTERN.search(value)) and not CJK_PATTERN.search(value)


def user_visible_literals(
    tree: ast.AST,
    rel_path: str,
) -> list[Issue]:
    issues: list[Issue] = []
    translator_names = translator_assignments(tree)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        if is_translation_call(node, translator_names):
            continue

        candidate_nodes: list[tuple[ast.AST, str]] = []
        if name in UI_METHODS:
            candidate_nodes.extend((arg, "ui") for arg in node.args[:2])
        if name in UI_CONSTRUCTORS or any(
            keyword.arg in PYTHON_UI_KEYWORDS for keyword in node.keywords
        ):
            candidate_nodes.extend(
                (keyword.value, "ui")
                for keyword in node.keywords
                if keyword.arg in PYTHON_UI_KEYWORDS
            )
        if name == "print":
            candidate_nodes.extend((arg, "console") for arg in node.args)
        if name in LOGGER_METHODS:
            func = node.func
            if isinstance(func, ast.Attribute):
                owner = func.value
                if isinstance(owner, ast.Name) and owner.id.lower() in {
                    "logger",
                    "logging",
                    "log",
                }:
                    candidate_nodes.extend((arg, "logger") for arg in node.args[:1])

        seen: set[tuple[int, str]] = set()
        for candidate, context in candidate_nodes:
            value = literal_string(candidate)
            if value is None or not english_candidate(value):
                continue
            line = getattr(candidate, "lineno", getattr(node, "lineno", 1))
            identity = (line, value)
            if identity in seen:
                continue
            seen.add(identity)

            if context == "ui" and looks_like_stable_internal_value(value):
                issues.append(
                    Issue(
                        severity="error",
                        rule="internal-value-in-ui",
                        path=rel_path,
                        line=line,
                        message=(
                            "stable internal value is shown directly in UI; use a "
                            "translated display label without changing the stored value"
                        ),
                        value=value,
                    )
                )
                continue
            if looks_like_technical_text(value):
                continue
            if context == "ui":
                severity = "error"
                rule = "hardcoded-user-visible"
                message = "user-visible English text should use a translation key"
            else:
                severity = "warning"
                rule = "possible-user-visible-output"
                message = f"{context} text may be user-visible and needs review"
            issues.append(
                Issue(
                    severity=severity,
                    rule=rule,
                    path=rel_path,
                    line=line,
                    message=message,
                    value=value,
                )
            )
    return issues


def parse_python_file(
    path: Path,
    root: Path,
    issues: list[Issue],
) -> tuple[list[TranslationReference], list[Issue]]:
    rel = relative_path(path, root)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel)
    except (OSError, SyntaxError, UnicodeError) as exc:
        issues.append(
            Issue(
                severity="error",
                rule="source-invalid",
                path=rel,
                line=getattr(exc, "lineno", 1) or 1,
                message=str(exc),
            )
        )
        return [], []
    return translation_references(tree, rel), user_visible_literals(tree, rel)


def _inno_directives(line: str) -> dict[str, str]:
    directives: dict[str, str] = {}
    pattern = re.compile(r"(?:^|;)\s*([A-Za-z][A-Za-z0-9]*)\s*:\s*\"([^\"]*)\"")
    for match in pattern.finditer(line):
        directives[match.group(1).lower()] = match.group(2)
    return directives


def _inno_custom_message_issues(
    messages: Mapping[str, Mapping[str, tuple[int, str]]],
    rel: str,
) -> list[Issue]:
    issues: list[Issue] = []
    english = messages.get("english", {})
    chinese = messages.get("chinesesimplified", {})
    for key in sorted(set(english) - set(chinese)):
        line, _ = english[key]
        issues.append(
            Issue(
                severity="error",
                rule="installer-translation-missing-zh",
                path=rel,
                line=line,
                message="installer custom message has no Simplified Chinese value",
                key=key,
            )
        )
    for key in sorted(set(chinese) - set(english)):
        line, _ = chinese[key]
        issues.append(
            Issue(
                severity="warning",
                rule="installer-translation-extra-zh",
                path=rel,
                line=line,
                message="Simplified Chinese installer message has no English counterpart",
                key=key,
            )
        )
    for key in sorted(set(english) & set(chinese)):
        line, value = chinese[key]
        if not CJK_PATTERN.search(value) and not looks_like_technical_text(value):
            issues.append(
                Issue(
                    severity="error",
                    rule="installer-zh-without-cjk",
                    path=rel,
                    line=line,
                    message="Simplified Chinese installer message has no CJK content",
                    key=key,
                    value=value,
                )
            )
    return issues


def inno_visible_literals(path: Path, root: Path) -> list[Issue]:
    rel = relative_path(path, root)
    issues: list[Issue] = []
    section = ""
    custom_messages: dict[str, dict[str, tuple[int, str]]] = {}
    assignment_pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*=\s*(.*?)\s*$")
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        return [
            Issue(
                severity="error",
                rule="source-invalid",
                path=rel,
                line=1,
                message=str(exc),
            )
        ]

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.lower()
            continue
        if not stripped or stripped.startswith((";", "#")):
            continue

        if section == "[custommessages]":
            match = assignment_pattern.match(line)
            if match and "." in match.group(1):
                locale_name, key = match.group(1).split(".", 1)
                custom_messages.setdefault(locale_name.lower(), {})[key] = (
                    number,
                    match.group(2).strip().strip('"'),
                )
            continue

        visible_names = INNO_VISIBLE_DIRECTIVES.get(section, set())
        for name, value in _inno_directives(line).items():
            if name not in visible_names:
                continue
            if "{cm:" in value.lower() or not english_candidate(value):
                continue
            if looks_like_technical_text(value):
                continue
            issues.append(
                Issue(
                    severity="error",
                    rule="installer-hardcoded-user-visible",
                    path=rel,
                    line=number,
                    message=(
                        "installer page text is hardcoded; use a localized "
                        "CustomMessages entry"
                    ),
                    value=value,
                )
            )

    issues.extend(_inno_custom_message_issues(custom_messages, rel))
    return issues


def read_allowlist(path: Path, root: Path) -> tuple[list[AllowlistEntry], list[Issue]]:
    rel = relative_path(path, root) if path.exists() else path.name
    issues: list[Issue] = []
    if not path.is_file():
        return [], [
            Issue(
                severity="error",
                rule="allowlist-missing",
                path=rel,
                line=1,
                message="allowlist file does not exist",
            )
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        return [], [
            Issue(
                severity="error",
                rule="allowlist-invalid",
                path=rel,
                line=getattr(exc, "lineno", 1) or 1,
                message=str(exc),
            )
        ]

    entries_payload = payload.get("entries") if isinstance(payload, Mapping) else None
    if payload.get("version") != 1 or not isinstance(entries_payload, list):
        return [], [
            Issue(
                severity="error",
                rule="allowlist-invalid",
                path=rel,
                line=1,
                message="allowlist must contain version 1 and an entries array",
            )
        ]

    entries: list[AllowlistEntry] = []
    for index, item in enumerate(entries_payload, 1):
        if not isinstance(item, Mapping):
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist entry must be an object",
                )
            )
            continue
        path_value = str(item.get("path", ""))
        rule = str(item.get("rule", ""))
        category = str(item.get("category", ""))
        reason = str(item.get("reason", ""))
        key = item.get("key")
        value = item.get("value")
        invalid_path = (
            not path_value
            or Path(path_value).is_absolute()
            or ".." in Path(path_value).parts
            or any(token in path_value for token in ("*", "?", "[", "]"))
        )
        if invalid_path:
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist paths must be exact repository-relative paths",
                )
            )
            continue
        if not rule or category not in ALLOWED_CATEGORIES:
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist rule/category is missing or unsupported",
                )
            )
            continue
        if len(reason.strip()) < 12:
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist reason must explain the precise exception",
                )
            )
            continue
        if (key is None) == (value is None):
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist entry must define exactly one of key or value",
                )
            )
            continue
        if value is not None and (value == ".*" or len(str(value)) < 2):
            issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-invalid",
                    path=rel,
                    line=index,
                    message="allowlist value is too broad",
                )
            )
            continue
        entries.append(
            AllowlistEntry(
                path=path_value,
                rule=rule,
                category=category,
                reason=reason.strip(),
                key=str(key) if key is not None else None,
                value=str(value) if value is not None else None,
            )
        )
    return entries, issues


def allowlist_matches(entry: AllowlistEntry, issue: Issue) -> bool:
    if entry.path != issue.path or entry.rule != issue.rule:
        return False
    if entry.key is not None:
        return entry.key == issue.key
    return entry.value == issue.value


def apply_allowlist(
    candidates: list[Issue],
    entries: Sequence[AllowlistEntry],
    allowlist_rel: str,
) -> tuple[list[Issue], list[Issue]]:
    remaining = list(candidates)
    allowlist_issues: list[Issue] = []
    for index, entry in enumerate(entries, 1):
        matches = [issue for issue in remaining if allowlist_matches(entry, issue)]
        if len(matches) != 1:
            message = (
                "allowlist entry no longer matches any finding"
                if not matches
                else "allowlist entry matches more than one finding"
            )
            allowlist_issues.append(
                Issue(
                    severity="error",
                    rule="allowlist-unused" if not matches else "allowlist-broad",
                    path=allowlist_rel,
                    line=index,
                    message=message,
                    key=entry.key,
                    value=entry.value,
                )
            )
            continue
        remaining.remove(matches[0])
        allowlist_issues.append(
            Issue(
                severity="info",
                rule="allowlisted",
                path=entry.path,
                line=matches[0].line,
                message=f"{entry.category}: {entry.reason}",
                key=entry.key,
                value=entry.value,
            )
        )
    return remaining, allowlist_issues


def catalog_issues(
    english: Mapping[str, str],
    chinese: Mapping[str, str],
) -> list[Issue]:
    issues: list[Issue] = []
    english_keys = set(english)
    chinese_keys = set(chinese)
    for key in sorted(english_keys - chinese_keys):
        issues.append(
            Issue(
                severity="error",
                rule="catalog-key-missing",
                path="locales/zh_CN.json",
                line=1,
                message="Simplified Chinese catalog is missing an English key",
                key=key,
            )
        )
    for key in sorted(chinese_keys - english_keys):
        issues.append(
            Issue(
                severity="error",
                rule="catalog-key-extra",
                path="locales/zh_CN.json",
                line=1,
                message="Simplified Chinese catalog contains an extra key",
                key=key,
            )
        )

    for key in sorted(english_keys & chinese_keys):
        english_signature = None
        chinese_signature = None
        try:
            english_signature = placeholder_signature(english[key])
        except ValueError as exc:
            issues.append(
                Issue(
                    severity="error",
                    rule="placeholder-invalid-en",
                    path="locales/en_US.json",
                    line=1,
                    message=f"invalid Python format string: {exc}",
                    key=key,
                )
            )
        try:
            chinese_signature = placeholder_signature(chinese[key])
        except ValueError as exc:
            issues.append(
                Issue(
                    severity="error",
                    rule="placeholder-invalid-zh",
                    path="locales/zh_CN.json",
                    line=1,
                    message=f"invalid Python format string: {exc}",
                    key=key,
                )
            )
        if (
            english_signature is not None
            and chinese_signature is not None
            and english_signature != chinese_signature
        ):
            issues.append(
                Issue(
                    severity="error",
                    rule="placeholder-mismatch",
                    path="locales/zh_CN.json",
                    line=1,
                    message=(
                        "placeholder names, conversions, or format specifications differ: "
                        f"en={english_signature!r}, zh={chinese_signature!r}"
                    ),
                    key=key,
                )
            )
        value = chinese[key]
        if not CJK_PATTERN.search(value) and not looks_like_technical_text(value):
            issues.append(
                Issue(
                    severity="error",
                    rule="zh-entry-without-cjk",
                    path="locales/zh_CN.json",
                    line=1,
                    message="Simplified Chinese entry has no CJK content",
                    key=key,
                    value=value,
                )
            )
    return issues


def reference_issues(
    references: Sequence[TranslationReference],
    english: Mapping[str, str],
    chinese: Mapping[str, str],
) -> tuple[list[Issue], set[str]]:
    issues: list[Issue] = []
    referenced: set[str] = set()
    for reference in references:
        if reference.key is None:
            issues.append(
                Issue(
                    severity="warning",
                    rule="dynamic-translation-key",
                    path=reference.path,
                    line=reference.line,
                    message=f"translation key is not statically known: {reference.expression}",
                )
            )
            continue
        referenced.add(reference.key)
        if reference.key not in english:
            issues.append(
                Issue(
                    severity="error",
                    rule="translation-key-missing-en",
                    path=reference.path,
                    line=reference.line,
                    message="referenced key does not exist in locales/en_US.json",
                    key=reference.key,
                )
            )
        if reference.key not in chinese:
            issues.append(
                Issue(
                    severity="error",
                    rule="translation-key-missing-zh",
                    path=reference.path,
                    line=reference.line,
                    message="referenced key does not exist in locales/zh_CN.json",
                    key=reference.key,
                )
            )
    return issues, referenced


def unused_key_issues(
    english: Mapping[str, str],
    chinese: Mapping[str, str],
    referenced: set[str],
) -> list[Issue]:
    issues: list[Issue] = []
    for key in sorted((set(english) | set(chinese)) - referenced):
        issues.append(
            Issue(
                severity="warning",
                rule="translation-key-unused",
                path="locales/en_US.json",
                line=1,
                message="translation key is defined but not statically referenced",
                key=key,
            )
        )
    return issues


def audit_repository(root: Path, allowlist_path: Path) -> dict[str, Any]:
    root = root.resolve()
    raw_issues: list[Issue] = []
    english = load_catalog(root / "locales" / "en_US.json", root, raw_issues)
    chinese = load_catalog(root / "locales" / "zh_CN.json", root, raw_issues)
    raw_issues.extend(catalog_issues(english, chinese))

    scanned_files = discover_files(root)
    references: list[TranslationReference] = []
    candidate_issues: list[Issue] = []
    for path in scanned_files:
        if path.suffix == ".py":
            file_references, visible_issues = parse_python_file(path, root, raw_issues)
            references.extend(file_references)
            candidate_issues.extend(visible_issues)
        elif path.suffix == ".iss":
            candidate_issues.extend(inno_visible_literals(path, root))

    ref_issues, referenced = reference_issues(references, english, chinese)
    raw_issues.extend(ref_issues)
    raw_issues.extend(unused_key_issues(english, chinese, referenced))

    entries, allowlist_validation = read_allowlist(allowlist_path, root)
    allowlist_rel = (
        relative_path(allowlist_path, root)
        if allowlist_path.exists() and not is_excluded(allowlist_path, root)
        else allowlist_path.name
    )
    allowlist_candidates = [
        issue
        for issue in raw_issues + candidate_issues
        if issue.rule in {
            "hardcoded-user-visible",
            "installer-hardcoded-user-visible",
            "installer-zh-without-cjk",
            "internal-value-in-ui",
            "possible-user-visible-output",
            "zh-entry-without-cjk",
        }
    ]
    non_allowlist_candidates = [
        issue
        for issue in raw_issues + candidate_issues
        if issue not in allowlist_candidates
    ]
    remaining, allowlist_results = apply_allowlist(
        allowlist_candidates,
        entries,
        allowlist_rel,
    )
    all_issues = sorted(
        non_allowlist_candidates
        + remaining
        + allowlist_validation
        + allowlist_results,
        key=Issue.sort_key,
    )
    summary = {
        "errors": sum(issue.severity == "error" for issue in all_issues),
        "warnings": sum(issue.severity == "warning" for issue in all_issues),
        "info": sum(issue.severity == "info" for issue in all_issues),
        "catalog_keys": len(set(english) | set(chinese)),
        "referenced_keys": len(referenced),
        "scanned_files": len(scanned_files),
        "allowlist_entries": len(entries),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "summary": summary,
        "issues": [asdict(issue) for issue in all_issues],
        "scanned_files": [relative_path(path, root) for path in scanned_files],
    }


def render_json(report: Mapping[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def markdown_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Simplified Chinese localization coverage",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Errors | {summary['errors']} |",
        f"| Warnings | {summary['warnings']} |",
        f"| Informational | {summary['info']} |",
        f"| Catalog keys | {summary['catalog_keys']} |",
        f"| Statically referenced keys | {summary['referenced_keys']} |",
        f"| Scanned files | {summary['scanned_files']} |",
        f"| Allowlist entries | {summary['allowlist_entries']} |",
        "",
        "## Findings",
        "",
    ]
    if not report["issues"]:
        lines.append("No findings.")
    else:
        lines.extend(
            [
                "| Severity | Rule | Location | Key/value | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for issue in report["issues"]:
            location = f"{issue['path']}:{issue['line']}"
            detail = issue.get("key") or issue.get("value") or ""
            lines.append(
                "| {severity} | {rule} | {location} | {detail} | {message} |".format(
                    severity=markdown_cell(issue["severity"]),
                    rule=markdown_cell(issue["rule"]),
                    location=markdown_cell(location),
                    detail=markdown_cell(detail),
                    message=markdown_cell(issue["message"]),
                )
            )
    lines.extend(["", "## Scanned files", ""])
    lines.extend(f"- `{path}`" for path in report["scanned_files"])
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--allowlist", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fail-on-errors", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = args.repository_root.resolve()
    allowlist = args.allowlist or root / "tools" / "localization-allowlist.json"
    if not allowlist.is_absolute():
        allowlist = root / allowlist
    report = audit_repository(root, allowlist)
    rendered = render_json(report) if args.format == "json" else render_markdown(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    if args.fail_on_errors and report["summary"]["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
