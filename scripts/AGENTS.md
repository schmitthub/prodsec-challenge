# `scripts/`

## Directory summary

Project-maintenance executables live here. `badhost-probe.py` performs a focused runtime security probe against a locally running Records API; `sarif-scan.sh` runs the repository's security scanners and writes full local SARIF reports for editor review. Generated `__pycache__/` data is not source and should not be documented or committed.

## Role in the project

These scripts support security triage and local analysis. They are operator tools, not imported application modules: one validates the practical reachability and impact of a dependency advisory, while the other reproduces the repository's scanner coverage without CI severity gates or baselines.

## Files and symbols

### `badhost-probe.py`

Dependency-free Python CLI that sends controlled raw HTTP/1.1 requests to test the Starlette BadHost primitive and determine whether this application's behavior makes it exploitable.

- `CANARY`: Unique path marker used to detect Host-header content folded into `request.url.path`.
- `send_raw`: Builds and sends one socket-level HTTP request with a caller-controlled `Host` header, then parses the response status, headers, and body.
- `reflected_path`: Decodes the global error handler's JSON response and returns its reflected `path`, or `None` when unavailable.
- `main`: Parses target credentials and URL, checks reachability, logs in, triggers the error-path oracle, tests a poisoned Host header, prints the verdict, and returns the CLI exit status.

### `sarif-scan.sh`

Bash CLI that runs Semgrep, Bandit, Gitleaks, and OSV-Scanner across their intended local inputs, writes `.sarif/` reports, and prints result counts.

- `out`: Output directory for SARIF and companion JSON reports; fixed to `.sarif` at the repository root.
- `cfg`: Pre-commit configuration used as the source of scanner version pins.
- `semgrep_version`, `bandit_version`: Versions extracted from `cfg` to keep local scans aligned with repository tooling.
- `tool`: Resolves a required binary from `PATH` or the prek hook cache and exits with an install hint when missing.
- `gitleaks`, `osv`: Resolved executable paths returned by `tool`.
- `empty`: Temporary empty OSV-Scanner configuration, removed by the `EXIT` trap so repository ignore policy is not applied to this full-report scan.
- `f`, `n`: Final reporting loop values for each SARIF file and its aggregate result count.
