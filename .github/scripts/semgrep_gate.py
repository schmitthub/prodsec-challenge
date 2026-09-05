"""Semgrep severity gate shared by CI (security.yml) and the pre-commit hooks.

Blocks on ERROR (classic INFO/WARNING/ERROR scale) plus HIGH and CRITICAL
(the CRITICAL/HIGH/MEDIUM/LOW scale rules may use since semgrep 1.72); every
other severity is advisory. semgrep itself cannot express this policy:
`--severity` only accepts INFO/WARNING/ERROR and drops HIGH/CRITICAL rules,
and `semgrep ci` blocks on per-rule `dev.semgrep.actions` metadata, not
severity. So the policy lives here, once, for both consumers.

Usage:
  semgrep_gate.py --contracts                  full contract scan + exception audit
  semgrep_gate.py --report semgrep.json         gate an existing JSON report (CI)
  semgrep_gate.py <semgrep scan args> [files]   test rule fixtures, run semgrep,
                                                then gate (pre-commit)

Exit 1 when a blocking finding exists, 0 otherwise; semgrep's own non-zero
exit (bad config, crash, failing rule fixture) is passed through.
"""

import json
import os
import re
import subprocess  # nosec B404 - runs semgrep as an argv list, never a shell
import sys
import tempfile
import tokenize
from pathlib import Path

RULES_DIR = Path(".semgrep")
CONTRACT_RULES = RULES_DIR / "fastapi-access-control.yaml"

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
            "Document intentional exceptions or false positives with a justification and a rule-specific nosemgrep comment."
        )
        return 1
    return 0


def audit_suppressions(root: Path = Path("app")) -> int:
    """Reject blanket/unjustified suppressions and keep accepted ones visible.

    Read Python comments, not strings. An adjacent preceding comment explains
    the exception; only explicit rule IDs may be suppressed. This audit runs
    independently of Semgrep so a suppression cannot suppress its own audit.
    """
    errors = 0
    for path in sorted(root.rglob("*.py")):
        lines = path.read_text().splitlines()
        with tokenize.open(path) as source:
            comments = [
                t
                for t in tokenize.generate_tokens(source.readline)
                if t.type == tokenize.COMMENT
            ]
        for comment in comments:
            if "nosemgrep" not in comment.string:
                continue
            match = re.fullmatch(
                r"#\s*nosemgrep:\s*([\w.-]+(?:\s*,\s*[\w.-]+)*)\s*", comment.string
            )
            previous = (
                lines[comment.start[0] - 2].strip() if comment.start[0] > 1 else ""
            )
            justified = (
                previous.startswith("#")
                and len(previous.lstrip("# ")) >= 12
                and "nosemgrep" not in previous
            )
            if not match or not justified:
                print(
                    f"{path}:{comment.start[0]}: suppression requires explicit rule IDs and a preceding justification comment"
                )
                errors += 1
            else:
                print(
                    f"reviewed exception: {path}:{comment.start[0]} [{match[1]}] {previous.lstrip('# ')}"
                )
    return int(errors > 0)


def contract_gate() -> int:
    """Full-tree contract checks; changes to providers affect untouched routes."""
    audit = audit_suppressions()
    report = run_semgrep(["--config", str(CONTRACT_RULES), "app"])
    try:
        return max(audit, gate(report))
    finally:
        Path(report).unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--report"]:
        return gate(argv[1])
    test_rules()
    contracts = contract_gate()
    if argv == ["--contracts"]:
        return contracts
    report = run_semgrep(argv)
    try:
        return max(contracts, gate(report))
    finally:
        Path(report).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
