#!/usr/bin/env python
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch a frozen smoke executable with isolation, timeout, and cleanup."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from PIL import Image

EXPECTED_SIZE = (320, 480)
CJK_FIELDS = (
    ("configuration_ui", "title"),
    ("configuration_ui", "display_section"),
    ("configuration_ui", "hardware"),
    ("theme_editor_ui", "title"),
    ("theme_editor_ui", "coordinate_hint"),
)


class FrozenSmokeRunnerError(RuntimeError):
    """Raised when the frozen child process or its artifacts are invalid."""


def isolated_environment(root: Path) -> Mapping[str, str]:
    env = os.environ.copy()
    home = root / "home"
    temp = root / "temp"
    config = root / "config"
    for directory in (home, temp, config):
        directory.mkdir(parents=True, exist_ok=True)

    env.update(
        {
            "TURING_LANGUAGE": "zh_CN",
            "HOME": str(home),
            "USERPROFILE": str(home),
            "XDG_CONFIG_HOME": str(config),
            "TMPDIR": str(temp),
            "TMP": str(temp),
            "TEMP": str(temp),
            "PYTHONUTF8": "1",
        }
    )
    return env


def _text_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _write_diagnostic(
    artifacts_dir: Path,
    reason: str,
    stdout: Any = "",
    stderr: Any = "",
    returncode: Optional[int] = None,
) -> None:
    diagnostic = {
        "schema_version": 1,
        "reason": reason,
        "returncode": returncode,
        "stdout": _text_output(stdout),
        "stderr": _text_output(stderr),
    }
    path = artifacts_dir / "frozen-smoke-diagnostic.json"
    path.write_text(
        json.dumps(diagnostic, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_report(report: Mapping[str, Any], screenshot: Path) -> None:
    if report.get("schema_version") != 1:
        raise FrozenSmokeRunnerError("Unexpected frozen smoke report schema")
    if report.get("frozen") is not True or report.get("meipass_detected") is not True:
        raise FrozenSmokeRunnerError("Smoke report did not prove a PyInstaller run")
    if report.get("resource_root_matches") is not True:
        raise FrozenSmokeRunnerError("Smoke report resource root does not match _MEIPASS")
    if report.get("language") != "zh_CN":
        raise FrozenSmokeRunnerError("Smoke report language is not zh_CN")

    simulation = report.get("simulation", {})
    expected_simulation = {
        "revision": "SIMU",
        "hardware": "STATIC",
        "theme": "3.5inchTheme2-zh-CN",
        "size": [320, 480],
    }
    for key, expected in expected_simulation.items():
        if simulation.get(key) != expected:
            raise FrozenSmokeRunnerError(
                f"Unexpected simulation field {key}: {simulation.get(key)!r}"
            )
    if int(simulation.get("cjk_label_count", 0)) <= 0:
        raise FrozenSmokeRunnerError("Smoke report contains no CJK theme labels")

    font = report.get("font", {})
    if font.get("mode") not in {"system", "fallback"}:
        raise FrozenSmokeRunnerError("Smoke report font mode is invalid")
    if font.get("mode") == "fallback" and not font.get("notice"):
        raise FrozenSmokeRunnerError("Fallback font mode did not emit a notice")

    for section, field in CJK_FIELDS:
        value = str(report.get(section, {}).get(field, ""))
        if not any("\u3400" <= char <= "\u9fff" for char in value):
            raise FrozenSmokeRunnerError(
                f"Smoke report field {section}.{field} is not Simplified Chinese"
            )

    if not screenshot.is_file() or screenshot.stat().st_size <= 0:
        raise FrozenSmokeRunnerError("Frozen smoke screenshot is missing")
    with Image.open(screenshot) as image:
        if image.size != EXPECTED_SIZE:
            raise FrozenSmokeRunnerError(
                f"Unexpected screenshot size: {image.size}, expected {EXPECTED_SIZE}"
            )
        extrema = image.convert("RGB").getextrema()
        if all(low == high for low, high in extrema):
            raise FrozenSmokeRunnerError("Frozen smoke screenshot is blank")


def run_frozen_smoke(
    executable: Path,
    artifacts_dir: Path,
    timeout_seconds: int,
) -> None:
    executable = executable.resolve()
    if not executable.is_file():
        raise FrozenSmokeRunnerError(f"Frozen executable does not exist: {executable}")
    if timeout_seconds <= 0:
        raise FrozenSmokeRunnerError("Timeout must be positive")

    artifacts_dir = artifacts_dir.resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    final_screenshot = artifacts_dir / "frozen-smoke.png"
    final_report = artifacts_dir / "frozen-smoke-report.json"
    final_diagnostic = artifacts_dir / "frozen-smoke-diagnostic.json"
    for path in (final_screenshot, final_report, final_diagnostic):
        if path.exists():
            path.unlink()

    with tempfile.TemporaryDirectory(prefix="turing-frozen-smoke-") as temp_name:
        root = Path(temp_name)
        staged_screenshot = root / "output" / "frozen-smoke.png"
        staged_report = root / "output" / "frozen-smoke-report.json"
        staged_screenshot.parent.mkdir(parents=True)

        command = [
            str(executable),
            "--output",
            str(staged_screenshot),
            "--report",
            str(staged_report),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                env=isolated_environment(root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            _write_diagnostic(
                artifacts_dir,
                reason="timeout",
                stdout=exc.stdout,
                stderr=exc.stderr,
            )
            raise FrozenSmokeRunnerError(
                f"Frozen smoke exceeded {timeout_seconds} seconds and was terminated"
            ) from exc

        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=os.sys.stderr)
        if completed.returncode != 0:
            _write_diagnostic(
                artifacts_dir,
                reason="nonzero-exit",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
            raise FrozenSmokeRunnerError(
                f"Frozen smoke exited with code {completed.returncode}"
            )

        try:
            report = json.loads(staged_report.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            _write_diagnostic(
                artifacts_dir,
                reason="invalid-report",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
            raise FrozenSmokeRunnerError("Frozen smoke report is invalid") from exc
        if not isinstance(report, dict):
            _write_diagnostic(
                artifacts_dir,
                reason="non-object-report",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
            raise FrozenSmokeRunnerError("Frozen smoke report root is not an object")

        try:
            validate_report(report, staged_screenshot)
        except FrozenSmokeRunnerError:
            _write_diagnostic(
                artifacts_dir,
                reason="report-validation",
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
            )
            raise
        shutil.copy2(staged_screenshot, final_screenshot)
        shutil.copy2(staged_report, final_report)

    validate_report(
        json.loads(final_report.read_text(encoding="utf-8")),
        final_screenshot,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        run_frozen_smoke(
            executable=args.executable,
            artifacts_dir=args.artifacts_dir,
            timeout_seconds=args.timeout_seconds,
        )
    except FrozenSmokeRunnerError as exc:
        print(f"[frozen-smoke-runner] {exc}", file=os.sys.stderr)
        return 1
    print("[frozen-smoke-runner] Frozen Simplified Chinese smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
