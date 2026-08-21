from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from headcleaner.cli import cli
from headcleaner.policy_packs import evaluate_pack, load_pack


def _pack(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_pack_inheritance_is_depth_first_and_reports_missing_source_evidence(tmp_path: Path) -> None:
    packs = tmp_path / "packs"
    packs.mkdir()
    _pack(
        packs / "base.toml",
        """id = "base"
version = "1"
extends = []
description = "base requirements"

[[rules]]
id = "sources-required"
severity = "error"
when = "sources.missing"
message = "A source citation is required."
""",
    )
    _pack(
        packs / "research.toml",
        """id = "research"
version = "1"
extends = ["base"]
description = "research requirements"

[[rules]]
id = "pending-review"
severity = "warning"
when = "verified.pending"
message = "Human review is pending."
""",
    )
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "note.md").write_text(
        "---\ntype: Document\nstatus: unverified\nverified: human:pending\n---\nBody.\n",
        encoding="utf-8",
    )

    pack = load_pack("research", installed_dir=packs)
    findings = evaluate_pack(pack, bundle)

    assert [rule.id for rule in pack.rules] == ["sources-required", "pending-review"]
    assert [(item.rule_id, item.severity, item.concept_ref) for item in findings] == [
        ("sources-required", "error", "note.md"),
        ("pending-review", "warning", "note.md"),
    ]
    assert findings[0].evidence == {"field": "sources", "value": None}


def test_policy_test_cli_uses_bundle_local_pack_and_returns_error_exit(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    policies = bundle / ".headcleaner" / "policies"
    policies.mkdir(parents=True)
    _pack(
        policies / "research.toml",
        """id = "research"
version = "1"
extends = []
description = "research requirements"

[[rules]]
id = "sources-required"
severity = "error"
when = "sources.missing"
message = "A source citation is required."
""",
    )
    (bundle / "note.md").write_text("---\ntype: Document\n---\nBody.\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["policy", "test", str(bundle), "--pack", "research", "--json"])

    assert result.exit_code == 1, result.output
    assert '"rule_id": "sources-required"' in result.output
