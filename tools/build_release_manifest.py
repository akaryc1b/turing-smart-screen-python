#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate release-candidate artifacts and build a reproducible JSON manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
PROJECT_NAME = "turing-system-monitor"
ARCHIVE_ROOT = PROJECT_NAME

ARTIFACT_KINDS: Mapping[str, Mapping[str, str]] = {
    "windows-release-installer": {
        "platform": "windows",
        "filename": f"{PROJECT_NAME}-{{version}}-windows.exe",
    },
    "windows-release-portable": {
        "platform": "windows",
        "filename": f"{PROJECT_NAME}-{{version}}-portable-windows.zip",
        "archive": "zip",
    },
    "windows-debug-installer": {
        "platform": "windows",
        "filename": f"{PROJECT_NAME}-{{version}}-debug-windows.exe",
    },
    "windows-debug-portable": {
        "platform": "windows",
        "filename": f"{PROJECT_NAME}-{{version}}-debug-portable-windows.zip",
        "archive": "zip",
    },
    "linux-release-archive": {
        "platform": "linux",
        "filename": f"{PROJECT_NAME}-{{version}}-linux.tar.gz",
        "archive": "tar.gz",
    },
}

REQUIRED_ARCHIVE_PATHS: Mapping[str, Tuple[str, ...]] = {
    "windows": (
        "configure.exe",
        "main.exe",
        "theme-editor.exe",
        "version.txt",
        "locales/en_US.json",
        "locales/zh_CN.json",
        "res/themes/3.5inchTheme2-zh-CN/theme.yaml",
    ),
    "linux": (
        "configure",
        "main",
        "theme-editor",
        "turing-smart-screen",
        "version.txt",
        "locales/en_US.json",
        "locales/zh_CN.json",
        "res/themes/3.5inchTheme2-zh-CN/theme.yaml",
    ),
}

FORBIDDEN_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
    "build",
    "dist",
    "tmp",
    "temp",
    "logs",
    "--theme examples",
}
FORBIDDEN_SUFFIXES = {".isl", ".log", ".pyc", ".pyo"}


class ReleaseManifestError(RuntimeError):
    """Raised when release-candidate metadata or artifacts are invalid."""


def validate_version(version: str) -> str:
    normalized = version.strip()
    if not VERSION_PATTERN.fullmatch(normalized):
        raise ReleaseManifestError(
            f"Version must use numeric major.minor.patch form, got: {version!r}"
        )
    return normalized


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _flatten_catalog(values: Mapping[str, Any], prefix: str = "") -> Dict[str, str]:
    flattened: Dict[str, str] = {}
    for key, value in values.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_catalog(value, full_key))
        elif isinstance(value, str):
            flattened[full_key] = value
        else:
            raise ReleaseManifestError(
                f"Translation value for {full_key!r} must be a string"
            )
    return flattened


def _catalog_metadata(path: Path) -> Dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"Invalid translation catalog {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ReleaseManifestError(f"Translation catalog root must be an object: {path}")
    flattened = _flatten_catalog(raw)
    return {
        "filename": path.name,
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "key_count": len(flattened),
        "contains_cjk": any(CJK_PATTERN.search(value) for value in flattened.values()),
    }


