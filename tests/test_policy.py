from __future__ import annotations

from pathlib import Path

import pytest


def test_policy_loads_claim_suppression_reasons(tmp_path: Path) -> None:
    from headcleaner.policy import Policy

    path = tmp_path / "policy.toml"
    path.write_text(
        "[claims]\nscope = 'source'\n\n"
        "[claims.suppressions]\nowner = 'policy/claims/owner-private'\n\n"
        "[graph]\nexclude_edge_kinds = ['mentions']\n",
        encoding="utf-8",
    )

    policy = Policy.load(path)

    assert policy.claim_suppressions == {"owner": "policy/claims/owner-private"}
    assert policy.claim_scope == "source"
    assert policy.graph_excluded_edge_kinds == {"mentions"}


def test_policy_rejects_invalid_graph_edge_kind(tmp_path: Path) -> None:
    from headcleaner.policy import Policy

    path = tmp_path / "policy.toml"
    path.write_text("[graph]\nexclude_edge_kinds = ['invented']\n", encoding="utf-8")

    with pytest.raises(ValueError, match="graph.exclude_edge_kinds"):
        Policy.load(path)


def test_policy_accepts_contract_graph_candidate_edge_kind(tmp_path: Path) -> None:
    from headcleaner.policy import Policy

    path = tmp_path / "policy.toml"
    path.write_text("[graph]\nexclude_edge_kinds = ['conflicts_candidate']\n", encoding="utf-8")

    assert Policy.load(path).graph_excluded_edge_kinds == {"conflicts_candidate"}
