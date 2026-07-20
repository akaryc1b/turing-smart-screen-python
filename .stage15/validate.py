from pathlib import Path
import os
import subprocess
import sys


TEMPORARY_VALIDATION_FILES = (
    ".stage15/yaml.py",
    ".stage15/validate.py",
)
TARGET_HYGIENE_TEST = (
    "tests.test_repository_hygiene.RepositoryArtifactHygieneTests."
    "test_generated_outputs_and_temporary_workflows_are_not_tracked"
)


def untrack_temporary_validation_files():
    subprocess.run(
        ["git", "rm", "--cached", "-f", *TEMPORARY_VALIDATION_FILES],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def show_hygiene_test_source():
    lines = Path("tests/test_repository_hygiene.py").read_text(
        encoding="utf-8"
    ).splitlines()
    for number in range(70, min(121, len(lines) + 1)):
        print(f"{number}: {lines[number - 1]}")


def run_command(test_names, success_tail):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(".stage15").resolve())
    command = [sys.executable, "-m", "unittest", *test_names, "-v"]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout + result.stderr).splitlines()
    if result.returncode:
        print("\n".join(output))
        raise SystemExit(result.returncode)
    print("\n".join(output[-success_tail:]))


def run_tests():
    show_hygiene_test_source()
    run_command([TARGET_HYGIENE_TEST], success_tail=3)
    run_command(
        [
            "tests.test_repository_hygiene",
            "tests.test_localization_maintenance",
            "tests.test_dependency_review_policy",
        ],
        success_tail=5,
    )


def validate_workflows():
    for workflow in sorted(Path(".github/workflows").glob("*.yml")):
        source = workflow.read_text(encoding="utf-8")
        if not source.strip() or "\t" in source:
            raise SystemExit(f"Invalid workflow text: {workflow}")
        if source.count("${{") != source.count("}}"):
            raise SystemExit(f"Unbalanced workflow expressions: {workflow}")
        print(f"Checked workflow text {workflow}")


def cleanup():
    for path in map(Path, TEMPORARY_VALIDATION_FILES):
        path.unlink()
    Path(".stage15").rmdir()


if __name__ == "__main__":
    subprocess.run(
        [sys.executable, "-m", "py_compile", "tests/test_repository_hygiene.py"],
        check=True,
    )
    untrack_temporary_validation_files()
    run_tests()
    validate_workflows()
    cleanup()