def _theme_metadata(path: Path) -> Dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReleaseManifestError(f"Invalid theme YAML {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ReleaseManifestError(f"Theme root must be a mapping: {path}")

    display = raw.get("display", {})
    static_text = raw.get("static_text", {})
    if not isinstance(display, Mapping) or not isinstance(static_text, Mapping):
        raise ReleaseManifestError(f"Theme display/static_text sections are invalid: {path}")

    cjk_labels = 0
    for value in static_text.values():
        if isinstance(value, Mapping) and CJK_PATTERN.search(str(value.get("TEXT", ""))):
            cjk_labels += 1

    assets: Dict[str, Dict[str, Any]] = {}
    for filename in ("background.png", "preview.png"):
        asset = path.parent / filename
        if asset.is_file():
            assets[filename] = {
                "sha256": _sha256(asset),
                "size_bytes": asset.stat().st_size,
            }

    return {
        "path": "res/themes/3.5inchTheme2-zh-CN/theme.yaml",
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "display_size": display.get("DISPLAY_SIZE"),
        "display_orientation": display.get("DISPLAY_ORIENTATION"),
        "cjk_label_count": cjk_labels,
        "assets": assets,
    }


def _validate_member_name(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/").rstrip("/")
    if not normalized:
        return PurePosixPath(".")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ReleaseManifestError(f"Unsafe archive member path: {name}")
    lowered_parts = {part.casefold() for part in path.parts}
    forbidden = lowered_parts & FORBIDDEN_PATH_PARTS
    if forbidden:
        raise ReleaseManifestError(
            f"Forbidden archive path component {sorted(forbidden)} in {name}"
        )
    if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
        raise ReleaseManifestError(f"Forbidden archive file type in {name}")
    return path


def _validate_link_target(member_name: str, link_target: str) -> None:
    target = PurePosixPath(link_target.replace("\\", "/"))
    if target.is_absolute() or ".." in target.parts:
        raise ReleaseManifestError(
            f"Unsafe archive link target {link_target!r} for {member_name}"
        )


def _archive_members(path: Path, archive_type: str) -> List[PurePosixPath]:
    members: List[PurePosixPath] = []
    if archive_type == "zip":
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    member = _validate_member_name(info.filename)
                    if member != PurePosixPath("."):
                        members.append(member)
        except (OSError, zipfile.BadZipFile) as exc:
            raise ReleaseManifestError(f"Invalid ZIP archive {path}: {exc}") from exc
    elif archive_type == "tar.gz":
        try:
            with tarfile.open(path, mode="r:gz") as archive:
                for info in archive.getmembers():
                    if info.ischr() or info.isblk() or info.isfifo():
                        raise ReleaseManifestError(
                            f"Unsupported special file in archive: {info.name}"
                        )
                    member = _validate_member_name(info.name)
                    if info.issym() or info.islnk():
                        _validate_link_target(info.name, info.linkname)
                    if member != PurePosixPath("."):
                        members.append(member)
        except (OSError, tarfile.TarError) as exc:
            raise ReleaseManifestError(f"Invalid TAR.GZ archive {path}: {exc}") from exc
    else:
        raise ReleaseManifestError(f"Unsupported archive type: {archive_type}")
    return members


def _validate_archive(path: Path, archive_type: str, platform_name: str) -> Dict[str, Any]:
    members = _archive_members(path, archive_type)
    if not members:
        raise ReleaseManifestError(f"Archive contains no members: {path}")

    roots = {member.parts[0] for member in members if member.parts}
    if roots != {ARCHIVE_ROOT}:
        raise ReleaseManifestError(
            f"Archive must contain exactly one top-level {ARCHIVE_ROOT!r} directory; "
            f"found {sorted(roots)}"
        )

    relative_members = {
        PurePosixPath(*member.parts[1:]).as_posix()
        for member in members
        if len(member.parts) > 1
    }
    missing = [
        required
        for required in REQUIRED_ARCHIVE_PATHS[platform_name]
        if required not in relative_members
    ]
    if missing:
        raise ReleaseManifestError(f"Archive is missing required packaged paths: {missing}")

    return {
        "format": archive_type,
        "root": ARCHIVE_ROOT,
        "member_count": len(members),
    }


def build_entry(
    artifact: Path,
    kind: str,
    version: str,
    commit: str,
    python_version: str,
    catalog_dir: Path,
    theme_path: Path,
) -> Dict[str, Any]:
    version = validate_version(version)
    if kind not in ARTIFACT_KINDS:
        raise ReleaseManifestError(f"Unsupported artifact kind: {kind}")
    if not SHA_PATTERN.fullmatch(commit.strip().lower()):
        raise ReleaseManifestError(f"Commit must be a full 40-character lowercase SHA: {commit}")

    path = artifact.resolve()
    if not path.is_file():
        raise ReleaseManifestError(f"Artifact does not exist: {path}")
    if path.stat().st_size <= 0:
        raise ReleaseManifestError(f"Artifact is empty: {path}")

    contract = ARTIFACT_KINDS[kind]
    expected_name = contract["filename"].format(version=version)
    if path.name != expected_name:
        raise ReleaseManifestError(
            f"Artifact filename mismatch for {kind}: expected {expected_name}, got {path.name}"
        )

    platform_name = contract["platform"]
    artifact_metadata: Dict[str, Any] = {
        "kind": kind,
        "filename": path.name,
        "platform": platform_name,
        "python_version": python_version.strip(),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }
    archive_type = contract.get("archive")
    if archive_type:
        artifact_metadata["archive"] = _validate_archive(
            path, archive_type, platform_name
        )

    catalogs = {
        locale: _catalog_metadata(catalog_dir / f"{locale}.json")
        for locale in ("en_US", "zh_CN")
    }
    if not catalogs["zh_CN"]["contains_cjk"]:
        raise ReleaseManifestError("zh_CN catalog metadata does not contain CJK text")

    return {
        "schema_version": 1,
        "project": PROJECT_NAME,
        "version": version,
        "commit": commit.strip().lower(),
        "artifact": artifact_metadata,
        "catalogs": catalogs,
        "theme": _theme_metadata(theme_path),
    }


def _load_metadata(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseManifestError(f"Invalid metadata file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleaseManifestError(f"Metadata root must be an object: {path}")
    return data


def _find_artifact(root: Path, filename: str) -> Path:
    matches = [path for path in root.rglob(filename) if path.is_file()]
    if len(matches) != 1:
        raise ReleaseManifestError(
            f"Expected exactly one downloaded artifact named {filename}, found {len(matches)}"
        )
    return matches[0]


def combine_metadata(metadata_paths: Iterable[Path], artifacts_root: Path) -> Dict[str, Any]:
    paths = list(metadata_paths)
    if not paths:
        raise ReleaseManifestError("At least one metadata file is required")

    entries = [_load_metadata(path) for path in paths]
    first = entries[0]
    shared_keys = ("schema_version", "project", "version", "commit", "catalogs", "theme")
    for entry in entries[1:]:
        for key in shared_keys:
            if entry.get(key) != first.get(key):
                raise ReleaseManifestError(f"Metadata files disagree on {key}")

    artifacts = [entry.get("artifact") for entry in entries]
    if not all(isinstance(artifact, dict) for artifact in artifacts):
        raise ReleaseManifestError("Every metadata file must contain an artifact object")

    kinds = [artifact["kind"] for artifact in artifacts]
    expected_kinds = set(ARTIFACT_KINDS)
    if set(kinds) != expected_kinds or len(kinds) != len(expected_kinds):
        raise ReleaseManifestError(
            f"Artifact kinds must be exactly {sorted(expected_kinds)}, got {sorted(kinds)}"
        )

    filenames = [artifact["filename"] for artifact in artifacts]
    if len(filenames) != len(set(filenames)):
        raise ReleaseManifestError("Artifact filenames must be unique")

    root = artifacts_root.resolve()
    if not root.is_dir():
        raise ReleaseManifestError(f"Downloaded artifact root does not exist: {root}")
    for artifact in artifacts:
        downloaded = _find_artifact(root, artifact["filename"])
        if downloaded.stat().st_size != artifact["size_bytes"]:
            raise ReleaseManifestError(f"Size mismatch for downloaded artifact: {downloaded}")
        if _sha256(downloaded) != artifact["sha256"]:
            raise ReleaseManifestError(f"SHA-256 mismatch for downloaded artifact: {downloaded}")

    return {
        "schema_version": first["schema_version"],
        "project": first["project"],
        "version": first["version"],
        "commit": first["commit"],
        "artifacts": sorted(artifacts, key=lambda item: item["kind"]),
        "catalogs": first["catalogs"],
        "theme": first["theme"],
    }


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("validate-version")
    version_parser.add_argument("version")

    entry_parser = subparsers.add_parser("entry")
    entry_parser.add_argument("--artifact", type=Path, required=True)
    entry_parser.add_argument("--kind", choices=sorted(ARTIFACT_KINDS), required=True)
    entry_parser.add_argument("--version", required=True)
    entry_parser.add_argument("--commit", required=True)
    entry_parser.add_argument("--python-version", required=True)
    entry_parser.add_argument("--catalog-dir", type=Path, required=True)
    entry_parser.add_argument("--theme", type=Path, required=True)
    entry_parser.add_argument("--output", type=Path, required=True)

    combine_parser = subparsers.add_parser("combine")
    combine_parser.add_argument("metadata", nargs="+", type=Path)
    combine_parser.add_argument("--artifacts-root", type=Path, required=True)
    combine_parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-version":
            print(validate_version(args.version))
        elif args.command == "entry":
            data = build_entry(
                artifact=args.artifact,
                kind=args.kind,
                version=args.version,
                commit=args.commit,
                python_version=args.python_version,
                catalog_dir=args.catalog_dir,
                theme_path=args.theme,
            )
            _write_json(args.output, data)
            print(f"Wrote release artifact metadata: {args.output.resolve()}")
        else:
            data = combine_metadata(args.metadata, args.artifacts_root)
            _write_json(args.output, data)
            print(f"Wrote release manifest: {args.output.resolve()}")
    except ReleaseManifestError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
