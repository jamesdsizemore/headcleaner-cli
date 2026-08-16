"""Tests for Batch 4 features: log.md (#37), enriched index (#38), bundle
manifest (#39), crossref (#34), policy (#35), git_commit (#32), themes (#40),
json output (#43), dry-run (#42)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from headcleaner import theme as theme_mod
from headcleaner.bundle_manifest import write_bundle_manifest
from headcleaner.crossref import linkify_bundle
from headcleaner.emit import okf_index
from headcleaner.git_commit import find_repo_root
from headcleaner.jsonlog import emit_json_event
from headcleaner.policy import Policy, evaluate


# ---------------------------------------------------------------------------
# Eng #37: log.md
# ---------------------------------------------------------------------------

def test_log_md_appends_entry(tmp_path: Path) -> None:
    """Eng #37: append_log_entry creates log.md with the expected sections."""
    # Build a fake record (RunRecord-like)
    from dataclasses import dataclass, field
    @dataclass
    class FakeResult:
        relpath: str
        status: str
        engine: str = "txt"
        error: str | None = None
    @dataclass
    class FakeRecord:
        version: str = "0.5.0"
        finished_at: str = "2026-08-16T10:00:00Z"
        format: str = "both"
        results: list = field(default_factory=list)
    rec = FakeRecord(results=[
        FakeResult("a.txt", "ok"),
        FakeResult("b.txt", "failed", engine="pdf", error="bad PDF"),
    ])
    okf_index.append_log_entry(tmp_path, rec)
    log_path = tmp_path / "log.md"
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "Bundle history" in text
    assert "headcleaner 0.5.0" in text
    assert "`txt`: 1 ok" in text
    assert "`pdf`: 1 failed" in text
    assert "b.txt: bad PDF" in text


def test_log_md_is_idempotent(tmp_path: Path) -> None:
    """Eng #37: running twice appends two entries, doesn't overwrite."""
    from dataclasses import dataclass, field
    @dataclass
    class FakeResult:
        relpath: str = "x.txt"
        status: str = "ok"
        engine: str = "txt"
    @dataclass
    class FakeRecord:
        version: str = "0.5.0"
        finished_at: str = "2026-08-16T10:00:00Z"
        format: str = "both"
        results: list = field(default_factory=list)
    rec1 = FakeRecord(results=[FakeResult()])
    rec2 = FakeRecord(finished_at="2026-08-16T11:00:00Z", results=[FakeResult()])
    okf_index.append_log_entry(tmp_path, rec1)
    okf_index.append_log_entry(tmp_path, rec2)
    text = (tmp_path / "log.md").read_text(encoding="utf-8")
    assert text.count("## 2026-08-16T10:00:00Z") == 1
    assert text.count("## 2026-08-16T11:00:00Z") == 1


# ---------------------------------------------------------------------------
# Eng #38: enriched index.md
# ---------------------------------------------------------------------------

def test_enriched_index_includes_word_count(tmp_path: Path) -> None:
    """Eng #38: enriched index shows word count + description."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    # Make a tiny concept
    (bundle / "doc1.md").write_text(
        "---\ntype: Document\ntitle: Doc One\ndescription: First document\n"
        "status: unverified\n---\nThis is a tiny body with eight words here.\n",
        encoding="utf-8",
    )
    n = okf_index.generate(bundle, enriched=True)
    assert n == 1
    idx = (bundle / "index.md").read_text(encoding="utf-8")
    assert "Doc One" in idx
    assert "First document" in idx
    assert "words" in idx


# ---------------------------------------------------------------------------
# Eng #39: bundle manifest
# ---------------------------------------------------------------------------

def test_bundle_manifest_aggregates(tmp_path: Path) -> None:
    """Eng #39: write_bundle_manifest merges engine counts across runs."""
    from dataclasses import dataclass, field
    @dataclass
    class FakeResult:
        relpath: str
        status: str
        engine: str
    @dataclass
    class FakeRecord:
        version: str = "0.5.0"
        finished_at: str = "2026-08-16T10:00:00Z"
        format: str = "both"
        input_root: str = "/tmp/in"
        output_root: str = str(tmp_path)
        results: list = field(default_factory=list)

    rec1 = FakeRecord(finished_at="2026-08-16T10:00:00Z", results=[
        FakeResult("a.txt", "ok", "txt"),
        FakeResult("b.docx", "ok", "officecli"),
    ])
    rec2 = FakeRecord(finished_at="2026-08-16T11:00:00Z", results=[
        FakeResult("c.pdf", "ok", "pdf"),
        FakeResult("d.docx", "ok", "officecli"),
    ])
    write_bundle_manifest(tmp_path, rec1)
    write_bundle_manifest(tmp_path, rec2)

    bm = json.loads((tmp_path / "bundle.manifest.json").read_text(encoding="utf-8"))
    assert bm["concept_count"] == 4
    assert bm["engine_counts"]["officecli"] == 2  # merged
    assert bm["engine_counts"]["txt"] == 1
    assert bm["engine_counts"]["pdf"] == 1
    assert len(bm["recent_runs"]) == 2


# ---------------------------------------------------------------------------
# Eng #34: cross-concept link inference
# ---------------------------------------------------------------------------

