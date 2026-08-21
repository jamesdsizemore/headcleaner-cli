from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from headcleaner.cli import cli
from headcleaner.review import decide
from headcleaner.review_workbench import build_packet, render_packet


def _write_concept(path: Path) -> None:
    path.write_text(
        "---\n"
        "type: Document\n"
        "title: Alpha\n"
        "status: unverified\n"
        "verified: human:pending\n"
        "sources:\n"
        "  - uri: file:///inbox/alpha.txt\n"
        "    sha256: "
        + "a" * 64
        + "\n---\n\nAlpha body.\n",
        encoding="utf-8",
    )


def _frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---\n", 2)[1])


def test_packet_is_a_read_only_evidence_projection(tmp_path: Path) -> None:
    concept = tmp_path / "alpha.md"
    _write_concept(concept)
    original = concept.read_text(encoding="utf-8")

    packet = build_packet(tmp_path, "alpha.md")

    assert packet.concept_ref == "alpha.md"
    assert packet.review_state == "human:pending"
    assert packet.citations == ({"uri": "file:///inbox/alpha.txt", "sha256": "a" * 64},)
    assert concept.read_text(encoding="utf-8") == original
    assert '"concept_ref": "alpha.md"' in render_packet(packet, format="json")


def test_decision_requires_evidence_and_appends_audit_record(tmp_path: Path) -> None:
    concept = tmp_path / "alpha.md"
    _write_concept(concept)

    with pytest.raises(ValueError, match="evidence"):
        decide(
            concept,
            decision="approved",
            reviewer="james",
            reason="Source and output agree",
            evidence_refs=(),
        )

    decide(
        concept,
        decision="approved",
        reviewer="james",
        reason="Source and output agree",
        evidence_refs=("source:file:///inbox/alpha.txt",),
    )

    frontmatter = _frontmatter(concept)
    assert frontmatter["verified"] == "human:reviewed"
    assert frontmatter["review_audit"] == [
        {
            "decision": "approved",
            "reviewer": "james",
            "reason": "Source and output agree",
            "evidence_refs": ["source:file:///inbox/alpha.txt"],
            "timestamp": frontmatter["review_audit"][0]["timestamp"],
        }
    ]


def test_review_workbench_cli_exports_offline_json(tmp_path: Path) -> None:
    _write_concept(tmp_path / "alpha.md")

    result = CliRunner().invoke(cli, ["review-workbench", str(tmp_path), "alpha.md", "--format", "json"])

    assert result.exit_code == 0, result.output
    assert '"concept_ref": "alpha.md"' in result.output
