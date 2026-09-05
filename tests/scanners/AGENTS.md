# Scanner gate tests

test_semgrep_gate.py imports the checked-in CI/local gate by file path and tests
rule-specific justifications, blanket suppression rejection, exception visibility,
comment tokenization, full-tree scope, and failure propagation.

The Compose test hook mounts .github read-only so the same gate is tested there.
Semgrep's own positive/negative fixtures live alongside rules in .semgrep and run
inside the existing scanner hook and the CI full-tree contract step.

## Direct files and symbols

- `__init__.py`: package marker/public re-exports.
- `test_semgrep_gate.py`: `SCRIPT`; `spec`; `gate`; `test_unjustified_or_blanket_suppression_blocks()`; `test_justified_exception_remains_visible()`; `test_comment_looking_string_is_not_a_suppression()`; `test_contract_gate_scans_whole_app_and_preserves_failures()`.

## Aliases

CLAUDE.md is a portable relative symlink to AGENTS.md. Keep this guide current when symbols move.