def test_crossref_links_titles(tmp_path: Path) -> None:
    """Eng #34: linkify_bundle rewrites a mention of concept title to a link."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    (bundle / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\nstatus: unverified\n---\nAlpha body.\n",
        encoding="utf-8",
    )
    (bundle / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\nstatus: unverified\n---\n"
        "See Alpha for context.\n",
        encoding="utf-8",
    )
    n = linkify_bundle(bundle)
    assert n == 1
    text = (bundle / "beta.md").read_text(encoding="utf-8")
    assert "[Alpha](alpha.md)" in text


def test_crossref_is_idempotent(tmp_path: Path) -> None:
    """Eng #34: running linkify twice doesn't double-wrap."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    (bundle / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\n---\nAlpha body.\n",
        encoding="utf-8",
    )
    (bundle / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\n---\nAlpha is good.\n",
        encoding="utf-8",
    )
    linkify_bundle(bundle)
    first = (bundle / "beta.md").read_text(encoding="utf-8")
    linkify_bundle(bundle)
    second = (bundle / "beta.md").read_text(encoding="utf-8")
    assert first == second


# ---------------------------------------------------------------------------
# Eng #35: trust policy
# ---------------------------------------------------------------------------

def test_policy_load_and_evaluate(tmp_path: Path) -> None:
    """Eng #35: Policy.load reads TOML, evaluate() emits findings."""
    (tmp_path / "policy.toml").write_text(textwrap.dedent("""
        [policy]
        require_type = "Document"
        require_status = ["unverified"]
        require_verified = ["human:pending"]
        require_sources = true
        require_sha256 = true
    """).strip(), encoding="utf-8")

    bundle = tmp_path / "okf"
    bundle.mkdir()
    (bundle / "ok.md").write_text(
        "---\ntype: Document\ntitle: OK\nstatus: unverified\n"
        "verified: human:pending\nsources:\n"
        "  - uri: file://a.txt\n    sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n"
        "---\nBody.\n",
        encoding="utf-8",
    )
    (bundle / "bad.md").write_text(
        "---\ntype: Document\ntitle: Bad\nstatus: archived\nverified: human:reviewed\n---\nBody.\n",
        encoding="utf-8",
    )
    pol = Policy.load(tmp_path / "policy.toml")
    findings = evaluate(pol, bundle)
    assert len(findings) >= 3  # bad has status, verified, and sources violations
    rules = {f.rule for f in findings}
    assert "policy/status" in rules
    assert "policy/verified" in rules
    assert "policy/sources" in rules


# ---------------------------------------------------------------------------
# Eng #32: git-backed bundle
# ---------------------------------------------------------------------------

def test_find_repo_root_walks_up(tmp_path: Path) -> None:
    """Eng #32: find_repo_root walks up until it finds .git."""
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "sub" / "deep"
    sub.mkdir(parents=True)
    repo = find_repo_root(sub)
    assert repo is not None
    assert repo.resolve() == tmp_path.resolve()


def test_find_repo_root_returns_none_outside(tmp_path: Path) -> None:
    """Eng #32: returns None when no .git ancestor."""
    sub = tmp_path / "no" / "git"
    sub.mkdir(parents=True)
    assert find_repo_root(sub) is None


# ---------------------------------------------------------------------------
# Eng #40: theme switching
# ---------------------------------------------------------------------------

def test_theme_switch_round_trip() -> None:
    """Eng #40: set_theme mutates module-level constants and accepts all 4 names."""
    theme_mod.set_theme("neon")
    neon_cyan = theme_mod.NEON_CYAN
    assert neon_cyan == "#22D3EE"

    theme_mod.set_theme("light")
    assert theme_mod.NEON_CYAN == "#0EA5E9"
    assert theme_mod.BG_BLACK == "#FFFFFF"

    theme_mod.set_theme("dark")
    assert theme_mod.BG_BLACK.startswith("#")

    theme_mod.set_theme("mono")
    assert theme_mod.NEON_PINK == "#FFFFFF"

    # Restore
    theme_mod.set_theme("neon")
    assert theme_mod.NEON_CYAN == "#22D3EE"


def test_theme_unknown_raises() -> None:
    """Eng #40: set_theme with unknown name raises ValueError."""
    with pytest.raises(ValueError):
        theme_mod.set_theme("chartreuse")


# ---------------------------------------------------------------------------
# Eng #43: json output (smoke test of the emit helper)
# ---------------------------------------------------------------------------

def test_emit_json_event_writes_one_line(capsys) -> None:
    """Eng #43: emit_json_event writes one JSON-serializable line + flushes."""
    emit_json_event({"event": "test", "n": 42})
    out = capsys.readouterr().out
    assert out.endswith("\n")
    obj = json.loads(out)
    assert obj == {"event": "test", "n": 42}


# ---------------------------------------------------------------------------
# Eng #42: dry-run (full pipeline level)
# ---------------------------------------------------------------------------

def test_dry_run_writes_no_files(tmp_path: Path) -> None:
    """Eng #42: dry_run=True means no _md/ or okf/ files are written."""
    from headcleaner.run import RunOptions, run_pipeline
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "out"
    in_dir.mkdir()
    (in_dir / "hello.txt").write_text("Hello world, this is content.\n", encoding="utf-8")
    rec = run_pipeline(RunOptions(
        input_root=in_dir,
        output_root=out_dir,
        fmt="both",
        dry_run=True,
    ))
    assert rec.results, "should have results"
    # No files written
    assert not (out_dir / "_md").exists() or not list((out_dir / "_md").iterdir())
    assert not (out_dir / "okf").exists() or not list((out_dir / "okf").iterdir())
    assert not (out_dir / "manifest.json").exists()
    # But the result still records "ok" with computed md_path / okf_path
    ok_results = [r for r in rec.results if r.status == "ok"]
    assert ok_results


# imports at the top for the policy test
import textwrap