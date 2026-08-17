"""Run-level manifest emitter — records what one headcleaner run did.

Written to <output_root>/manifest.json after every successful run.
Shape:
    {
      "tool": "headcleaner",
      "version": "0.1.0",
      "started_at": "ISO",
      "finished_at": "ISO",
      "input_root": "...",
      "output_root": "...",
      "format": "md" | "okf" | "both",
      "options": {...},
      "results": [
        {"source_path": "...", "relpath": "...",
         "engine": "...", "sha256": "...",
         "md_path": "..." | null, "okf_path": "..." | null,
         "status": "ok" | "skipped" | "failed",
         "error": "..." | null}
      ]
    }
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class FileResult:
    source_path: str
    relpath: str
    engine: str | None
    sha256: str | None
    md_path: str | None
    okf_path: str | None
    status: str  # "ok" | "skipped" | "failed"
    error: str | None = None
    duration_seconds: float | None = None  # extraction + emission wall time


@dataclass
class RunRecord:
    tool: str = "headcleaner"
    version: str = "0.1.0"
    started_at: str = ""
    finished_at: str = ""
    input_root: str = ""
    output_root: str = ""
    format: str = "both"  # "md" | "okf" | "both"
    options: dict[str, Any] = field(default_factory=dict)
    results: list[FileResult] = field(default_factory=list)

    def finish(self) -> None:
        self.finished_at = _utc_now_iso()

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2, ensure_ascii=False)


def write(record: RunRecord, output_root: Path) -> Path:
    """Write the manifest.json into the output root."""
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "manifest.json"
    path.write_text(record.to_json(), encoding="utf-8")
    return path


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
