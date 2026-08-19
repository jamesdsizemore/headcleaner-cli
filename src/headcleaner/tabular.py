"""Typed structured-table assets shared by extraction and emission."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

TABULAR_KINDS = frozenset({"csv", "worksheet", "pdf_table"})


def _json_safe(value: object) -> bool:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


@dataclass(frozen=True)
class TabularAsset:
    """Immutable table payload with an output-root-relative sidecar location."""

    id: str
    kind: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    source_location: dict[str, int | None] | None
    formula_cells: tuple[dict[str, Any], ...]
    merged_ranges: tuple[str, ...]
    provenance: dict[str, Any]
    sidecar_relpath: str

    def __post_init__(self) -> None:
        if self.kind not in TABULAR_KINDS:
            raise ValueError(f"invalid tabular asset kind: {self.kind}")
        if not _json_safe(self.provenance) or not _json_safe(self.formula_cells):
            raise ValueError("tabular metadata must be JSON-safe")
        if not self.sidecar_relpath.startswith("_assets/tables/"):
            raise ValueError("tabular sidecar must remain below _assets/tables")

    @classmethod
    def create(
        cls,
        source_sha: str,
        kind: str,
        ordinal: int,
        columns: Sequence[str],
        rows: Sequence[Sequence[str]],
        *,
        source_location: dict[str, int | None] | None = None,
        formula_cells: Sequence[dict[str, Any]] = (),
        merged_ranges: Sequence[str] = (),
        provenance: dict[str, Any],
    ) -> TabularAsset:
        normalized_columns = tuple(str(column) for column in columns)
        normalized_rows = tuple(tuple(str(cell) for cell in row) for row in rows)
        normalized_content = json.dumps(
            {"columns": normalized_columns, "rows": normalized_rows},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        asset_id = hashlib.sha256(
            f"{source_sha}\0{kind}\0{ordinal}\0{normalized_content}".encode()
        ).hexdigest()
        return cls(
            id=asset_id,
            kind=kind,
            columns=normalized_columns,
            rows=normalized_rows,
            source_location=source_location,
            formula_cells=tuple(dict(cell) for cell in formula_cells),
            merged_ranges=tuple(merged_ranges),
            provenance=dict(provenance),
            sidecar_relpath=f"_assets/tables/{asset_id}.csv",
        )
