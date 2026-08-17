"""Webhook integration — POST the run manifest to a URL after a run completes.

Usage (programmatic):
    from headcleaner.webhook import post_webhook
    post_webhook("https://hooks.slack.com/...", run_record)

Used by `headcleaner watch --webhook-url <URL>` to notify external
services (Slack, Discord, ntfy, custom) when a re-conversion completes.

The payload is JSON: {tool, version, started_at, finished_at, format,
input_root, output_root, results: [...]}. The full manifest is sent; if
you want a slimmer payload, edit `post_webhook()`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .emit.manifest import RunRecord


def build_payload(record: RunRecord) -> dict[str, Any]:
    """Build the JSON payload from a RunRecord."""
    return {
        "tool": record.tool,
        "version": record.version,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "format": record.format,
        "input_root": record.input_root,
        "output_root": record.output_root,
        "options": record.options,
        "results": [
            {
                "source_path": r.source_path,
                "relpath": r.relpath,
                "engine": r.engine,
                "sha256": r.sha256,
                "md_path": r.md_path,
                "okf_path": r.okf_path,
                "status": r.status,
                "error": r.error,
            }
            for r in record.results
        ],
        "summary": {
            "total": len(record.results),
            "ok": sum(1 for r in record.results if r.status == "ok"),
            "failed": sum(1 for r in record.results if r.status == "failed"),
            "skipped": sum(1 for r in record.results if r.status == "skipped"),
        },
    }


def post_webhook(url: str, record: RunRecord, *, timeout: float = 10.0) -> int:
    """POST the manifest payload to `url`. Returns the HTTP status code.

    Raises urllib.error.URLError on network/timeout failure (caller
    catches and logs).
    """
    payload = build_payload(record)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "headcleaner/0.4"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status
