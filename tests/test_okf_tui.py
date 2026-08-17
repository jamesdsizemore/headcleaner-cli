"""Tests for the OKF TUI viewer (v0.12.0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from headcleaner.okf_tui import (
    _clip,
    _strip_frontmatter,
    _term_size,
    _trust_badge,
    render_frame,
    run_tui,
)


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    d = tmp_path / "okf"
    d.mkdir(parents=True, exist_ok=True)
    (d / "concepts").mkdir(parents=True, exist_ok=True)
    (d / "concepts" / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\ndescription: First concept\nstatus: unverified\n"
        "verified: human:pending\nstale_after: 2099-01-01\n---\n\n"
        "# Alpha\n\nThis concept links to [beta](beta.md).",
        encoding="utf-8",
    )
    (d / "concepts" / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\ndescription: Second\n"
        "verified:\n  - {by: human:alice, at: 2026-08-01}\n---\n\n# Beta",
        encoding="utf-8",
    )
    (d / "concepts" / "gamma.md").write_text(
        "---\ntype: Document\ntitle: Gamma\n---\n\n# Gamma\n\nStandalone.",
        encoding="utf-8",
    )
    return d


def test_term_size_returns_int_tuple():
    r, c = _term_size()
    assert isinstance(r, int) and isinstance(c, int)
    assert r > 0 and c > 0


def test_clip_short_string_unchanged():
    assert _clip("hello", 10) == "hello"


def test_clip_exact_length_unchanged():
    assert _clip("hello", 5) == "hello"


def test_clip_too_long_gets_ellipsis():
    out = _clip("hello world", 6)
    assert out.endswith("…")
    assert len(out) == 6


def test_clip_zero_width_empty():
    assert _clip("anything", 0) == ""


def test_trust_badge_unverified():
    assert _trust_badge({}, "2026-01-01") == "unverified"


def test_trust_badge_human_reviewed():
    n = {"verified": [{"by": "human:alice", "at": "2026-08-01"}]}
    assert _trust_badge(n, "2026-01-01") == "human-reviewed"


def test_trust_badge_machine_confirmed():
    n = {"verified": [{"by": "ci-bot", "at": "2026-08-01"}]}
    assert _trust_badge(n, "2026-01-01") == "machine-confirmed"


def test_trust_badge_stale_flag():
    n = {"verified": [], "stale_after": "2020-01-01"}
    out = _trust_badge(n, "2026-08-16")
    assert "stale" in out
    assert "2020-01-01" in out


def test_trust_badge_deprecated_flag():
    n = {"verified": [], "status": "deprecated"}
    assert "deprecated" in _trust_badge(n, "2026-08-16")


def test_strip_frontmatter_removes_yaml_block():
    text = "---\nkey: value\n---\nbody"
    assert _strip_frontmatter(text) == "body"


def test_strip_frontmatter_no_frontmatter_passthrough():
    assert _strip_frontmatter("# Title\n\nbody") == "# Title\n\nbody"


def test_render_frame_returns_string(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100)
    assert isinstance(frame, str)
    # 24 rows + trailing newline (one extra entry from splitlines)
    assert len(frame.splitlines()) in (24, 25)


def test_render_frame_header_mentions_concepts(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100)
    assert "3 concepts" in frame
    assert "1 links" in frame  # only alpha→beta (beta has no body link, gamma is standalone)


def test_render_frame_lists_titles(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100)
    assert "Alpha" in frame
    assert "Beta" in frame
    assert "Gamma" in frame


def test_render_frame_marks_selected(bundle: Path):
    """The selected row gets a ▶ marker; others get blank."""
    frame = render_frame(bundle, rows=24, cols=100, selected=0)
    # First non-header row should have ▶ marker on Alpha
    rows = frame.splitlines()
    # header + separator + body... find Alpha row
    alpha_row = next(r for r in rows if "Alpha" in r)
    assert "▶" in alpha_row


def test_render_frame_selection_with_filter(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100, filter_query="beta")
    assert "Beta" in frame
    assert "Alpha" not in frame.split("\n", 3)[3]  # body section


def test_render_frame_shows_trust_in_detail(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100, selected=0)
    # Alpha has no verified entries → unverified
    assert "unverified" in frame


def test_render_frame_shows_human_reviewed(bundle: Path):
    frame = render_frame(bundle, rows=24, cols=100, selected=1)
    # Beta has human:alice → human-reviewed
    assert "human-reviewed" in frame


def test_render_frame_constant_width_rows(bundle: Path):
    """Every row in the rendered frame must be exactly `cols` wide (the
    whole-frame paint assumption from serradura/okf-tui)."""
    cols = 100
    frame = render_frame(bundle, rows=24, cols=cols)
    for i, line in enumerate(frame.splitlines()):
        assert len(line) == cols, f"row {i} is {len(line)} chars, expected {cols}: {line!r}"


def test_render_frame_handles_empty_bundle(tmp_path: Path):
    d = tmp_path / "empty"
    d.mkdir()
    frame = render_frame(d, rows=24, cols=80)
    assert "0 concepts" in frame


def test_render_frame_clamps_selection_to_visible(bundle: Path):
    """If selection is out of range after filtering, clamp to 0."""
    frame = render_frame(bundle, rows=24, cols=100, selected=99, filter_query="beta")
    # Only Beta visible; selection should land on Beta
    assert "▶" in frame
    assert "Beta" in frame


def test_run_tui_non_tty_prints_and_returns(tmp_path: Path, capsys):
    """Non-TTY stdout: print once and exit cleanly."""
    d = tmp_path / "okf"
    d.mkdir(parents=True, exist_ok=True)
    (d / "x.md").write_text("---\ntype: Doc\ntitle: X\n---\n\nbody", encoding="utf-8")
    rc = run_tui(d)
    assert rc == 0
    captured = capsys.readouterr()
    assert "1 concepts" in captured.out
