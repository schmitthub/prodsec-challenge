import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/semgrep_gate.py"
spec = importlib.util.spec_from_file_location("semgrep_gate", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.mark.parametrize(
    "comment",
    [
        "# nosemgrep",
        "# nosemgrep: authz-public-policy",
        "# nosemgrep: *",
    ],
)
def test_unjustified_or_blanket_suppression_blocks(tmp_path, comment) -> None:
    (tmp_path / "policy.py").write_text(f"{comment}\nprincipal = PUBLIC\n")
    assert gate.audit_suppressions(tmp_path) == 1


def test_justified_exception_remains_visible(tmp_path, capsys) -> None:
    (tmp_path / "policy.py").write_text(
        "# OAuth2 credential exchange is deliberately anonymous.\n"
        "principal = PUBLIC  # nosemgrep: authz-public-policy\n"
    )
    assert gate.audit_suppressions(tmp_path) == 0
    assert "reviewed exception:" in capsys.readouterr().out


def test_comment_looking_string_is_not_a_suppression(tmp_path) -> None:
    (tmp_path / "example.py").write_text('example = "# nosemgrep"\n')
    assert gate.audit_suppressions(tmp_path) == 0


def test_contract_gate_scans_whole_app_and_preserves_failures(
    monkeypatch, tmp_path
) -> None:
    report = tmp_path / "report.json"
    report.write_text('{"results": []}')
    calls = []

    def scan(args):
        calls.append(args)
        return str(report)

    monkeypatch.setattr(gate, "run_semgrep", scan)
    monkeypatch.setattr(gate, "audit_suppressions", lambda: 1)
    assert gate.contract_gate() == 1
    assert calls == [["--config", str(gate.CONTRACT_RULES), "app"]]
    assert not report.exists()
