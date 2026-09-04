# Repo conventions: records-api

Maintained by hand. The only place repo-specific policy lives; reviewer prompts stay
portable and read this instead.

## Baselines

- `baseline.md` (this directory): human-triaged findings. Listed there means **baselined**:
  still real, still reported, `comment` not `block`. Verifier only.
- `gitleaks-report.json`: redacted secret-scanner baseline; every consumer passes `--redact`.
- `osv-scanner.toml`: dependency ignores, each with `reason` + `ignoreUntil`.

## Policy-exempt files (do not flag these for being what they are)

- `.github/workflows/test.yml`: the seeded workflow; intentionally minimal, left untouched
  apart from SHA-pinning. Not a security workflow.
- Seeded vulnerabilities in `../../../../app/` are the subject of the exercise and are **not fixed** on
  purpose (see `AGENTS.md`). Report them; never suggest patching them.
- `../../../../tests/`, `../../../../helpers/` fixture credentials for the in-memory fake DB.

## Test accounts (for the verifier's reproductions)

`alice@example.test`/`alice-password`, `bob@example.test`/`bob-password` (members),
`clinician@example.test`/`clinician-password` (staff). Login `POST /api/login` returns a
bearer token. Test client: `fastapi.testclient.TestClient(app.main.app)`.

## Conventions a reviewer should hold the repo to

- Actions SHA-pinned with a `# vX.Y.Z` comment.
- Tool versions pinned in two places that must match: `security.yml` /
  `.github/actions/osv-image-scan/action.yml` and `.pre-commit-config.yaml`.
- Findings are triaged into baselines with a reason, never silenced via `.gitleaksignore`,
  `# nosemgrep`, `# nosec` or `continue-on-error` without an adjacent justification that
  points at a baseline entry.
- Two dependency surfaces exist (`requirements.txt` for README/Dockerfile/test.yml;
  `uv.lock` for SBOM and the osv hook). Drift between them is tracked (`baseline.md` B10).

## Release topology (artifact identity, not job ordering)

`image.yml`: `build` produces one docker-archive and its image ID. Two independent
consumers: `scan` (best-effort, advisory, may not block) and `sign` (release only, depends
on `build` alone). `build.yml` then signs and attests the source archive, SBOMs and
checksums, and copies in `image.yml`'s bundle for the image. No registry anywhere.

The invariant a reviewer checks: every scan, sign and attest step consumes the **exact**
archive or digest `build` emitted. A step that rebuilds, pulls, or substitutes the subject
is the finding. A `sign` job that does not `need` `scan` is **not** a finding; scanning is
advisory by policy here.
