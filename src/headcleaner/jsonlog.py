"""JSON event log for `headcleaner convert --json` (Eng #43).

Each file event emits one JSON line on stdout. Designed for piping
into `jq`, log aggregators, or downstream pipelines.

Event types:
- {"event": "start", "tool": "headcleaner", "version": "0.5.0", "format": "both", "files": N}
- {"event": "file", "index": i, "total": N, "relpath": "...", "engine": "...",
   "status": "ok"|"skipped"|"failed", "sha256": "...", "md_path": "...", "okf_path": "...",
   "error": "..."}
- {"event": "finish", "tool": "headcleaner", "version": "0.5.0", "ok": N, "failed": N, "skipped": N}
"""

from __future__ import annotations

import json
import sys
from typing import Any


def emit_json_event(payload: dict[str, Any]) -> None:
    """Emit one JSON line on stdout. Always line-buffered."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()
