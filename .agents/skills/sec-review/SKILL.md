---
name: sec-review
description: Fan-out AI security review of a diff (or the whole tree) for this FastAPI service. Builds a redacted context pack (diff, route map, auth model, scanner findings), runs one reviewer per vulnerability class in parallel where the harness supports subagents, adversarially verifies every finding, and emits a block/comment/escalate decision that only blocks on deterministic evidence. Use for "security review this PR/branch/diff", "sec-review", "run the AI reviewer", or before opening a PR that touches app/, tests/, or .github/.
---

# sec-review

Reference implementation of `challenge/ai-security-review.md`. Harness-agnostic: every
step is a file or a shell command. Works in Claude Code (`.claude/skills/sec-review` is a
symlink here), Codex (`.agents/skills/` is read natively), or by hand.

Arguments: `$ARGUMENTS` may be a base ref (`main`, `origin/main`, a SHA), a PR number
(`#12` → resolve with `gh pr view 12 --json baseRefOid -q .baseRefOid`), or `--full`.
Default: merge-base with `origin/main`.

**Cost.** Every reviewer and verifier is a fresh subagent that re-reads the pack. A normal
PR (2–5 changed files) runs 1–3 reviewers and 1–2 verifiers: roughly 150–300k tokens.
`--full` is a whole-tree audit that runs every reviewer and verifies every finding — the
first run on this repo cost ~1.9M tokens. Treat `--full` as eval-only; run it when
`eval/cases.md` or a reviewer prompt changes, not per PR. Tell the user the mode and the
expected cost before fanning out.

## Non-negotiables

1. **Never block on an AI-only finding.** `decision: block` requires `evidence.deterministic:
   true` — a scanner hit in `findings.json`, a failing test in `tests/`, or a reproduction the
   verifier actually executed (TestClient or curl against a local server). Reasoning alone
   is `comment` at most.
2. **Redaction runs before any model sees the pack.** `scripts/context-pack.sh` excludes the
   paths in `redact-paths.txt` and runs gitleaks over the pack. If gitleaks reports a leak the
   pack is deleted and you stop. If gitleaks is unavailable, `MANIFEST.md` says so and you
   must tell the user the pack is unredacted before proceeding.
3. **Reviewers do not talk to each other and do not see each other's output.** Independence
   is what makes the verify pass meaningful.
4. **Do not fix anything.** This skill reports. Seeded vulnerabilities in `app/` are the
   subject of the exercise (see `AGENTS.md`).

## Steps

### 1. Build the context pack

```bash
.agents/skills/sec-review/scripts/context-pack.sh [--base <ref>] [--full] [--out .sec-review]
```

Produces `.sec-review/` (gitignored):

| file | what | source |
|---|---|---|
| `MANIFEST.md` | base/head SHAs, mode, redaction status, file list | script |
| `diff.patch` | `git diff <base>...HEAD` minus redacted paths | git |
| `changed-files.txt` | paths in the diff (or all tracked `app/ tests/ .github/` on `--full`) | git |
| `route-map.md` / `route-map.json` | every route: method, path, handler `file:line`, path/query/body params, dependencies, `client_supplied_id` flag | `scripts/route_map.py` (imports `app.main`) |
| `auth-model.md` | how identity and authorization work in this service, per resource | `context/auth-model.md` (maintained by hand) |
| `repo-conventions.md` | where triage lives, which files are policy-exempt, pin/baseline conventions | `context/repo-conventions.md` (maintained by hand) |
| `findings.json` | normalized scanner results `{tool, rule, level, file, line, message}` limited to changed files | `.sarif/*.sarif` from `scripts/sarif-scan.sh` |
| `codeowners.txt` | for `suggested_owner` | `.github/CODEOWNERS` |

If `.sarif/` is missing or older than HEAD, run `scripts/sarif-scan.sh` first. Findings are
the deterministic evidence tier; without them nothing can block.

### 2. Fan out reviewers

One reviewer per file in `reviewers/`, **but only those whose scope intersects
`changed-files.unredacted.txt`**. Skipped reviewers are listed in the report as
"not run (no files in scope)". `--full` runs all five.

