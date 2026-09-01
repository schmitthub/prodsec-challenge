#!/usr/bin/env bash
# Local SARIF for the VS Code SARIF Viewer (MS-SarifVSCode.sarif-viewer auto-loads
# .sarif/*.sarif in the workspace). Runs the same scanners as
# .pre-commit-config.yaml / security.yml over the whole tree, all severities, no
# gates, no baselines — the full picture, including findings CI deliberately
# ignores. Exits 0 regardless of findings; .sarif/ is gitignored.
#
# Needs: uvx (semgrep, bandit), gitleaks, osv-scanner on PATH — or a prek cache
# that already holds the go binaries (`prek run --all-files` installs them).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
out=.sarif
mkdir -p "$out"

# Pins come from the hook config so this script never drifts from CI.
cfg=.pre-commit-config.yaml
semgrep_version=$(grep -oE 'semgrep==[0-9.]+' "$cfg" | head -1 | cut -d= -f3)
bandit_version=$(grep -A1 'PyCQA/bandit' "$cfg" | grep -oE 'frozen: [0-9.]+' | cut -d' ' -f2)

tool() { # $1 binary, $2 install hint
  local bin
  bin=$(command -v "$1" || find "${PREK_HOME:-$HOME/.cache/prek}/hooks" -path "*/bin/$1" 2>/dev/null | head -1)
  [[ -n $bin ]] || { echo "missing: $1 — $2" >&2; exit 2; }
  echo "$bin"
}
command -v uvx >/dev/null || { echo "missing: uvx — https://docs.astral.sh/uv/" >&2; exit 2; }
gitleaks=$(tool gitleaks "brew install gitleaks")
osv=$(tool osv-scanner "brew install osv-scanner")

echo "semgrep $semgrep_version"
uvx "semgrep==$semgrep_version" scan --quiet --metrics=off --disable-version-check \
  --config p/default --config p/python --config p/security-audit --config p/owasp-top-ten --config .semgrep/ \
  --exclude .github/workflows \
  --sarif-output "$out/semgrep.sarif" --json-output "$out/semgrep.json" .
uvx "semgrep==$semgrep_version" scan --quiet --metrics=off --disable-version-check \
  --config p/github-actions --config .semgrep/ \
  --sarif-output "$out/semgrep-actions.sarif" --json-output "$out/semgrep-actions.json" .github/workflows

echo "bandit $bandit_version"
uvx --from "bandit[toml,sarif]==$bandit_version" bandit -c pyproject.toml -r . -q \
  -f sarif -o "$out/bandit.sarif" || true # exit 1 = findings

echo "gitleaks (full history, baseline not applied)"
"$gitleaks" git . --config .gitleaks.toml --redact --no-banner --exit-code 0 \
  --report-format sarif --report-path "$out/gitleaks.sarif"

echo "osv-scanner (uv.lock, osv-scanner.toml ignores not applied)"
empty=$(mktemp)
trap 'rm -f "$empty"' EXIT
"$osv" scan source -L uv.lock --config "$empty" --verbosity error --format sarif --output-file "$out/osv.sarif" >/dev/null || true
"$osv" scan source -L uv.lock --config "$empty" --verbosity error --format json --output-file "$out/osv.json" >/dev/null || true

echo
for f in "$out"/*.sarif; do
  n=$(python3 -c 'import json,sys; print(sum(len(r.get("results", [])) for r in json.load(open(sys.argv[1]))["runs"]))' "$f")
  printf '%-32s %s results\n' "$f" "$n"
done
