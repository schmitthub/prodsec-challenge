"""Prove the configured linters reject representative weak patterns."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG = PROJECT_ROOT / "pyproject.toml"


@pytest.mark.parametrize("narrowed", [False, True])
def test_mypy_checks_mutable_policy_overrides(tmp_path: Path, narrowed: bool) -> None:
    annotation = "Callable[..., object]" if narrowed else "Principal"
    source = tmp_path / "policy_probe.py"
    source.write_text(
        "from collections.abc import Callable\n"
        "from typing import ClassVar\n"
        "from app.authz import Policy, Principal\n"
        "def identify() -> object:\n"
        "    return object()\n"
        "class ExamplePolicy(Policy):\n"
        f"    principal: ClassVar[{annotation}] = staticmethod(identify)\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(CONFIG),
            "--cache-dir",
            str(tmp_path / "mypy-cache"),
            str(source),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if narrowed:
        assert result.returncode == 1, result.stdout + result.stderr
        assert "[mutable-override]" in result.stdout
    else:
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("def untyped(value):\n    return value\n", "ANN001"),
        ("from typing import Any\ndef weak() -> Any:\n    return 1\n", "ANN401"),
        ("value = 1  # type: ignore\n", "PGH003"),
        ("value = 1  # noqa\n", "PGH004"),
        ("value = 1  # noqa: F821\n", "RUF100"),
        ("class Shared:\n    values = []\n", "RUF012"),
        (
            (
                "def load() -> dict[str, int]:\n    return {}\n"
                "def eager(value: dict[str, int] = load()) -> dict[str, int]:\n    return value\n"
            ),
            "B008",
        ),
    ],
)
def test_ruff_rejects_weak_patterns(source: str, rule: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(CONFIG),
            "--output-format",
            "json",
            "--stdin-filename",
            "app/lint_probe.py",
            "-",
        ],
        cwd=PROJECT_ROOT,
        input=source,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert rule in {diagnostic["code"] for diagnostic in json.loads(result.stdout)}
