from __future__ import annotations

import pytest

from headcleaner.tabular import TabularAsset


def test_tabular_asset_is_immutable_and_preserves_csv_structure() -> None:
    asset = TabularAsset.create(
        source_sha="source-sha",
        kind="csv",
        ordinal=0,
        columns=["name", "score"],
        rows=[["Ada", "10"]],
        provenance={"engine": "csv", "delimiter": ","},
    )

    assert (
        asset.id
        == TabularAsset.create(
            source_sha="source-sha",
            kind="csv",
            ordinal=0,
            columns=["name", "score"],
            rows=[["Ada", "10"]],
            provenance={"engine": "csv", "delimiter": ","},
        ).id
    )
    assert asset.sidecar_relpath == f"_assets/tables/{asset.id}.csv"
    with pytest.raises(AttributeError):
        asset.kind = "worksheet"  # type: ignore[misc]


def test_tabular_asset_rejects_non_tabular_or_unsafe_metadata() -> None:
    with pytest.raises(ValueError, match="kind"):
        TabularAsset.create("source-sha", "invalid", 0, [], [], provenance={})
    with pytest.raises(ValueError, match="JSON-safe"):
        TabularAsset.create("source-sha", "csv", 0, [], [], provenance={"bad": {1}})
