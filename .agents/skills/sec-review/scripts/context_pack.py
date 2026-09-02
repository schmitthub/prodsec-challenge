"""Build the redacted context pack for sec-review.

    uv run python .agents/skills/sec-review/scripts/context_pack.py [--base REF] [--full] [--out DIR]

--base  diff base (default: merge-base with origin/main, then main, then HEAD~1).
        Diff mode compares the base to the working tree, so uncommitted work is reviewed.
--full  whole in-scope tree instead of a diff.
--out   output dir (default .sec-review, gitignored).

Redaction: pathspecs in redact-paths.txt never enter the pack. If gitleaks is on PATH or
in the prek cache the finished pack is scanned; a leak deletes the pack and exits 3. If
gitleaks is missing the MANIFEST says "unverified" and the caller must warn the user.

Requires git, Python 3.11+, and the project's runtime deps (for the route map). No other
tools. Works on Linux and macOS.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SKILL = Path(".agents/skills/sec-review")
SNIPPET = 120
# Prose files match words like "owner" or "role" constantly; only path signals apply to them.
PROSE_SUFFIXES = {".md", ".rst", ".txt", ".lock"}

# Tracked paths that are in scope for a full-tree review.
FULL_SCOPE = [
    "app",
    "tests",
    "helpers",
    "config",
    "scripts",
    ".github",
    "Dockerfile",
    ".dockerignore",
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    ".pre-commit-config.yaml",
    ".gitleaks.toml",
    ".gitleaksignore",
    "osv-scanner.toml",
    ".semgrepignore",
    ".syft.yaml",
]

# Selection signals per lens. `paths` match file paths (weight 3 per file); `content`
# matches added lines (diff mode) or file lines (full mode), weight 1 per line. The
# orchestrator ranks lenses by score and picks at most five; `general` has no
# signals and is chosen on judgement.
SIGNALS: dict[str, dict[str, list[str]]] = {
    "access-control": {
        "paths": [r"(^|/)(routes?|handlers?|views?|api|controllers?)/"],
        "content": [
            r"@\w+\.(get|post|put|patch|delete)\(",
            r"\{\w*(id|ids|key|uuid|slug)\}",
            r"\b(owner|role|tenant|permission|authori[sz]e)\b",
            r"current_user",
        ],
    },
    "authentication": {
        "paths": [r"(^|/)(auth|login|session|token|middleware)\w*\.py$"],
        "content": [
            r"\bjwt\b|\.decode\(|\.encode\(",
            r"\b(password|passwd|credential|session|bearer|oauth)\b",
            r"verify_(exp|signature|aud|iss)",
            r"get_current_user|Depends\(",
        ],
    },
    "secrets-crypto": {
        "paths": [r"(^|/)(\.env|config/|settings|secrets?)", r"(^|/)Dockerfile$"],
        "content": [
            r"\b(SECRET|API_KEY|TOKEN|PRIVATE_KEY|PASSWORD)\b\s*[=:]",
            r"BEGIN (RSA |EC )?PRIVATE KEY",
            r"\b(hashlib|hmac|random\.|secrets\.|Fernet|AES|ssl\.|verify\s*=\s*False)",
            r"environ\.get\([^)]*,\s*['\"]",
        ],
    },
    "injection": {
        "paths": [r"(^|/)(db|database|models?|query|repositor\w+|sql)\w*\.py$"],
        "content": [
            r"\.execute(many)?\(|cursor\(|\btext\(",
            r"f['\"].*\b(SELECT|INSERT|UPDATE|DELETE|WHERE)\b",
            r"\bsubprocess\b|os\.system|os\.popen|shell\s*=\s*True",
            r"\beval\(|\bexec\(|Template\(",
            r"\bopen\(|os\.path\.join|Path\(",
        ],
    },
    "outbound-requests": {
        "paths": [
            r"(^|/)(webhooks?|callbacks?|clients?|integrations?|outbound)\w*\.py$"
        ],
        "content": [
            r"\b(requests|httpx|urllib|aiohttp)\b",
            r"\bsocket\.|getaddrinfo",
            r"\b(redirect|webhook|callback|url)\b",
        ],
    },
    "data-exposure": {
        "paths": [r"(^|/)(main|app|errors?|logging)\w*\.py$"],
        "content": [
            r"exception_handler|repr\(exc|str\(exc|traceback",
            r"\blogging\b|logger\.|print\(",
            r"response_model|JSONResponse|/docs|/redoc|openapi",
            r"\bdebug\b|--reload",
        ],
    },
    "input-validation-dos": {
        "paths": [r"(^|/)(schemas?|models?|validators?)\w*\.py$"],
        "content": [
            r"\bre\.(compile|match|search|fullmatch|sub)\(",
            r"\b(limit|page|page_size|offset|max_length|Field\(|Query\()",
            r"\bwhile\b|\.read\(\)|\bgzip\b|\bzlib\b",
        ],
    },
    "business-logic": {
        "paths": [r"(^|/)(orders?|payments?|billing|workflow|jobs?|tasks?)\w*\.py$"],
        "content": [
            r"\b(status|state|balance|total|amount|quota|refund|transfer|approve)\b",
            r"\b(retry|lock|transaction|commit|idempot\w*)\b",
        ],
    },
    "unsafe-parsing-files": {
        "paths": [r"(^|/)(uploads?|files?|import|parsers?)\w*\.py$"],
        "content": [
            r"\b(pickle|marshal|shelve|jsonpickle)\b|yaml\.load\(|etree|xml\.",
            r"\b(zipfile|tarfile|UploadFile|tempfile|shutil|FileResponse|send_file)\b",
        ],
    },
    "web-platform": {
        "paths": [r"(^|/)(templates?|static|middleware)\w*"],
        "content": [
            r"CORSMiddleware|allow_origins|allow_credentials",
            r"set_cookie|SameSite|csrf|X-Frame-Options|Content-Security-Policy",
            r"HTMLResponse|Jinja2Templates|\bHost\b|\bOrigin\b|Referer|X-Forwarded",
        ],
    },
    "supply-chain-ci": {
        "paths": [
            r"^\.github/",
            r"(^|/)Dockerfile",
            r"^\.dockerignore$",
            r"^(pyproject\.toml|uv\.lock|requirements[^/]*\.txt)$",
            r"^\.pre-commit-config\.yaml$",
            r"^(\.gitleaks\.toml|\.gitleaksignore|osv-scanner\.toml|\.semgrepignore|\.syft\.yaml)$",
            r"^scripts/",
        ],
        "content": [
            r"\buses:\s*\S+@(?![0-9a-f]{40})",
            r"\$\{\{\s*(github\.event|inputs|steps\.[^}]*outputs)",
            r"pull_request_target|workflow_run|permissions:\s*write-all",
            r"continue-on-error|nosec|nosemgrep",
        ],
    },
}
LENSES = [*SIGNALS, "general"]


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def resolve_base(base: str | None) -> str:
    if base:
        return git("rev-parse", "--verify", base).strip()
    for cand in ("origin/main", "main"):
        if (
            subprocess.run(
                ["git", "rev-parse", "-q", "--verify", cand],
                capture_output=True,
                check=False,
            ).returncode
            == 0
        ):
            return git("merge-base", cand, "HEAD").strip()
    return git("rev-parse", "HEAD~1").strip()


def read_redactions() -> list[str]:
    lines = (SKILL / "redact-paths.txt").read_text().splitlines()
    return [
        ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")
    ]


def lines_of(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln]


def collect_scope(
    mode: str, base: str, exclude: list[str], out: Path
) -> tuple[list[str], list[str]]:
    """Write diff.patch and the changed-file lists; return (all, unredacted) paths."""
    if mode == "diff":
        (out / "diff.patch").write_text(git("diff", base, "--", ".", *exclude))
        changed = lines_of(git("diff", "--name-only", base))
        unredacted = lines_of(git("diff", "--name-only", base, "--", ".", *exclude))
    else:
        (out / "diff.patch").write_text("")
        changed = lines_of(git("ls-files", *FULL_SCOPE))
        unredacted = lines_of(git("ls-files", *FULL_SCOPE, "--", *exclude))
    (out / "changed-files.txt").write_text(
        "\n".join(changed) + ("\n" if changed else "")
    )
    (out / "changed-files.unredacted.txt").write_text(
        "\n".join(unredacted) + ("\n" if unredacted else "")
    )
    redacted = sorted(set(changed) - set(unredacted))
    (out / "redacted-in-scope.txt").write_text(
        "\n".join(redacted) + ("\n" if redacted else "")
    )
    return changed, unredacted


def build_route_map(out: Path) -> str:
    sys.path.insert(0, str(SKILL / "scripts"))
    try:
        import route_map  # local import so a broken app does not kill the pack

        route_map.main(
            ["--json", str(out / "route-map.json"), "--md", str(out / "route-map.md")]
        )
        return "ok"
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - any app import failure must not kill the pack
        (out / "raw" / "route-map.err").write_text(f"{type(exc).__name__}: {exc}\n")
        (out / "route-map.md").write_text("# Route map unavailable\n")
        (out / "route-map.json").write_text("[]\n")
        return "failed (see raw/route-map.err; run 'uv sync' first?)"


def normalize_sarif(sarif_dir: Path) -> list[dict]:
    findings: list[dict] = []
    for path in sorted(sarif_dir.glob("*.sarif")):
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        for run in doc.get("runs", []):
            driver = run.get("tool", {}).get("driver", {})
            rules = {r.get("id"): r for r in driver.get("rules", [])}
            for res in run.get("results", []):
                rule = rules.get(res.get("ruleId"), {})
                props = rule.get("properties", {})
                loc = (res.get("locations") or [{}])[0].get("physicalLocation", {})
                uri = loc.get("artifactLocation", {}).get("uri", "")
                uri = re.sub(r"^file://", "", uri)
                uri = re.sub(r"^\./", "", uri)
                findings.append(
                    {
                        "tool": driver.get("name"),
                        "rule": res.get("ruleId"),
                        "level": res.get("level")
                        or rule.get("defaultConfiguration", {}).get("level", "warning"),
                        "severity": props.get("security-severity")
                        or props.get("severity"),
                        "file": uri,
                        "line": loc.get("region", {}).get("startLine"),
                        "message": (res.get("message", {}).get("text") or "")[:300],
                    }
                )
    return findings


def write_findings(out: Path, unredacted: list[str]) -> str:
    sarif_dir = Path(".sarif")
    if not any(sarif_dir.glob("*.sarif")):
        (out / "findings.json").write_text("[]\n")
        (out / "findings.all.json").write_text("[]\n")
        return "none (.sarif/ missing; run scripts/sarif-scan.sh)"
    all_findings = normalize_sarif(sarif_dir)
    in_scope = [f for f in all_findings if f["file"] in set(unredacted)]
    (out / "findings.all.json").write_text(json.dumps(all_findings, indent=1) + "\n")
    (out / "findings.json").write_text(json.dumps(in_scope, indent=1) + "\n")
    newest = max(p.stat().st_mtime for p in sarif_dir.glob("*.sarif"))
    stamp = datetime.fromtimestamp(newest, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{len(in_scope)} in scope / {len(all_findings)} total; newest SARIF {stamp}"


def scan_lines(
    mode: str, out: Path, unredacted: list[str]
) -> list[tuple[str, int, str]]:
    """(file, line, text) for every reviewable line: added diff lines or whole files."""
    rows: list[tuple[str, int, str]] = []
    if mode == "diff":
        current = ""
        new_line = 0
        for ln in (out / "diff.patch").read_text(errors="replace").splitlines():
            if ln.startswith("+++ "):
                current = re.sub(r"^\+\+\+ b/", "", ln)
                continue
            if ln.startswith("@@"):
                m = re.search(r"\+(\d+)", ln)
                new_line = int(m.group(1)) if m else 0
                continue
            if ln.startswith("+"):
                if Path(current).suffix not in PROSE_SUFFIXES:
                    rows.append((current, new_line, ln[1:]))
                new_line += 1
            elif not ln.startswith("-"):
                new_line += 1
        return rows
    for path in unredacted:
        if Path(path).suffix in PROSE_SUFFIXES:
            continue
        try:
            text = Path(path).read_text(errors="replace")
        except OSError:
            continue
        rows.extend((path, i, ln) for i, ln in enumerate(text.splitlines(), 1))
    return rows


def compute_signals(mode: str, out: Path, unredacted: list[str]) -> dict:
    rows = scan_lines(mode, out, unredacted)
    result: dict[str, dict] = {}
    for lens, spec in SIGNALS.items():
        path_hits = [
            p for p in unredacted if any(re.search(rx, p) for rx in spec["paths"])
        ]
        content_hits = []
        for file, line, text in rows:
            for rx in spec["content"]:
                if re.search(rx, text):
                    content_hits.append(f"{file}:{line}: {text.strip()[:SNIPPET]}")
                    break
        result[lens] = {
            "score": 3 * len(path_hits) + len(content_hits),
            "path_hits": path_hits,
            "content_hits": content_hits[:25],
            "content_hit_count": len(content_hits),
        }
    result["general"] = {"score": None, "note": "no signals; chosen on judgement"}
    ranked = sorted(SIGNALS, key=lambda k: -result[k]["score"])
    return {"ranked": [k for k in ranked if result[k]["score"] > 0], "lenses": result}


def find_gitleaks() -> str | None:
    found = shutil.which("gitleaks")
    if found:
        return found
    home = Path(os.environ.get("PREK_HOME", Path.home() / ".cache" / "prek")) / "hooks"
    for candidate in home.glob("**/bin/gitleaks"):
        return str(candidate)
    return None


def verify_redaction(out: Path) -> str:
    binary = find_gitleaks()
    if not binary:
        return "unverified (gitleaks not installed)"
    report = out / "raw" / "gitleaks-pack.json"
    proc = subprocess.run(
        [
            binary,
            "dir",
            str(out),
            "--config",
            ".gitleaks.toml",
            "--redact",
            "--no-banner",
            "--exit-code",
            "3",
            "--report-path",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return "clean"
    if proc.returncode == 3:
        print(
            "REDACTION FAILED: gitleaks found secret material in the pack. Pack deleted.",
            file=sys.stderr,
        )
        try:
            for hit in json.loads(report.read_text()):
                print(
                    f"  {hit.get('RuleID')} {hit.get('File')}:{hit.get('StartLine')}",
                    file=sys.stderr,
                )
        except (OSError, ValueError):
            pass
        shutil.rmtree(out, ignore_errors=True)
        sys.exit(3)
    (out / "raw" / "gitleaks.err").write_text(proc.stderr)
    return "unverified (gitleaks error, see raw/gitleaks.err)"


def write_manifest(
    out: Path,
    *,
    mode: str,
    base: str | None,
    head: str,
    redaction: str,
    route_status: str,
    findings_status: str,
    signals: dict,
) -> None:
    diff_files = (out / "diff.patch").read_text(errors="replace").count(
        "\ndiff --git "
    ) + (
        1
        if (out / "diff.patch").read_text(errors="replace").startswith("diff --git ")
        else 0
    )
    redacted = lines_of((out / "redacted-in-scope.txt").read_text())
    branch = git("branch", "--show-current", check=False).strip() or "detached"
    ranked = signals["ranked"]
    top = (
        ", ".join(f"{k} ({signals['lenses'][k]['score']})" for k in ranked[:8])
        or "none"
    )
    lines = [
        "# sec-review context pack",
        "",
        f"- mode: {mode}",
        *([f"- base: {base}"] if mode == "diff" else []),
        f"- head: {head}",
        f"- branch: {branch}",
        f"- generated: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- redaction: **{redaction}**",
        f"- route map: {route_status}",
        f"- scanner findings: {findings_status}",
        f"- lens signals (score): {top}",
        "",
        "## Redacted paths in scope (review manually, contents withheld)",
        *([f"- {p}" for p in redacted] or ["- none"]),
        "",
        "## Files",
        f"- diff.patch: {diff_files} files",
        (
            f"- changed-files.txt: {len(lines_of((out / 'changed-files.txt').read_text()))} paths "
            "(changed-files.unredacted.txt = what reviewers may read)"
        ),
        "- route-map.md / route-map.json",
        "- auth-model.md, repo-conventions.md",
        "- baseline.md (verifier only)",
        "- findings.json (findings.all.json = whole tree)",
        "- signals.json (lens selection input)",
        "- codeowners.txt",
        "",
    ]
    (out / "MANIFEST.md").write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--out", default=".sec-review")
    args = parser.parse_args(argv)

    os.chdir(git("rev-parse", "--show-toplevel").strip())
    mode = "full" if args.full else "diff"
    head = git("rev-parse", "HEAD").strip()
    base = None
    if mode == "diff":
        base = resolve_base(args.base)
        if base == head and not git("status", "--porcelain").strip():
            sys.exit(
                "base == head and the working tree is clean; nothing to review (use --full)"
            )

    out = Path(args.out)
    shutil.rmtree(out, ignore_errors=True)
    (out / "raw").mkdir(parents=True)

    exclude = [f":(exclude,glob){p}" for p in read_redactions()]
    _, unredacted = collect_scope(mode, base or head, exclude, out)

    route_status = build_route_map(out)
    for name in ("auth-model.md", "repo-conventions.md", "baseline.md"):
        shutil.copy(SKILL / "context" / name, out / name)
    owners = Path(".github/CODEOWNERS")
    (out / "codeowners.txt").write_text(owners.read_text() if owners.exists() else "")

    findings_status = write_findings(out, unredacted)
    signals = compute_signals(mode, out, unredacted)
    (out / "signals.json").write_text(json.dumps(signals, indent=1) + "\n")

    redaction = verify_redaction(out)
    write_manifest(
        out,
        mode=mode,
        base=base,
        head=head,
        redaction=redaction,
        route_status=route_status,
        findings_status=findings_status,
        signals=signals,
    )
    print((out / "MANIFEST.md").read_text())
    if redaction != "clean":
        print(
            f"WARNING: redaction {redaction}; tell the user before sending this pack to any model.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
