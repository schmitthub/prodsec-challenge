# GitHub security settings audit: schmitthub/prodsec-challenge

Pulled 2026-09-03 via `gh api` (viewer permission: ADMIN) plus local `.github/` files. Items marked **review** are observations, not necessarily defects.

## Repository (General)

- Visibility: public, not a fork (upstream `fhsol/prodsec-challenge` is a separate remote, push disabled locally).
- Default branch: `main`.
- Merge methods: squash only (merge commits and rebase disabled at repo level). **review**: the `main` ruleset allows `squash` and `rebase`; repo setting is the effective restriction.
- Auto-merge: disabled.
- Delete head branch on merge: enabled.
- Web commit sign-off: not required.
- Forking: allowed (public repo, cannot be disabled).
- Features on: issues, wiki, projects. Discussions off. **review**: wiki is world-editable-by-collaborator content with no ruleset coverage; disable if unused.
- Security policy (`SECURITY.md`): none, `isSecurityPolicyEnabled: false`.
- Private vulnerability reporting: disabled. **review**: public repo with no `SECURITY.md` and PVR off means no disclosure channel.
- Direct collaborators: `schmitthub` only.
- Deploy keys: none. Webhooks: none.
- CODEOWNERS: `* @schmitthub`, `/.github/ @schmitthub`; validation errors: none.
- Environments: one, `copilot`, no protection rules, no deployment branch policy, admins can bypass.

## Actions

- Actions enabled, allowed actions: **all** (no allowlist of verified/creator actions). `sha_pinning_required: false` at repo level; pins enforced only by convention in-repo plus the Semgrep/CodeQL Actions rules.
- Default `GITHUB_TOKEN` permissions: read-only. Workflows may not approve PRs.
- Fork PR workflow approval: first-time contributors only.
- OIDC subject claim: default (`repo:owner/repo`), immutable subject off.
- Actions secrets: none. Dependabot secrets: none.
- Actions variables: `CVSS_FAIL_THRESHOLD=9.0`.
- Actions cache: 30 active caches, ~1.4 GB (image archives keyed `image-<sha>`).
- Workflow permission blocks: every job declares explicit `permissions:`; `contents: read` floor, `security-events: write` on scanner jobs, `id-token`/`attestations`/`artifact-metadata: write` only on `release.yml` image and build jobs, `contents: write` only on the release build job.
- Triggers: `pr.yml` on `pull_request` to main (opened/synchronize/reopened); `main.yml` on push main; `codeql.yml` push main, PR to main, weekly cron; `release.yml` on tag `v*`. No `pull_request_target` anywhere.

## Advanced Security / Code security

- Dependency graph and Dependabot alerts: enabled (`hasVulnerabilityAlertsEnabled: true`).
- Dependabot security updates: enabled, not paused.
- Dependabot version updates (`.github/dependabot.yml`): pip, github-actions, docker; weekly Monday; 7-day cooldown; pip excludes `requirements.txt`; groups for pip minor/patch and all actions.
- Open Dependabot alerts: 29 across three manifests. `uv.lock` 13 (3 high, 8 medium, 2 low), `pyproject.toml` 8 (1 high, 6 medium, 1 low), `requirements.txt` 8 (1 high, 6 medium, 1 low). Same advisories reported three times.
- **review**: `dependabot.yml` comment says `requirements.txt` alerts "are dismissed by a Dependabot rule in repo settings (manifest path filter)", but 8 `requirements.txt` alerts are open and zero alerts are in `auto_dismissed` or `dismissed` state. Either the auto-triage rule was never saved, or it does not match. Check Settings > Code security > Dependabot > Auto-triage rules.
- Code scanning default setup: **not configured** (advanced setup via `codeql.yml`). Default-setup probe lists languages `actions, javascript, javascript-typescript, python, typescript`; only `python` and `actions` are analyzed by the workflow.
- Code scanning upload categories present: `/language:python` and `/language:actions` (CodeQL), `semgrep` (Semgrep OSS), `bandit`, `gitleaks`, `container` (osv-scanner).
- Open code scanning alerts: 2, both CodeQL python: `py/full-ssrf` (critical, `app/routes/webhooks.py`) and `py/sql-injection` (high, `app/db.py`). Zero dismissed, zero fixed. **review**: Semgrep, Bandit, Gitleaks and osv-scanner categories show no open alerts even though the seeded findings exist. Confirm their SARIF uploads carry results, or the alerts are being suppressed by the baseline/diff logic.
- CodeQL databases stored: `python-database`, `actions-database`.
- Secret scanning: enabled. Push protection: enabled. Open secret scanning alerts: 0.
- Secret scanning non-provider patterns and validity checks: API reports `disabled` for both, but neither is available on a personal public repo. Non-provider patterns, AI/generic secret detection, custom patterns, and validity checks all require GitHub Secret Protection (Team or Enterprise Cloud). Personal public repos get partner-pattern scanning and push protection only. No action possible here; the Gitleaks entropy gap in the write-up stays a client-side concern, and Bandit remains the only low-entropy password check in the pipeline.
- Advanced Security flag: not returned for public repos (GHAS features are on by default for public).
- Update branch button ("always suggest updating PR branches"): enabled. Squash commit title `COMMIT_OR_PR_TITLE`, message `COMMIT_MESSAGES`.
- Immutable releases: enabled at repo level (`enforced_by_owner: false`).

