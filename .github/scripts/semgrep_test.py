"""Run semgrep's rule fixtures for every custom rule file under .semgrep/.

A rule file `.semgrep/<name>.yaml` is tested against its sibling fixture
`.semgrep/<name>.<ext>` (any extension but yaml). Rule files without a fixture
are skipped. Paths are passed absolute: semgrep 1.175 raises IndexError in
`--test` when the config and target are given relative to the cwd.

Usage: semgrep_test.py            (pre-commit hook; exits non-zero on any failure)
"""

import subprocess  # nosec B404 - runs semgrep as an argv list, never a shell
import sys
from pathlib import Path

RULES_DIR = Path(".semgrep").resolve()


def fixtures() -> list[tuple[Path, Path]]:
    pairs = []
    for rules in sorted(RULES_DIR.glob("*.yaml")):
        for fixture in sorted(RULES_DIR.glob(f"{rules.stem}.*")):
            if fixture.suffix not in {".yaml", ".yml"}:
                pairs.append((rules, fixture))
    return pairs


def main() -> int:
    pairs = fixtures()
    if not pairs:
        print("no semgrep rule fixtures found under .semgrep/")
        return 0
    failed = 0
    for rules, fixture in pairs:
        print(f"semgrep --test {rules.name} against {fixture.name}")
        cmd = [
            "semgrep",
            "--test",
            "--metrics=off",
            "--disable-version-check",
            "--config",
            str(rules),
            str(fixture),
        ]
        rc = subprocess.run(cmd, check=False).returncode  # nosec B603 - fixed argv
        failed += rc != 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
