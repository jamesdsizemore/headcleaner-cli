from __future__ import annotations

from pathlib import Path

from headcleaner.redact import propose_redactions, write_derivative


def test_redaction_proposal_hashes_secret_and_derivative_leaves_canonical_unchanged(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    concept = bundle / "note.md"
    original = "---\ntype: Document\ntitle: Synthetic\nverified: human:pending\n---\nAPI key: sk-abcdefghijklmnopqrstuvwxyz123456\n"
    concept.write_text(original, encoding="utf-8")

    findings = propose_redactions(bundle)
    derivative = write_derivative(bundle, findings)

    assert concept.read_text(encoding="utf-8") == original
    assert len(findings) == 1
    assert findings[0].category == "secret"
    assert findings[0].status == "proposed"
    assert "sk-" not in findings[0].to_dict_json()
    assert len(findings[0].value_sha256) == 64
    rendered = (derivative / "note.md").read_text(encoding="utf-8")
    assert "[REDACTED:secret]" in rendered
    assert "sk-" not in rendered
    assert "canonical_concept: note.md" in rendered
