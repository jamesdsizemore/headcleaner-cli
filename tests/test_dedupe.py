from __future__ import annotations


def test_dedupe_groups_exact_and_orders_candidate_pairs() -> None:
    from headcleaner.dedupe import analyze_documents

    families = analyze_documents(
        [
            {"id": "a", "sha256": "same", "title": "Guide", "text": "alpha beta", "path": "a.md"},
            {"id": "b", "sha256": "same", "title": "Guide", "text": "alpha beta", "path": "b.md"},
            {
                "id": "c",
                "sha256": "other",
                "title": "Guide revised",
                "text": "alpha beta gamma",
                "path": "c.md",
            },
        ],
        threshold=0.5,
    )

    assert any(family.exact_members == ("a", "b") for family in families)
    candidates = [candidate for family in families for candidate in family.candidate_members]
    assert all(candidate["left_id"] < candidate["right_id"] for candidate in candidates)
