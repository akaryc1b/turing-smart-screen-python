from pathlib import Path
import os
import subprocess
import sys


def run_tests():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(".stage15").resolve())
    command = [
        sys.executable,
        "-m",
        "unittest",
        "tests.test_repository_hygiene",
        "tests.test_localization_maintenance",
        "tests.test_dependency_review_policy",
        "-v",
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout + result.stderr).splitlines()
    print("\n".join(output[-60:]))
    if result.returncode:
        raise SystemExit(result.returncode)


def validate_workflows():
    for workflow in sorted(Path(".github/workflows").glob("*.yml")):
        source = workflow.read_text(encoding="utf-8")
        if not source.strip() or "\t" in source:
            raise SystemExit(f"Invalid workflow text: {workflow}")
        if source.count("${{") != source.count("}}"):
            raise SystemExit(f"Unbalanced workflow expressions: {workflow}")
        print(f"Checked workflow text {workflow}")


def cleanup():
    for path in (Path(".stage15/yaml.py"), Path(".stage15/validate.py")):
        path.unlink()
    Path(".stage15").rmdir()


if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "py_compile", "tests/test_repository_hygiene.py"],
        check=True,
    )
    run_tests()
    validate_workflows()
    cleanup()
