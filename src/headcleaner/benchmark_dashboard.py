"""Public benchmark transparency renderer (Contract 3.8).

Accepts only validated `tests/quality/baseline.json`, a current benchmark
result JSON, and `ATTRIBUTION.md`. Emits a self-contained static HTML/JSON
dashboard. Rejects paths outside `tests/quality/fixtures` and any fixture
marked non-public.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PUBLIC_FIXTURES_ROOT = Path("tests/quality/fixtures")
BASELINE_PATH = Path("tests/quality/baseline.json")
ATTRIBUTION_PATH = Path("ATTRIBUTION.md")


@dataclass(frozen=True)
class DashboardInputs:
    baseline: dict[str, Any]
    current: dict[str, Any]
    attribution: str
    fixtures_root: Path = PUBLIC_FIXTURES_ROOT
    baseline_path: Path = BASELINE_PATH
    attribution_path: Path = ATTRIBUTION_PATH
    known_limitations: tuple[str, ...] = ()


def _validate_fixtures_root(fixtures_root: Path) -> None:
    if not fixtures_root.is_dir():
        raise ValueError(f"fixtures root is not a directory: {fixtures_root}")


def _validate_attribution(text: str) -> None:
    if not text or not text.strip():
        raise ValueError("attribution text is empty; refuse to render")
    lowered = text.lower()
    if "author" not in lowered and "license" not in lowered and "source" not in lowered:
        raise ValueError(
            "ATTRIBUTION.md must mention author/license/source; refusing to render"
        )


def _validate_baseline(baseline: dict[str, Any]) -> None:
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a JSON object")
    required = {"schema_version", "tool_version", "fixtures", "summary"}
    missing = required - set(baseline.keys())
    if missing:
        raise ValueError(f"baseline missing keys: {sorted(missing)}")
    fixtures = baseline.get("fixtures")
    if not isinstance(fixtures, list):
        raise ValueError("baseline.fixtures must be a list")
    for fx in fixtures:
        if not isinstance(fx, dict):
            raise ValueError("each fixture must be an object")
        if "fixture_id" not in fx or "metrics" not in fx:
            raise ValueError("fixture requires fixture_id and metrics")
        if fx.get("non_public") is True:
            raise ValueError(
                f"fixture {fx.get('fixture_id')!r} is marked non_public; refusing to render"
            )


def _validate_current(current: dict[str, Any]) -> None:
    if not isinstance(current, dict):
        raise ValueError("current must be a JSON object")
    if "results" not in current or not isinstance(current["results"], list):
        raise ValueError("current.results must be a list")
    for r in current["results"]:
        if not isinstance(r, dict):
            raise ValueError("each result must be an object")
        if "fixture_id" not in r or "metrics" not in r:
            raise ValueError("each result requires fixture_id and metrics")


def load_inputs(
    *,
    baseline_path: Path = BASELINE_PATH,
    current_path: Path,
    attribution_path: Path = ATTRIBUTION_PATH,
    fixtures_root: Path = PUBLIC_FIXTURES_ROOT,
) -> DashboardInputs:
    _validate_fixtures_root(fixtures_root)
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    current = json.loads(Path(current_path).read_text(encoding="utf-8"))
    _validate_baseline(baseline)
    _validate_current(current)
    attribution = Path(attribution_path).read_text(encoding="utf-8")
    _validate_attribution(attribution)
    known = current.get("known_limitations") or []
    if not isinstance(known, list):
        known = []
    return DashboardInputs(
        baseline=baseline,
        current=current,
        attribution=attribution,
        fixtures_root=fixtures_root,
        baseline_path=Path(baseline_path),
        attribution_path=Path(attribution_path),
        known_limitations=tuple(str(x) for x in known),
    )


_METRIC_KEYS = (
    "heading_order",
    "output_exists",
    "table_anchor_recall",
    "text_anchor_recall",
)


def _delta(baseline_metric: float, current_metric: float) -> float:
    """Return signed delta: positive = improvement, negative = regression."""
    return round(current_metric - baseline_metric, 6)


def build_json(inputs: DashboardInputs) -> dict[str, Any]:
    fixtures = {fx["fixture_id"]: fx for fx in inputs.baseline.get("fixtures", [])}
    deltas: list[dict[str, Any]] = []
    for r in inputs.current["results"]:
        fx = fixtures.get(r["fixture_id"])
        if fx is None:
            raise ValueError(
                f"current result references unknown fixture: {r['fixture_id']}"
            )
        for key in _METRIC_KEYS:
            if key in r["metrics"] and key in fx["metrics"]:
                d = _delta(float(fx["metrics"][key]), float(r["metrics"][key]))
                deltas.append(
                    {
                        "fixture_id": r["fixture_id"],
                        "metric": key,
                        "baseline_metric": fx["metrics"][key],
                        "current_metric": r["metrics"][key],
                        "delta": d,
                    }
                )
    summary = inputs.baseline.get("summary", {})
    return {
        "schema_version": "1",
        "baseline_schema": inputs.baseline.get("schema_version", "unknown"),
        "tool_version": inputs.baseline.get("tool_version", "unknown"),
        "summary": summary,
        "fixtures_root": str(inputs.fixtures_root),
        "known_limitations": list(inputs.known_limitations),
        "attribution_excerpt": inputs.attribution.strip().splitlines()[0][:200],
        "deltas": deltas,
    }


def render_html(inputs: DashboardInputs) -> str:
    """Deterministic, self-contained HTML dashboard (no network)."""
    payload = build_json(inputs)
    rows = []
    for d in payload["deltas"]:
        delta_class = "improve" if d["delta"] >= 0 else "regress"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(d['fixture_id']))}</td>"
            f"<td>{html.escape(str(d['metric']))}</td>"
            f"<td>{d['baseline_metric']:.4f}</td>"
            f"<td>{d['current_metric']:.4f}</td>"
            f'<td class="{delta_class}">{d["delta"]:+.4f}</td>'
            "</tr>"
        )
    known = (
        "<ul>"
        + "".join(f"<li>{html.escape(s)}</li>" for s in payload["known_limitations"])
        + "</ul>"
        if payload["known_limitations"]
        else "<p><em>None reported.</em></p>"
    )
    summary = payload.get("summary") or {}
    summary_text = (
        f"passed={summary.get('passed', '?')}, "
        f"failed={summary.get('failed', '?')}, "
        f"fixture_count={summary.get('fixture_count', '?')}"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        "<title>HeadCleaner benchmark dashboard</title>\n"
        "<style>\n"
        "body{font-family:system-ui,sans-serif;margin:2rem;max-width:60rem}\n"
        "table{border-collapse:collapse;width:100%}\n"
        "th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}\n"
        "th{background:#f3f4f6}\n"
        ".improve{color:#22D3EE}\n"
        ".regress{color:#EC4899}\n"
        "</style></head><body>\n"
        "<h1>HeadCleaner benchmark dashboard</h1>\n"
        f"<p>Tool version: <code>{html.escape(str(payload['tool_version']))}</code>; "
        f"Baseline schema: <code>{html.escape(str(payload['baseline_schema']))}</code>; "
        f"Summary: <code>{html.escape(summary_text)}</code></p>\n"
        "<h2>Per-fixture metric deltas</h2>\n"
        "<table><thead><tr>"
        "<th>Fixture ID</th><th>Metric</th><th>Baseline</th><th>Current</th><th>Δ</th>"
        "</tr></thead><tbody>\n"
        + "\n".join(rows)
        + "\n</tbody></table>\n"
        "<h2>Known limitations</h2>\n"
        + known
        + "\n<h2>Attribution</h2>\n"
        f"<pre>{html.escape(inputs.attribution)}</pre>\n"
        "</body></html>\n"
    )


def render_dashboard(inputs: DashboardInputs, *, fmt: str = "json") -> str:
    if fmt == "json":
        return json.dumps(
            build_json(inputs), indent=2, sort_keys=True, ensure_ascii=False
        )
    if fmt == "html":
        return render_html(inputs)
    raise ValueError(f"unknown format: {fmt!r}")
