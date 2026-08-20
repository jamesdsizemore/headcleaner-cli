"""Conversion report emitter (v0.13.x — bonus item).

After a successful run, write `<output>/REPORT.md` with per-format stats:

- Total files processed / skipped / failed
- Per-engine breakdown (count, avg time, error rate)
- Overall wall-clock
- Top 10 errors (truncated)

Designed for org-wide adoption dashboards — a quick scan of the report
shows whether the conversion is healthy.
"""

from __future__ import annotations

import datetime as _dt
from collections import Counter
from collections.abc import Iterable
from pathlib import Path


def _format_pct(num: int, denom: int) -> str:
    if denom == 0:
        return "0%"
    return f"{100.0 * num / denom:.1f}%"


def build_report(
    records: Iterable[dict],
    *,
    started_at: _dt.datetime,
    finished_at: _dt.datetime,
    bundle_root: Path | str,
    claim_review: dict[str, object] | None = None,
    dedupe: dict[str, object] | None = None,
    graph: dict[str, object] | None = None,
) -> str:
    """Render a Markdown conversion report from run records.

    Each record is the dict shape produced by `run.run_pipeline` per file
    (relpath, engine, status, sha256, error, etc.). Missing fields are
    tolerated.
    """
    rows = list(records)
    by_status = Counter(r.get("status", "unknown") for r in rows)
    by_engine = Counter(str(r.get("engine") or "unknown") for r in rows)
    ok = by_status.get("ok", 0)
    skipped = by_status.get("skipped", 0)
    failed = by_status.get("failed", 0)
    total = len(rows)
    wall = (finished_at - started_at).total_seconds()

    lines = []
    lines.append("# headcleaner conversion report")
    lines.append("")
    lines.append(f"- **Bundle:** `{bundle_root}`")
    lines.append(f"- **Started:** {started_at.isoformat(timespec='seconds')}")
    lines.append(f"- **Finished:** {finished_at.isoformat(timespec='seconds')}")
    lines.append(f"- **Wall clock:** {wall:.1f}s")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Files processed | **{ok}** |")
    lines.append(f"| Files skipped | {skipped} |")
    lines.append(f"| Files failed | {failed} |")
    lines.append(f"| **Total** | {total} |")
    lines.append(f"| Success rate | {_format_pct(ok, total)} |")
    lines.append("")

    # Per-engine breakdown
    lines.append("## Per-engine breakdown")
    lines.append("")
    lines.append("| Engine | Total | OK | Failed | Error rate | Avg time |")
    lines.append("|---|---|---|---|---|---|")
    for engine, count in sorted(by_engine.items(), key=lambda kv: (-kv[1], kv[0])):
        e_rows = [r for r in rows if str(r.get("engine") or "unknown") == engine]
        e_ok = sum(1 for r in e_rows if r.get("status") == "ok")
        e_failed = sum(1 for r in e_rows if r.get("status") == "failed")
        durations = [
            float(r["duration_seconds"])
            for r in e_rows
            if isinstance(r.get("duration_seconds"), (int, float))
        ]
        avg_time = f"{sum(durations) / len(durations):.3f}s" if durations else "n/a"
        lines.append(
            f"| `{engine}` | {count} | {e_ok} | {e_failed} | "
            f"{_format_pct(e_failed, count)} | {avg_time} |"
        )
    lines.append("")

    confidences = [
        float(row["confidence"]) for row in rows if isinstance(row.get("confidence"), (int, float))
    ]
    diagnostic_codes = Counter(
        diagnostic.get("code", "UNKNOWN")
        for row in rows
        for diagnostic in row.get("diagnostics", [])
        if isinstance(diagnostic, dict)
    )
    if confidences or diagnostic_codes:
        lines.append("## Extraction diagnostics")
        lines.append("")
        if confidences:
            lines.append(f"- **Average confidence:** {sum(confidences) / len(confidences):.2f}")
        if diagnostic_codes:
            lines.append("- **Diagnostic codes:**")
            for code, count in sorted(diagnostic_codes.items()):
                lines.append(f"  - `{code}`: {count}")
        lines.append("")

    if claim_review is not None:
        lines.append("## Claim review candidates")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Cited candidates | {int(claim_review.get('count', 0))} |")
        lines.append(f"| Potential findings | {int(claim_review.get('finding_count', 0))} |")
        lines.append(f"| Derivative | `{claim_review.get('path', 'okf/claim-review.json')}` |")
        lines.append("")

    if dedupe is not None:
        lines.append("## Duplicate and version candidates")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Families | {int(dedupe.get('count', 0))} |")
        lines.append(f"| Threshold | {float(dedupe.get('threshold', 0.8)):.2f} |")
        lines.append(f"| Derivative | `{dedupe.get('path', 'okf/duplicate-families.json')}` |")
        lines.append("")

    if graph is not None:
        lines.append("## Evidence graph")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        lines.append(f"| Nodes | {int(graph.get('node_count', 0))} |")
        lines.append(f"| Edges | {int(graph.get('edge_count', 0))} |")
        lines.append(f"| Derivative | `{graph.get('path', 'okf/graph.jsonl')}` |")
        lines.append("")

    # Errors (top 10)
    err_rows = [r for r in rows if r.get("status") == "failed" and r.get("error")]
    if err_rows:
        lines.append("## Top errors")
        lines.append("")
        lines.append("| File | Engine | Error |")
        lines.append("|---|---|---|")
        for r in err_rows[:10]:
            rel = r.get("relpath", "?")
            engine = r.get("engine", "?")
            err = (r.get("error") or "").replace("|", "\\|").replace("\n", " ")[:120]
            lines.append(f"| `{rel}` | `{engine}` | {err} |")
        if len(err_rows) > 10:
            lines.append("")
            lines.append(f"_... and {len(err_rows) - 10} more._")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Generated by headcleaner._")
    return "\n".join(lines) + "\n"


def write_report(
    path: Path,
    records: Iterable[dict],
    *,
    started_at: _dt.datetime,
    finished_at: _dt.datetime,
    bundle_root: Path | str,
    claim_review: dict[str, object] | None = None,
    dedupe: dict[str, object] | None = None,
    graph: dict[str, object] | None = None,
) -> Path:
    """Build the report and write it to `path`. Returns the path."""
    text = build_report(
        records,
        started_at=started_at,
        finished_at=finished_at,
        bundle_root=bundle_root,
        claim_review=claim_review,
        dedupe=dedupe,
        graph=graph,
    )
    path.write_text(text, encoding="utf-8")
    return path
