#!/usr/bin/env bash
# Build the redacted context pack for sec-review.
#
#   context-pack.sh [--base <ref>] [--full] [--out <dir>]
#
# --base   diff base (default: merge-base with origin/main, falling back to main, then HEAD~1)
# --full   no diff; every tracked file under app/ tests/ .github/ Dockerfile etc. is in scope
# --out    output dir (default .sec-review, gitignored)
#
# Redaction: paths in redact-paths.txt never enter the pack. If gitleaks is available the
# finished pack is scanned; a leak deletes the pack and exits 3. If gitleaks is missing the
# MANIFEST says "unverified" and the caller must warn the user.
set -euo pipefail

root=$(git rev-parse --show-toplevel)
cd "$root"
skill=.agents/skills/sec-review
out=.sec-review
base=""
mode=diff

while [[ $# -gt 0 ]]; do
  case $1 in
    --base) base=$2; shift 2 ;;
    --full) mode=full; shift ;;
    --out) out=$2; shift 2 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

rm -rf "$out"
mkdir -p "$out/raw"

head=$(git rev-parse HEAD)
if [[ $mode == diff ]]; then
  if [[ -z $base ]]; then
    for cand in origin/main main; do
      if git rev-parse -q --verify "$cand" >/dev/null; then base=$(git merge-base "$cand" HEAD); break; fi
    done
    [[ -n $base ]] || base=$(git rev-parse HEAD~1)
  else
    base=$(git rev-parse "$base")
  fi
  [[ $base != "$head" ]] || { echo "base == head; nothing to review (use --full for a tree audit)" >&2; exit 2; }
fi

# --- redaction pathspecs -----------------------------------------------------
mapfile -t redact < <(grep -vE '^\s*(#|$)' "$skill/redact-paths.txt")
exclude=()
for p in "${redact[@]}"; do exclude+=(":(exclude,glob)$p"); done

# --- diff / file list ----------------------------------------------------------
if [[ $mode == diff ]]; then
  git diff "$base...$head" -- . "${exclude[@]}" > "$out/diff.patch"
  git diff --name-only "$base...$head" > "$out/changed-files.txt"
  git diff --name-only "$base...$head" -- . "${exclude[@]}" > "$out/changed-files.unredacted.txt"
else
  : > "$out/diff.patch"
  git ls-files app tests helpers config scripts .github Dockerfile .dockerignore pyproject.toml uv.lock requirements.txt \
    .pre-commit-config.yaml .gitleaks.toml .gitleaksignore osv-scanner.toml .semgrepignore .syft.yaml > "$out/changed-files.txt"
  git ls-files app tests helpers config scripts .github Dockerfile .dockerignore pyproject.toml uv.lock requirements.txt \
    .pre-commit-config.yaml .gitleaks.toml .gitleaksignore osv-scanner.toml .semgrepignore .syft.yaml -- "${exclude[@]}" > "$out/changed-files.unredacted.txt"
fi
comm -23 <(sort "$out/changed-files.txt") <(sort "$out/changed-files.unredacted.txt") > "$out/redacted-in-scope.txt"

# --- route map -------------------------------------------------------------------
route_status=ok
if ! uv run --quiet python "$skill/scripts/route_map.py" --json "$out/route-map.json" --md "$out/route-map.md" 2> "$out/raw/route-map.err"; then
  route_status="failed (see raw/route-map.err — run 'uv sync' first?)"
  echo "# Route map unavailable" > "$out/route-map.md"
fi

# --- auth model + owners --------------------------------------------------------
cp "$skill/context/auth-model.md" "$out/auth-model.md"
cp "$skill/context/repo-conventions.md" "$out/repo-conventions.md"
[[ -f .github/CODEOWNERS ]] && cp .github/CODEOWNERS "$out/codeowners.txt" || : > "$out/codeowners.txt"

