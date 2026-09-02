# Contributing

> [!IMPORTANT]
> **Reviewing the take-home?** The submission index (CI, custom check, write-up, AI reviewer design, AI usage note) is at the top of [`README.md`](README.md#records-api-security-take-home). This file is the local-setup quickstart.

The seeded app under `app/` is intentionally vulnerable and stays that way — the work here is the CI, hooks and checks around it. Python 3.11; [`uv`](https://docs.astral.sh/uv/) manages the interpreter and deps.

```bash
uv sync                                        # runtime deps + ruff (dev group)
uv run python -m unittest discover -s tests    # what CI runs
uv run uvicorn app.main:app --reload           # API on :8000
```

## 1. Sandboxed agent session with clawker (optional)

[clawker](https://github.com/schmitthub/clawker) runs a coding agent (Claude Code or Codex) in a hardened container with a path-scoped egress firewall. The repo ships a ready [`.clawker.yaml`](.clawker.yaml): Python/Node/Go stacks, `gh`, `cosign`, `syft`, `prek`, the Serena/deepwiki/Context7 MCP servers, and an allowlist scoped to this project's GitHub paths plus the scanner and package hosts the hooks need.

Prerequisites: Docker running, macOS or Linux, an Anthropic or OpenAI API key (you authenticate once inside the container; the credential persists in a named volume).

### Install

```bash
brew install schmitthub/tap/clawker
# or
curl -fsSL https://raw.githubusercontent.com/schmitthub/clawker/main/scripts/install.sh | bash
clawker version
```

Full options: <https://docs.clawker.dev/installation>. Quickstart: <https://docs.clawker.dev/quickstart>.

### Build the images

`clawker init` is not needed — the project config is committed. Images are per project and per harness:

```bash
clawker build              # default harness: claude
clawker build -t codex     # codex harness
clawker build --no-cache   # after editing build.* in .clawker.yaml
```

If you want to run `docker build` from inside the agent container (the Dockerfile / image workflow), copy [`.clawker.local.yaml.example`](.clawker.local.yaml.example) to `.clawker.local.yaml` (gitignored) — it mounts the host Docker socket.

### Monitoring (optional)

Opt-in OpenTelemetry stack: collector, OpenSearch + Dashboards (`http://localhost:5601`), Prometheus (`http://localhost:9090`). Bring it up **before** starting agents — a container resolves the collector at start and will not connect retroactively.

```bash
clawker monitor init && clawker monitor up
clawker monitor status
clawker monitor down            # keep data
clawker monitor down --volumes  # wipe data and re-seed on next up
```

The `Clawker` workspace in Dashboards has Claude Code cost/usage and activity dashboards plus firewall (Envoy/CoreDNS/eBPF) logs — useful for spotting which path a blocked request needed before adding a rule. Details: <https://docs.clawker.dev/monitoring>.

### Start an agent

```bash
clawker go dev                                 # build if needed, then run agent "dev"
clawker run -it --rm --agent dev @             # claude harness
clawker run -it --rm --agent dev @:codex       # codex harness
clawker attach --agent dev                     # reattach
clawker stop --agent dev && clawker rm --agent dev
```

Inside the container `.venv` is a tmpfs, so run `uv sync` at the start of every session. A blocked request shows up as `NXDOMAIN` or HTTP 403; add a rule to `security.firewall` in `.clawker.yaml` (path-scoped where possible) and apply it live with `clawker firewall refresh` on the host. `clawker firewall status` / `clawker firewall list` show the active set.

## 2. Git hooks: prek (or pre-commit)

[`.pre-commit-config.yaml`](.pre-commit-config.yaml) mirrors the CI gates: ruff, gitleaks (redacted baseline), bandit (HIGH), semgrep python + GitHub Actions rulesets through the shared [`semgrep_gate.py`](.github/scripts/semgrep_gate.py), osv-scanner on `uv.lock` changes, and the unit tests. Scanners install into the hook runner's own cache from their pinned `rev` — none of them are project dependencies.

[prek](https://github.com/j178/prek) is the intended runner (the clawker image already has it):

```bash
uv tool install prek
prek install                # git pre-commit hook
prek run --all-files        # everything, whole tree
prek run semgrep --all-files
```

[pre-commit](https://pre-commit.com/) works with the same config:

```bash
uv tool install pre-commit
pre-commit install
pre-commit run --all-files
```

Notes:

- gitleaks and osv-scanner are `golang` hooks: a Go toolchain must be on `PATH` for either runner to build them.
- `--all-files` also runs ruff `--fix`/format and the whitespace fixers over the seeded `app/`, `tests/`, `helpers/` and `README.md`. Unless you mean to commit a formatting change, revert those: `git checkout -- app tests helpers README.md`.
- Hooks always run. `.claude/hooks/git-checks.sh` (and the Codex mirror) rejects `--no-verify`, `-n`, `SKIP=` and `core.hooksPath` overrides from an agent session; do the same by hand.

## 3. Local SARIF reports

[`scripts/sarif-scan.sh`](scripts/sarif-scan.sh) runs the same scanners over the whole tree with **all severities, no gates, no baselines** and writes `.sarif/*.sarif` (gitignored). The VS Code [SARIF Viewer](https://marketplace.visualstudio.com/items?itemName=MS-SarifVSCode.sarif-viewer) picks the directory up automatically for inline findings.

```bash
prek run --all-files        # once: populates prek's cache with the gitleaks + osv-scanner binaries
scripts/sarif-scan.sh
```

Needs `uvx` (semgrep and bandit run at the version pinned in the hook config) and `gitleaks` + `osv-scanner`, resolved from `PATH` or from prek's hook cache. pre-commit users, or anyone skipping the hooks, install the two binaries directly (`brew install gitleaks osv-scanner`).
