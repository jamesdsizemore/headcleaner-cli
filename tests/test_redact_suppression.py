from __future__ import annotations

from pathlib import Path

from headcleaner.redact import propose_redactions, write_derivative


def test_redaction_suppression_is_auditable_but_not_applied_to_derivative(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    concept = bundle / "note.md"
    original = "---\ntype: Document\n---\nAPI key: sk-abcdefghijklmnopqrstuvwxyz123456\n"
    concept.write_text(original, encoding="utf-8")

    findings = propose_redactions(bundle, suppress_categories={"secret": "policy/test"})
    derivative = write_derivative(bundle, findings)

    assert [(item.status, item.suppression_reason) for item in findings] == [("suppressed", "policy/test")]
    assert concept.read_text(encoding="utf-8") == original
    assert "sk-" in (derivative / "note.md").read_text(encoding="utf-8")
    assert "sk-" not in (derivative / "redaction-report.json").read_text(encoding="utf-8")