| reviewer | class | runs when the diff touches |
|---|---|---|
| `access-control.md` | BAC / IDOR / privilege escalation | `app/routes/`, `app/auth.py`, `app/db.py`, `app/main.py`, or the route map changed |
| `injection.md` | SQLi, command, SSRF, path traversal | any `app/**/*.py` |
| `authn-secrets.md` | JWT, sessions, secrets, crypto, password handling | `app/auth.py`, `app/routes/login.py`, `app/db.py`, `app/models.py`, any redacted path, or a gitleaks/bandit-B105 hit in `findings.json` |
| `data-exposure.md` | error handlers, logging, over-broad responses, debug surfaces | `app/main.py`, `app/routes/`, `app/models.py`, `Dockerfile` |
| `supply-chain-ci.md` | workflows, action pins, permissions, deps, Dockerfile | `.github/`, `Dockerfile`, `.dockerignore`, `pyproject.toml`, `uv.lock`, `requirements.txt`, `.pre-commit-config.yaml`, `*.toml`, `.gitleaks*`, `.semgrepignore`, `scripts/` |

Each reviewer gets exactly this prompt (fill the placeholders, nothing else):

```
You are the <class> reviewer. Read <skill>/reviewers/<file>.md and follow it exactly.
Context pack: <abs path to .sec-review/>. Read MANIFEST.md first.
Read-only. Do NOT execute code, run tests, start servers, or send requests — that is
the verifier's job. Trace and cite; give the verifier a concrete payload to try.
Return ONLY a JSON array matching the "finding" definition in <skill>/schema.json.
Return [] if nothing meets the bar. Do not modify files.
```

- **Harness has a subagent/task tool** (Claude Code `Agent`, anything equivalent): spawn all
  five in one turn, in parallel, fresh context each, read-only tools. Collect the arrays.
- **No subagent tool** (Codex without multi-agent, plain chat): run the five prompts one
  after another yourself, writing each result to `.sec-review/raw/<reviewer>.json` before
  starting the next so earlier output doesn't leak into later reasoning.

### 3. Verify

Merge the arrays, dedupe on `(file, line, class)`, keep the higher confidence. Then run
`verify.md` — **one verifier per class that produced findings** (so at most five), each
given that class's full array, fresh context, parallel. A verifier walks its findings in
order and returns one `verdict` per finding. The verifier's job is to kill each finding:
prove it's a false positive, or produce the deterministic evidence that lets it block.

Batching per class is a deliberate cost trade: findings in one class share the same
files and repro setup, so one context does the work of N. Independence across classes is
preserved. If a class has more than ~6 findings, split it in two.

Discard `verdict.is_real == false`. Attach `verdict.evidence` to the finding. A verdict
with `baselined: true` survives but is downgraded from `block` to `comment` in step 4 —
it is already tracked in the repo's triage, not a regression.

### 4. Decide

Apply in order; first match wins.

| condition | decision |
|---|---|
| any surviving finding touches `app/auth.py`, exposes a credential, or is a full auth bypass | `escalate` (notify security owner now, also apply the row below) |
| `severity ∈ {critical, high}` AND `confidence == high` AND `evidence.deterministic` AND NOT `baselined` | `block` |
| `confidence ≥ medium` (includes baselined findings that would otherwise block — say so in the report) | `comment` |
| otherwise | drop (log to `.sec-review/dropped.json` for eval) |

`risk_label` is the highest surviving severity, or `none`. `suggested_owner` = CODEOWNERS
match for the file, else the last committer of the line (`git log -1 --format=%ae -L`).

### 5. Report

Write `.sec-review/report.md` and print it. Format:

```
## sec-review: <risk_label> — <decision>
base <sha7>..head <sha7> · <n> files · <n> findings after verify (<n> dropped) · redaction: <status>

| # | sev | conf | class | where | summary | evidence | owner |
...

### Details
one paragraph per finding: what, why it matters here (reference auth-model.md), how the
verifier confirmed it, suggested fix direction (no code).

### Not flagged (deliberate)
things a reviewer raised and the verifier killed, one line each with the reason. This is
the false-positive record the eval needs.
```

Also write `.sec-review/result.json` matching the top-level object in `schema.json`.

## Evaluation

`eval/cases.md` lists the seeded vulnerabilities as expected detections and the
legitimate patterns (`/me`, `/notes`, staff gate) as expected non-detections. Run
`--full`, compare `result.json` against it, record hit/miss/FP counts in the report footer.
Anything missed or falsely flagged is triage material, not something to tune away
silently.

## Files

```
SKILL.md              this
schema.json           finding / verdict / result shapes
redact-paths.txt      never enters the pack
context/auth-model.md maintained description of identity + authz per resource
context/repo-conventions.md  maintained repo policy: triage location, exempt files, pin conventions
reviewers/*.md        one per class
verify.md             adversarial verifier
eval/cases.md         expected hits and non-hits
scripts/context-pack.sh, scripts/route_map.py
```
