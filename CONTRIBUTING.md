# Contributing

## Setup

Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

### [Optional] Sandboxed agent session with clawker

[clawker](https://github.com/schmitthub/clawker) is an agent sandboxing environment I've built that runs coding agents in hardened docker containers with a path-scoped egress firewall stack and control plane. The repo ships a ready [`.clawker.yaml`](.clawker.yaml).

Full Quickstart can be found at: <https://docs.clawker.dev/quickstart>. First go will take a bit of time as the necessary images are built and the monitoring stack is initialized.

```bash
# install with homebrew
brew install schmitthub/tap/clawker
# install with script
curl -fsSL https://raw.githubusercontent.com/schmitthub/clawker/main/scripts/install.sh | bash

# confirm installation
clawker version

# register project
clawker project register --yes

# build claude code image
clawker build              # default harness: claude

# build codex image
clawker build -t codex     # codex harness

# start monitoring stack (optional, must be done first)
clawker monitor init && clawker monitor up

# to bring the stack down at any point
clawker monitor down            # keep data
clawker monitor down --volumes  # wipe data and re-seed on next up

# run claude code image
clawker claude dev

# run codex image
clawker codex dev  # use a different agent name if "dev" is already taken by the claude agent, e.g. `clawker codex codex` creates a container named "codex"
```

> If you want to mount your host's docker socket for Docker Outside of Docker inside the agent container, copy [`.clawker.local.yaml.example`](.clawker.local.yaml.example) to `.clawker.local.yaml` (gitignored)

### [Optional] Git hooks: prek (or pre-commit)

[`.pre-commit-config.yaml`](.pre-commit-config.yaml) mirrors the CI gates for local feedback: ruff, gitleaks (redacted baseline), bandit (HIGH), semgrep python + GitHub Actions rulesets through the shared [`semgrep_gate.py`](.github/scripts/semgrep_gate.py), osv-scanner on `uv.lock` changes, and the unit tests. Scanners install into the hook runner's own cache from their pinned `rev` — none of them are project dependencies.

[prek](https://github.com/j178/prek) is the intended runner (drop in replacement for pre-commit written in Rust):

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

[golang](https://go.dev/doc/install) must be installed so `pre-commit` and `prek` can build the gitleaks and osv-scanner hooks.

### Local SARIF reports

[`scripts/sarif-scan.sh`](scripts/sarif-scan.sh) runs the same scanners over the whole tree with **all severities, no gates, no baselines** and writes `.sarif/*.sarif` (gitignored). IDEs that support SARIF will pick up the reports automatically. The VS Code [SARIF Viewer](https://marketplace.visualstudio.com/items?itemName=MS-SarifVSCode.sarif-viewer) extension detects the directory automatically and shows inline findings.

```bash
prek run --all-files        # once: populates prek's cache with the gitleaks + osv-scanner binaries
scripts/sarif-scan.sh
```

Needs `uvx` (semgrep and bandit run at the version pinned in the hook config) and `gitleaks` + `osv-scanner`, resolved from `PATH` or from prek's hook cache. pre-commit users, or anyone skipping the hooks, install the two binaries directly (`brew install gitleaks osv-scanner`).


### Security Review Agent Skill

Use `/sec-review` to scan PRs, Diffs, or specific files for top priority security issues.
