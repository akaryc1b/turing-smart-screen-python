#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate a complete localized release candidate before publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

PROJECT_NAME = "turing-system-monitor"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ReleaseSetError(RuntimeError):
    """Raised when a localized release set is incomplete or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_filenames(version: str) -> set[str]:
    return {
        f"{PROJECT_NAME}-{version}-windows.exe",
        f"{PROJECT_NAME}-{version}-portable-windows.zip",
        f"{PROJECT_NAME}-{version}-debug-windows.exe",
        f"{PROJECT_NAME}-{version}-debug-portable-windows.zip",
        f"{PROJECT_NAME}-{version}-linux.tar.gz",
        "release-manifest.json",
    }


def _load_manifest(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSetError(f"Invalid release manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleaseSetError("Release manifest root must be an object")
    return data


def validate_release_set(root: Path, version: str, commit: str) -> Dict[str, Any]:
    version = version.strip()
    commit = commit.strip().lower()
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseSetError(f"Invalid release version: {version!r}")
    if not SHA_PATTERN.fullmatch(commit):
        raise ReleaseSetError(f"Invalid release commit: {commit!r}")

    directory = root.resolve()
    if not directory.is_dir():
        raise ReleaseSetError(f"Release candidate directory does not exist: {directory}")

    actual_files = {path.name for path in directory.iterdir() if path.is_file()}
    expected_files = expected_filenames(version)
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        unexpected = sorted(actual_files - expected_files)
        raise ReleaseSetError(
            f"Release candidate files do not match contract; missing={missing}, "
            f"unexpected={unexpected}"
        )

    manifest = _load_manifest(directory / "release-manifest.json")
    if manifest.get("schema_version") != 1:
        raise ReleaseSetError("Release manifest schema_version must be 1")
    if manifest.get("project") != PROJECT_NAME:
        raise ReleaseSetError(f"Unexpected project in manifest: {manifest.get('project')!r}")
    if manifest.get("version") != version:
        raise ReleaseSetError(
            f"Release manifest version mismatch: expected {version!r}, "
            f"got {manifest.get('version')!r}"
        )
    if manifest.get("commit") != commit:
        raise ReleaseSetError(
            f"Release manifest commit mismatch: expected {commit!r}, "
            f"got {manifest.get('commit')!r}"
        )

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 5:
        raise ReleaseSetError("Release manifest must contain exactly five artifacts")

    artifact_names: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            raise ReleaseSetError("Every release artifact entry must be an object")
        filename = artifact.get("filename")
        if not isinstance(filename, str):
            raise ReleaseSetError("Every release artifact must have a filename")
        if filename in artifact_names:
            raise ReleaseSetError(f"Duplicate artifact filename in manifest: {filename}")
        artifact_names.add(filename)

        path = directory / filename
        if not path.is_file():
            raise ReleaseSetError(f"Manifest artifact is missing: {filename}")
        if path.stat().st_size != artifact.get("size_bytes"):
            raise ReleaseSetError(f"Size mismatch for release artifact: {filename}")
        if _sha256(path) != artifact.get("sha256"):
            raise ReleaseSetError(f"SHA-256 mismatch for release artifact: {filename}")

    expected_artifacts = expected_files - {"release-manifest.json"}
    if artifact_names != expected_artifacts:
        raise ReleaseSetError(
            "Manifest artifact filenames do not match the localized release contract"
        )

    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--commit", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        manifest = validate_release_set(args.root, args.version, args.commit)
    except ReleaseSetError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"Validated {len(manifest['artifacts'])} localized release artifacts "
        f"for {manifest['version']} at {manifest['commit']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