# --- scanner findings -----------------------------------------------------------
findings_status="none (.sarif/ missing — run scripts/sarif-scan.sh)"
if compgen -G ".sarif/*.sarif" >/dev/null; then
  # normalize every SARIF run into {tool, rule, level, file, line, message}
  jq -s '
    [ .[] | .runs[]? as $run
      | ($run.tool.driver.name) as $tool
      | ($run.tool.driver.rules // [] | map({(.id): .}) | add // {}) as $rules
      | $run.results[]?
      | {
          tool: $tool,
          rule: .ruleId,
          level: (.level // ($rules[.ruleId].defaultConfiguration.level // "warning")),
          severity: ($rules[.ruleId].properties["security-severity"] // $rules[.ruleId].properties.severity // null),
          file: (.locations[0].physicalLocation.artifactLocation.uri // "" | sub("^file://"; "") | sub("^\\./"; "")),
          line: (.locations[0].physicalLocation.region.startLine // null),
          message: (.message.text // "" | .[0:300])
        }
    ]' .sarif/*.sarif > "$out/findings.all.json"
  # scope to files in the pack (unredacted)
  jq --slurpfile files <(jq -R . "$out/changed-files.unredacted.txt" | jq -s .) \
    '[ .[] | select(.file as $f | $files[0] | index($f) != null) ]' "$out/findings.all.json" > "$out/findings.json"
  findings_status="$(jq length "$out/findings.json") in scope / $(jq length "$out/findings.all.json") total; SARIF mtime $(stat -c %y .sarif/semgrep.sarif 2>/dev/null | cut -d. -f1)"
else
  echo '[]' > "$out/findings.json"
fi

# --- redaction verification ---------------------------------------------------------
gitleaks_bin=$(command -v gitleaks || find "${PREK_HOME:-$HOME/.cache/prek}/hooks" -path '*/bin/gitleaks' 2>/dev/null | head -1 || true)
redaction=unverified
if [[ -n $gitleaks_bin ]]; then
  if "$gitleaks_bin" dir "$out" --config .gitleaks.toml --redact --no-banner --exit-code 3 \
       --report-path "$out/raw/gitleaks-pack.json" >/dev/null 2> "$out/raw/gitleaks.err"; then
    redaction=clean
  else
    rc=$?
    if [[ $rc -eq 3 ]]; then
      echo "REDACTION FAILED: gitleaks found secret material in the pack. Pack deleted." >&2
      jq -r '.[] | "  \(.RuleID) \(.File):\(.StartLine)"' "$out/raw/gitleaks-pack.json" >&2 || true
      rm -rf "$out"
      exit 3
    fi
    redaction="unverified (gitleaks error, see raw/gitleaks.err)"
  fi
fi

# --- manifest -----------------------------------------------------------------------
{
  echo "# sec-review context pack"
  echo
  echo "- mode: $mode"
  [[ $mode == diff ]] && echo "- base: $base"
  echo "- head: $head"
  echo "- branch: $(git branch --show-current 2>/dev/null || echo detached)"
  echo "- generated: $(date -u +%FT%TZ)"
  echo "- redaction: **$redaction**"
  echo "- route map: $route_status"
  echo "- scanner findings: $findings_status"
  echo
  echo "## Redacted paths in scope (review manually, contents withheld)"
  if [[ -s $out/redacted-in-scope.txt ]]; then sed 's/^/- /' "$out/redacted-in-scope.txt"; else echo "- none"; fi
  echo
  echo "## Files"
  echo "- diff.patch — $(grep -c '^diff --git' "$out/diff.patch" || true) files"
  echo "- changed-files.txt — $(wc -l < "$out/changed-files.txt") paths (changed-files.unredacted.txt = what reviewers may read)"
  echo "- route-map.md / route-map.json"
  echo "- auth-model.md, repo-conventions.md"
  echo "- findings.json (findings.all.json = whole tree)"
  echo "- codeowners.txt"
} > "$out/MANIFEST.md"

cat "$out/MANIFEST.md"
[[ $redaction == clean ]] || { echo; echo "WARNING: redaction $redaction — tell the user before sending this pack to any model." >&2; }
