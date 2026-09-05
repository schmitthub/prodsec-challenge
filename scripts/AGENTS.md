# `scripts/`

## Directory summary

Project-maintenance executables live here. The shell entry points format and lint the application, run the test suite, prepare the database before application or test startup, and produce full local security-scanner reports. `badhost-probe.py` is a focused runtime security probe against a locally running Records API. Generated `__pycache__/` data is not source and should not be documented or committed.

## Role in the project

These are operator and container-lifecycle tools, not imported application modules. `format.sh` and `lint.sh` provide developer checks; `prestart.sh`, `test.sh`, and `tests-start.sh` compose startup and test commands; `sarif-scan.sh` reproduces the repository's scanner coverage without CI severity gates or baselines; and `badhost-probe.py` tests the practical reachability and application impact of a dependency advisory.

## Code files and symbols

### `badhost-probe.py`

Dependency-free Python CLI that sends controlled raw HTTP/1.1 requests to test the Starlette BadHost primitive and determine whether this application's behavior makes it exploitable.

- `CANARY`: Unique path marker used to detect Host-header content folded into `request.url.path`.
- `send_raw`: Builds and sends one socket-level HTTP request with a caller-controlled `Host` header, then parses the response status, headers, and body.
- `reflected_path`: Decodes the global error handler's JSON response and returns its reflected `path`, or `None` when unavailable.
- `main`: Parses target credentials and URL, checks reachability, logs in, triggers the error-path oracle, tests a poisoned Host header, prints the verdict, and returns the CLI exit status.

### `format.sh`

POSIX-shell formatter that exits on the first failure, enables command tracing, applies Ruff's autofixes to `app/` and `scripts/`, and formats both trees. It defines no named shell variables or functions.

### `lint.sh`

Bash lint entry point shared by pre-commit and GitHub Actions. It resolves the repository root from `BASH_SOURCE`, then uses `uv run --frozen` for strict mypy over `app/` and Ruff lint/format checks over `app/`, `scripts/`, `tests/`, `.github/scripts/`, and `.semgrep/`. Historical generated migration revisions are excluded; the live Alembic environment is checked. It never autofixes source and defines no named shell variables or functions.

### `prestart.sh`

Bash container-startup entry point that waits for the database through `app.backend_pre_start`, applies Alembic migrations, and loads initial data through `app/initial_data.py`. It defines no named shell variables or functions.

### `sarif-scan.sh`

Bash CLI that runs Semgrep, Bandit, Gitleaks, and OSV-Scanner across their intended local inputs, writes `.sarif/` reports, and prints aggregate result counts. It changes to the repository root before resolving paths.

- `out`: Output directory for SARIF and companion JSON reports; fixed to `.sarif` at the repository root.
- `cfg`: Pre-commit configuration used as the source of scanner version pins.
- `semgrep_version`, `bandit_version`: Versions extracted from `cfg` to keep local scans aligned with repository tooling.
- `tool`: Resolves the binary named by positional parameter `$1` from `PATH` or the prek hook cache, using `$2` as its install hint, and exits when the binary is unavailable.
- `bin`: Function-local path selected by `tool` for the requested executable.
- `PREK_HOME`, `HOME`: Environment inputs used to select the prek hook-cache root, with `$HOME/.cache/prek` as the fallback.
- `gitleaks`, `osv`: Resolved executable paths returned by `tool`.
- `empty`: Temporary empty OSV-Scanner configuration, removed by the `EXIT` trap so repository ignore policy is not applied to this full-report scan.
- `f`, `n`: Final reporting-loop values for each SARIF file and its aggregate result count.

### `test.sh`

Bash test entry point that exits on failure, traces commands, runs the `tests/` pytest suite under Coverage.py, prints the terminal coverage report, and generates HTML coverage. The optional positional arguments (`$@`) provide the HTML report title, defaulting to `coverage`; it defines no named shell variables or functions.

### `tests-start.sh`

Bash test-startup entry point that exits on failure, traces commands, waits for test dependencies through `app.tests_pre_start`, and delegates to `scripts/test.sh` while forwarding all positional arguments (`$@`). It defines no named shell variables or functions.

## Local guide aliases

- `AGENTS.md`: This directory-scoped contributor guide.
- `CLAUDE.md`: Portable sibling symlink to `AGENTS.md`; keep its target local and relative so clones work at any filesystem path.
