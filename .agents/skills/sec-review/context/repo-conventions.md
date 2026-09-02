# Repo conventions — records-api

Maintained by hand. The only place repo-specific policy lives; reviewer prompts stay
portable and read this instead.

## Where triage lives

- `challenge/deliverables/triage.md` — the human triage of known findings. A finding
  listed there is **baselined**: still real, still reported, but `comment` not `block`.
- `challenge/osv-uvlock.md`, `challenge/osv-requirements.md` — per-CVE reachability notes
  for dependency findings.
- `gitleaks-report.json` — redacted gitleaks baseline. `osv-scanner.toml` — dependency
  ignores, each must carry `reason` + `ignoreUntil`.

## Policy-exempt files (do not flag these for being what they are)

- `.github/workflows/test.yml` — the seeded workflow; intentionally minimal, left untouched
  apart from SHA-pinning. Not a security workflow.
- `app/` seeded vulnerabilities are the subject of the exercise and are **not fixed** on
  purpose. Report them; never suggest the reviewer patch them.
- `tests/`, `helpers/` fixture credentials for the in-memory fake DB.

## Conventions a reviewer should hold the repo to

- Actions SHA-pinned with a `# vX.Y.Z` comment.
- Tool versions pinned in two places that must match: `security.yml` /
  `.github/actions/osv-image-scan/action.yml` and `.pre-commit-config.yaml`.
- Gitleaks baseline stored **redacted**; every consumer passes `--redact`.
- Findings are triaged into baselines with a reason, never silenced via `.gitleaksignore`,
  `# nosemgrep`, `# nosec` or `continue-on-error` without an adjacent justification that
  points at a triage entry.
- Two dependency surfaces exist (`requirements.txt` for README/Dockerfile/test.yml;
  `uv.lock` for SBOM and the osv hook). Drift between them is a known, tracked item.
- Release chain: build → scan → sign, artifacts passed between jobs, no registry.
