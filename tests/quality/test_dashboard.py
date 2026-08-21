"""Tests for the public benchmark transparency dashboard (Contract 3.8)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from headcleaner.benchmark_dashboard import (
    PUBLIC_FIXTURES_ROOT,
    build_json,
    load_inputs,
    render_dashboard,
    render_html,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def public_fixtures_root(tmp_path: Path) -> Path:
    """A clean public fixtures root with a single fixture."""
    root = tmp_path / "tests" / "quality" / "fixtures"
    root.mkdir(parents=True)
    (root / "alpha.txt").write_text("Hello world\n", encoding="utf-8")
    (root / "ATTRIBUTION.md").write_text(
        "# Attribution\n- Author: test\n- License: Apache-2.0\n- Source: synthetic\n",
        encoding="utf-8",
    )
    return root


def _write_baseline(path: Path, *, schema: str = "1.0") -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": schema,
                "tool_version": "0.14.0",
                "fixtures": [
                    {
                        "fixture_id": "alpha.txt",
                        "metrics": {
                            "heading_order": 1.0,
                            "output_exists": 1.0,
                            "text_anchor_recall": 1.0,
                        },
                    }
                ],
                "summary": {"fixture_count": 1, "passed": 1, "failed": 0},
            }
        ),
        encoding="utf-8",
    )


def _write_current(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "fixture_id": "alpha.txt",
                        "metrics": {
                            "heading_order": 1.0,
                            "output_exists": 1.0,
                            "text_anchor_recall": 0.5,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _write_attribution(path: Path) -> None:
    path.write_text(
        "# Attribution\n- Author: test\n- License: Apache-2.0\n- Source: synthetic\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Rejection
# ---------------------------------------------------------------------------


def test_rejects_attribution_missing_author_license_source(tmp_path: Path) -> None:
    bad_att = tmp_path / "ATTRIBUTION.md"
    bad_att.write_text("# Hi\n", encoding="utf-8")
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    _write_baseline(base)
    _write_current(cur)
    with pytest.raises(ValueError, match="author/license/source"):
        load_inputs(
            baseline_path=base,
            current_path=cur,
            attribution_path=bad_att,
            fixtures_root=fx_root,
        )


def test_rejects_empty_attribution(tmp_path: Path) -> None:
    bad_att = tmp_path / "ATTRIBUTION.md"
    bad_att.write_text("   \n", encoding="utf-8")
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    _write_baseline(base)
    _write_current(cur)
    with pytest.raises(ValueError, match="empty"):
        load_inputs(
            baseline_path=base,
            current_path=cur,
            attribution_path=bad_att,
            fixtures_root=fx_root,
        )


def test_rejects_baseline_marking_fixture_non_public(tmp_path: Path) -> None:
    base = tmp_path / "baseline.json"
    base.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "tool_version": "0.14.0",
                "fixtures": [
                    {
                        "fixture_id": "secret.txt",
                        "non_public": True,
                        "metrics": {"output_exists": 1.0},
                    }
                ],
                "summary": {"fixture_count": 1, "passed": 0, "failed": 1},
            }
        ),
        encoding="utf-8",
    )
    cur = tmp_path / "current.json"
    _write_current(cur)
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    with pytest.raises(ValueError, match="non_public"):
        load_inputs(
            baseline_path=base,
            current_path=cur,
            attribution_path=tmp_path / "ATTRIBUTION.md",
            fixtures_root=fx_root,
        )


def test_rejects_current_result_referencing_unknown_fixture(tmp_path: Path) -> None:
    base = tmp_path / "baseline.json"
    _write_baseline(base)
    cur = tmp_path / "current.json"
    cur.write_text(
        json.dumps({"results": [{"fixture_id": "ghost.txt", "metrics": {"x": 1.0}}]}),
        encoding="utf-8",
    )
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    att = tmp_path / "ATTRIBUTION.md"
    _write_attribution(att)
    inputs = load_inputs(
        baseline_path=base,
        current_path=cur,
        attribution_path=att,
        fixtures_root=fx_root,
    )
    with pytest.raises(ValueError, match="unknown fixture"):
        build_json(inputs)


def test_rejects_baseline_missing_required_keys(tmp_path: Path) -> None:
    base = tmp_path / "baseline.json"
    base.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
    cur = tmp_path / "current.json"
    _write_current(cur)
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    with pytest.raises(ValueError, match="missing keys"):
        load_inputs(
            baseline_path=base,
            current_path=cur,
            attribution_path=tmp_path / "ATTRIBUTION.md",
            fixtures_root=fx_root,
        )


# ---------------------------------------------------------------------------
# Determinism + content
# ---------------------------------------------------------------------------


def _full_inputs(tmp_path: Path):
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    att = tmp_path / "ATTRIBUTION.md"
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    _write_baseline(base)
    _write_current(cur)
    _write_attribution(att)
    return load_inputs(
        baseline_path=base,
        current_path=cur,
        attribution_path=att,
        fixtures_root=fx_root,
    )


def test_render_json_is_deterministic(tmp_path: Path) -> None:
    inputs = _full_inputs(tmp_path)
    a = render_dashboard(inputs, fmt="json")
    b = render_dashboard(inputs, fmt="json")
    assert a == b


def test_render_html_excludes_timestamps_and_is_self_contained(tmp_path: Path) -> None:
    inputs = _full_inputs(tmp_path)
    html_out = render_html(inputs)
    assert "http://" not in html_out
    assert "<script" not in html_out
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", html_out)


def test_render_html_escapes_fixture_labels(tmp_path: Path) -> None:
    base = tmp_path / "baseline.json"
    cur = tmp_path / "current.json"
    att = tmp_path / "ATTRIBUTION.md"
    fx_root = tmp_path / "fixtures"
    fx_root.mkdir()
    base.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "tool_version": "0.14.0",
                "fixtures": [
                    {
                        "fixture_id": "<script>alert(1)</script>",
                        "metrics": {"output_exists": 1.0},
                    }
                ],
                "summary": {"fixture_count": 1, "passed": 1, "failed": 0},
            }
        ),
        encoding="utf-8",
    )
    cur.write_text(
        json.dumps(
            {"results": [{"fixture_id": "<script>alert(1)</script>", "metrics": {"output_exists": 0.5}}]}
        ),
        encoding="utf-8",
    )
    _write_attribution(att)
    inputs = load_inputs(
        baseline_path=base,
        current_path=cur,
        attribution_path=att,
        fixtures_root=fx_root,
    )
    html_out = render_html(inputs)
    assert "&lt;script&gt;" in html_out
    assert "<script>alert(1)</script>" not in html_out


def test_render_html_includes_engine_versions_platform_schema(tmp_path: Path) -> None:
    inputs = _full_inputs(tmp_path)
    html_out = render_html(inputs)
    assert "Baseline schema" in html_out
    assert "Tool version" in html_out


def test_delta_direction_is_signed_correctly(tmp_path: Path) -> None:
    inputs = _full_inputs(tmp_path)
    payload = build_json(inputs)
    recall = next(d for d in payload["deltas"] if d["metric"] == "text_anchor_recall")
    assert recall["delta"] == pytest.approx(-0.5, abs=1e-9)


def test_no_network_calls_in_renderer(tmp_path: Path) -> None:
    """Static check: the renderer must not import networking modules."""
    import headcleaner.benchmark_dashboard as bd

    src = Path(bd.__file__).read_text(encoding="utf-8")
    for forbidden in ("urllib.request", "requests.", "httpx.", "socket.socket"):
        assert forbidden not in src, f"forbidden network import: {forbidden}"


def test_public_fixtures_root_constant_points_inside_repo() -> None:
    resolved = PUBLIC_FIXTURES_ROOT.resolve()
    assert "tests/quality/fixtures" in str(resolved).replace("\\", "/")
