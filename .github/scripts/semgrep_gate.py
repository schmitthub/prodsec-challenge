"""Semgrep severity gate shared by CI (security.yml) and the pre-commit hooks.

Blocks on ERROR (classic INFO/WARNING/ERROR scale) plus HIGH and CRITICAL
(the CRITICAL/HIGH/MEDIUM/LOW scale rules may use since semgrep 1.72); every
other severity is advisory. semgrep itself cannot express this policy:
`--severity` only accepts INFO/WARNING/ERROR and drops HIGH/CRITICAL rules,
and `semgrep ci` blocks on per-rule `dev.semgrep.actions` metadata, not
severity. So the policy lives here, once, for both consumers.

Usage:
  semgrep_gate.py --report semgrep.json         gate an existing JSON report (CI)
  semgrep_gate.py <semgrep scan args> [files]   test rule fixtures, run semgrep,
                                                then gate (pre-commit)

Exit 1 when a blocking finding exists, 0 otherwise; semgrep's own non-zero
exit (bad config, crash, failing rule fixture) is passed through.
"""

import json
import os
import subprocess  # nosec B404 - runs semgrep as an argv list, never a shell
import sys
import tempfile
from pathlib import Path

RULES_DIR = Path(".semgrep")

BLOCKING = {"ERROR", "CRITICAL", "HIGH"}
LEVEL = {
    "ERROR": "error",
    "CRITICAL": "error",
    "HIGH": "error",
    "WARNING": "warning",
    "MEDIUM": "warning",
    "INFO": "notice",
    "LOW": "notice",
}


def test_rules() -> None:
    """`semgrep --test` every .semgrep/<name>.yaml against its sibling fixture
    (`.semgrep/<name>.<ext>`, any extension but yaml). Rule files without a
    fixture are skipped. Paths are passed absolute: semgrep 1.175 raises
    IndexError in --test when config and target are relative to the cwd."""
    for rules in sorted(RULES_DIR.glob("*.yaml")):
        for fixture in sorted(RULES_DIR.glob(f"{rules.stem}.*")):
            if fixture.suffix in {".yaml", ".yml"}:
                continue
            cmd = [
                "semgrep",
                "--test",
                "--metrics=off",
                "--disable-version-check",
                "--config",
                str(rules.resolve()),
                str(fixture.resolve()),
            ]
            rc = subprocess.run(cmd, check=False).returncode  # nosec B603 - fixed argv, no shell
            if rc != 0:
                print(f"rule fixture failed: {rules} vs {fixture}")
                sys.exit(rc)


def run_semgrep(args: list[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    cmd = [
        "semgrep",
        "scan",
        "--json-output",
        path,
        "--quiet",
        "--metrics=off",
        "--disable-version-check",
        *args,
    ]
    rc = subprocess.run(cmd, check=False).returncode  # nosec B603 - fixed argv, no shell
    if (
        rc != 0
    ):  # without --error semgrep exits 0 on findings, so this is a real failure
        sys.exit(rc)
    return path


def gate(report: str) -> int:
    with open(report) as f:
        results = json.load(f)["results"]
    on_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    blocking = 0
    for r in results:
        sev = r["extra"]["severity"]
        msg = r["extra"]["message"].strip().splitlines()[0]
        path, line = r["path"], r["start"]["line"]
        if on_actions:
            print(
                f"::{LEVEL.get(sev, 'notice')} file={path},line={line},title={r['check_id']}::{msg}"
            )
        else:
            print(f"{path}:{line}  {sev:<8} {r['check_id']}\n    {msg}")
        blocking += sev in BLOCKING
    if results or on_actions:
        print(
            f"{len(results)} finding(s); {blocking} blocking ({'/'.join(sorted(BLOCKING))})"
        )
    if blocking:
        print(
            ("::error::" if on_actions else "")
            + "Blocking Semgrep findings. Lower severities are advisory. "
            "Justify a true false positive with an inline `# nosemgrep: <rule-id>` comment."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["--report"]:
        return gate(argv[1])
    test_rules()
    return gate(run_semgrep(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