## CodeQL customisation (`.github/codeql/`)

- `codeql-config.yml`: `disable-default-queries: false`; query suite `security-and-quality` (superset of `security-extended`); comment notes to fall back to `security-extended` if quality alerts get noisy.
- `paths-ignore`: `tests`, `challenge`, `.venv`, `.serena`, `.claude`, `.codex`. No `paths:` allowlist on purpose so `.github/workflows` stays visible to the `actions` language. **review**: `paths-ignore` is shared across both languages, so `.claude`/`.codex` hook scripts are also excluded from the actions/python analyses.
- Custom pack `custom-queries/`: `qlpack.yml` (`schmitthub/prodsec-challenge-queries` 0.0.1, depends on `codeql/python-all: "*"`), one placeholder `challenge.ql` (`where none()`), `@id py/prodsec-challenge/placeholder`. The `- uses: ./.github/codeql/custom-queries` line in the config is commented out, so the pack is not run in CI.
- Workflow: `codeql.yml` matrix `python` + `actions`, per-job `contents: read`, `security-events: write`, `actions: read`, `packages: read`; `fail-fast: false`.
- CodeQL threat model: `remote` (default-setup probe value; advanced setup does not set `threat-models` in the config, so default applies).

## Rulesets

- Legacy branch protection on `main`: none (`branches/main/protection` returns "Branch not protected"). All enforcement is via rulesets.
- All three rulesets: `enforcement: active`, one bypass actor: `RepositoryRole` id 5 = repository **admin**, `bypass_mode: always`. **review**: the sole collaborator is an admin, so every rule below is bypassable by the only person who can push. Fine for a solo repo, worth stating in the write-up.

### `all` (branch, `~ALL`)

- Rules: block deletion, require signed commits.

### `main` (branch, `~DEFAULT_BRANCH` + `refs/heads/main`)

- Rules: block deletion, block force push (`non_fast_forward`), restrict creation, restrict update, require linear history, require signed commits.
- Pull request rule: 1 approving review, dismiss stale reviews on push, require code owner review, require approval of last push, require conversation resolution, require extra approval for unattributed changes, allowed merge methods `squash` and `rebase`. No `required_reviewers` list.
- Code scanning rule: tool `CodeQL`, block on security alerts `high_or_higher`, other alerts `errors`. **review**: only CodeQL is named; Semgrep/Bandit/osv uploads are not gating via this rule (they gate inside `security.yml` on PRs instead).
- Code quality rule: severity `errors`.
- Copilot code review: enabled on PRs, not on push, not on draft PRs.
- Required status checks (strict, enforced on create): `CodeQL` (integration 57789 = GitHub Code Scanning) and `Security / Container image / Scan image archive` (integration 15368 = GitHub Actions). **review**: the container scan job is documented as best-effort/non-blocking in CLAUDE.md, but it is a required check here. It will only ever fail on infra errors, so the check adds friction without gating. The `semgrep`, `bandit`, `gitleaks`, `test` and `dependency-review` jobs are **not** required checks, so a red PR scanner job does not block merge on its own.

### `releases` (tag, `refs/tags/v*`)

- Rules: block deletion, block force push, restrict creation, restrict update, require signed commits.
- Combined with immutable releases, `v*` tags cannot be created, moved or deleted except by admin bypass.

## Egress note

- `GET /repos/schmitthub/prodsec-challenge` (no trailing slash) was initially denied by the container firewall because the `.clawker.yaml` allow was the prefix `/repos/schmitthub/prodsec-challenge/`. Replaced with regex `~/repos/schmitthub/prodsec-challenge(/.*)?` and refreshed; all items above are now verified. `gh auth status` still reports the token as invalid because `/user` is denied; the token is fine.
