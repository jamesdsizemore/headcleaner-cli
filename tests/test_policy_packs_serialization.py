from __future__ import annotations

from headcleaner.policy_packs import PackRule, PolicyPack


def test_policy_pack_serializes_version_and_rules_in_declaration_order() -> None:
    pack = PolicyPack(
        id="research",
        version="1",
        description="Evidence requirements.",
        rules=(
            PackRule("sources-required", "error", "sources.missing", "Source required."),
            PackRule("review-pending", "warning", "verified.pending", "Review pending."),
        ),
    )

    assert pack.to_dict() == {
        "id": "research",
        "version": "1",
        "description": "Evidence requirements.",
        "rules": [
            {
                "id": "sources-required",
                "severity": "error",
                "when": "sources.missing",
                "message": "Source required.",
            },
            {
                "id": "review-pending",
                "severity": "warning",
                "when": "verified.pending",
                "message": "Review pending.",
            },
        ],
    }
