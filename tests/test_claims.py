from __future__ import annotations


def test_claims_emit_cited_potential_conflict_and_stale_only() -> None:
    from headcleaner.claims import analyze_claims

    chunks = [
        {"id": "a", "text": "Owner: Alice\nBudget: $10", "citation": {"source_sha256": "a"}},
        {"id": "b", "text": "Owner: Bob\nBudget: $10", "citation": {"source_sha256": "b"}},
    ]
    claims, findings = analyze_claims(chunks, stale_after="2000-01-01", today="2026-08-19")
    assert {claim.kind for claim in claims} >= {"owner", "amount"}
    assert any(finding.type == "potential_conflict" for finding in findings)
    assert any(finding.type == "stale" for finding in findings)


def test_claim_suppression_retains_candidate_and_reason_without_conflict() -> None:
    from headcleaner.claims import analyze_claims

    claims, findings = analyze_claims(
        [
            {"id": "a", "text": "Owner: Alice", "citation": {"source_sha256": "a"}},
            {"id": "b", "text": "Owner: Bob", "citation": {"source_sha256": "b"}},
        ],
        suppressions={"owner": "policy/claims/owner-private"},
    )

    assert {claim.status for claim in claims} == {"suppressed"}
    assert {claim.suppression_reason for claim in claims} == {"policy/claims/owner-private"}
    assert not findings


def test_claims_source_scope_excludes_cross_source_conflicts() -> None:
    from headcleaner.claims import analyze_claims

    _claims, findings = analyze_claims(
        [
            {"id": "a", "text": "Owner: Alice", "citation": {"source_sha256": "a"}},
            {"id": "b", "text": "Owner: Bob", "citation": {"source_sha256": "b"}},
        ],
        scope="source",
    )

    assert not findings


def test_claims_emit_cited_staleness_from_per_source_lifecycle_fields() -> None:
    from headcleaner.claims import analyze_claims

    _claims, findings = analyze_claims(
        [
            {
                "id": "a",
                "text": "Owner: Alice",
                "citation": {"source_sha256": "source-a", "start": 1, "end": 1},
            }
        ],
        stale_after_by_source={"source-a": "2000-01-01"},
        today="2026-08-19",
    )

    stale = next(finding for finding in findings if finding.type == "stale")
    assert stale.rule_id == "lifecycle/stale_after"
    assert stale.evidence == ({"source_sha256": "source-a", "start": 1, "end": 1},)
