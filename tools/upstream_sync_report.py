#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Report path-level overlap between an upstream ref and a localization ref."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set


@dataclass(frozen=True)
class ChangedPath:
    status: str
    path: str
    previous_path: Optional[str] = None

    def aliases(self) -> Set[str]:
        paths = {self.path}
        if self.previous_path:
            paths.add(self.previous_path)
        return paths


@dataclass(frozen=True)
class Overlap:
    path: str
    category: str
    risk: str


@dataclass(frozen=True)
class SyncReport:
    repository: str
    upstream_ref: str
    local_ref: str
    merge_base: str
    upstream_changes: List[ChangedPath]
    local_changes: List[ChangedPath]
    overlaps: List[Overlap]

    def to_dict(self) -> Dict[str, object]:
        return {
            "repository": self.repository,
            "upstream_ref": self.upstream_ref,
            "local_ref": self.local_ref,
            "merge_base": self.merge_base,
            "upstream_changes": [asdict(change) for change in self.upstream_changes],
            "local_changes": [asdict(change) for change in self.local_changes],
            "overlaps": [asdict(overlap) for overlap in self.overlaps],
        }


class GitCommandError(RuntimeError):
    """Raised when a required Git command cannot be completed."""


def _run_git(repository: Path, arguments: Sequence[str]) -> str:
    command = ["git", "-C", str(repository), *arguments]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise GitCommandError(f"{' '.join(command)} failed: {detail}")
    return completed.stdout.strip()


def verify_ref(repository: Path, ref: str) -> str:
    return _run_git(repository, ["rev-parse", "--verify", f"{ref}^{{commit}}"]).strip()


def parse_name_status(output: str) -> List[ChangedPath]:
    changes: List[ChangedPath] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split("\t")
        status = fields[0]
        if status.startswith(("R", "C")):
            if len(fields) != 3:
                raise ValueError(f"Unexpected rename/copy record: {raw_line}")
            changes.append(
                ChangedPath(
                    status=status,
                    previous_path=fields[1],
                    path=fields[2],
                )
            )
        else:
            if len(fields) != 2:
                raise ValueError(f"Unexpected name-status record: {raw_line}")
            changes.append(ChangedPath(status=status, path=fields[1]))
    return changes


def collect_changes(repository: Path, base: str, ref: str) -> List[ChangedPath]:
    output = _run_git(repository, ["diff", "--name-status", "-M", f"{base}..{ref}"])
    return parse_name_status(output)


def classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("locales/") or normalized == "library/i18n.py":
        return "catalog-and-i18n"
    if normalized in {"main.py", "configure.py", "theme-editor.py"}:
        return "runtime-and-ui"
    if (
        normalized.endswith(".spec")
        or normalized.startswith(".github/workflows/")
        or normalized.startswith("tools/windows-installer/")
        or normalized in {"library/resources.py", "tools/validate_release_bundle.py"}
    ):
        return "packaging-and-release"
    if normalized.startswith("library/"):
        return "runtime-library"
    if normalized.startswith("res/themes/") or normalized.startswith("res/fonts/"):
        return "themes-and-fonts"
    if normalized.startswith("docs/") or normalized.endswith(".md"):
        return "documentation"
    if normalized.startswith("tests/"):
        return "tests"
    return "other"


def risk_for_category(category: str) -> str:
    if category in {
        "catalog-and-i18n",
        "runtime-and-ui",
        "runtime-library",
        "packaging-and-release",
    }:
        return "high"
    if category in {"themes-and-fonts", "tests"}:
        return "medium"
    return "low"


def _all_aliases(changes: Iterable[ChangedPath]) -> Set[str]:
    aliases: Set[str] = set()
    for change in changes:
        aliases.update(change.aliases())
    return aliases


def build_report(
    repository: Path,
    upstream_ref: str,
    local_ref: str,
    merge_base: Optional[str] = None,
) -> SyncReport:
    root = repository.resolve()
    if not root.is_dir():
        raise GitCommandError(f"Repository directory does not exist: {root}")

    upstream_commit = verify_ref(root, upstream_ref)
    local_commit = verify_ref(root, local_ref)
    base_commit = merge_base
    if base_commit:
        base_commit = verify_ref(root, base_commit)
    else:
        base_commit = _run_git(root, ["merge-base", upstream_commit, local_commit])

    upstream_changes = collect_changes(root, base_commit, upstream_commit)
    local_changes = collect_changes(root, base_commit, local_commit)
    overlap_paths = sorted(
        _all_aliases(upstream_changes).intersection(_all_aliases(local_changes))
    )
    overlaps = []
    for path in overlap_paths:
        category = classify_path(path)
        overlaps.append(
            Overlap(
                path=path,
                category=category,
                risk=risk_for_category(category),
            )
        )

    return SyncReport(
        repository=str(root),
        upstream_ref=upstream_ref,
        local_ref=local_ref,
        merge_base=base_commit,
        upstream_changes=upstream_changes,
        local_changes=local_changes,
        overlaps=overlaps,
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown(report: SyncReport) -> str:
    lines = [
        "# Upstream synchronization report",
        "",
        f"- Repository: `{report.repository}`",
        f"- Upstream ref: `{report.upstream_ref}`",
        f"- Localization ref: `{report.local_ref}`",
        f"- Merge base: `{report.merge_base}`",
        f"- Upstream changed paths: {len(report.upstream_changes)}",
        f"- Localization changed paths: {len(report.local_changes)}",
        f"- Overlapping paths: {len(report.overlaps)}",
        "",
    ]

    if report.overlaps:
        lines.extend(
            [
                "## Paths requiring manual review",
                "",
                "| Risk | Category | Path |",
                "| --- | --- | --- |",
            ]
        )
        for overlap in report.overlaps:
            lines.append(
                "| "
                f"{overlap.risk} | {overlap.category} | "
                f"`{_escape_table(overlap.path)}` |"
            )
    else:
        lines.extend(
            [
                "## Paths requiring manual review",
                "",
                "No path-level overlap was detected.",
            ]
        )

    lines.extend(
        [
            "",
            "> This report detects path overlap, not semantic merge conflicts.",
            "> Review upstream behavior before keeping localization changes.",
            "",
        ]
    )
    return "\n".join(lines)


def render_json(report: SyncReport) -> str:
    return json.dumps(
        report.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path("."))
    parser.add_argument("--upstream-ref", default="upstream/main")
    parser.add_argument("--local-ref", default="HEAD")
    parser.add_argument("--merge-base")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-overlap", action="store_true")
    args = parser.parse_args(argv)

    try:
        report = build_report(
            repository=args.repository,
            upstream_ref=args.upstream_ref,
            local_ref=args.local_ref,
            merge_base=args.merge_base,
        )
    except (GitCommandError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        rendered = render_json(report)
    else:
        rendered = render_markdown(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    if args.fail_on_overlap and report.overlaps:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
