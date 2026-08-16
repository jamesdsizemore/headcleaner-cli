"""Bundle-level manifest (Eng #39) — aggregate across runs.

After every `headcleaner convert`, the per-run `manifest.json` lives at
`<output_root>/manifest.json`. When `write_bundle_manifest=True`, this
module also writes a persistent `<output_root>/bundle.manifest.json`
that:

- accumulates a top-level `concept_count` count
- tracks `last_run_at` timestamp
- maintains a `format_breakdown` (engine -> file count)
- keeps a `recent_runs` list (last 20 entries)

This is the single source of truth for "what's in this OKF bundle?"
across multiple convert runs.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def write_bundle_manifest(output_root: Path, record) -> Path:
    """Write (or merge) `<output_root>/bundle.manifest.json`.

    Reads existing bundle.manifest.json if present, merges with the new
    run record, writes back. Idempotent.
    """
    path = output_root / "bundle.manifest.json"
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    else:
        existing = {}

    # Merge: counts from the new run
    counts = {"ok": 0, "failed": 0, "skipped": 0}
    engines: Counter[str] = Counter()
    for r in record.results:
        if r.status in counts:
            counts[r.status] += 1
        if r.engine:
            engines[r.engine] += 1

    merged: dict[str, Any] = {
        "tool": "headcleaner",
        "version": record.version,
        "last_run_at": record.finished_at,
        "last_run_summary": counts,
        "concept_count": sum(counts.values()) + int(existing.get("concept_count", 0)),
        "engine_counts": dict(existing.get("engine_counts", {})),
        "format_breakdown": dict(existing.get("format_breakdown", {})),
        "recent_runs": ([
            {
                "timestamp": record.finished_at,
                "format": record.format,
                "input_root": record.input_root,
                "output_root": record.output_root,
                "counts": counts,
            }
        ] + existing.get("recent_runs", []))[:20],
    }

    # Merge engine counts across runs (preserve existing engines)
    for e, n in engines.items():
        merged["engine_counts"][e] = merged["engine_counts"].get(e, 0) + n

    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
