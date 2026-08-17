"""Tests for Eng #3: `headcleaner review` TUI / REPL sign-off."""

from __future__ import annotations

from pathlib import Path


from headcleaner.review import (
    approve,
    iter_pending,
    reject,
    run_review_tui,
)
import yaml


def _write_concept(path: Path, fm: dict, body: str = "Body content.\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{yaml_text}\n---\n{body}", encoding="utf-8")


def test_iter_pending_finds_only_pending(tmp_path: Path) -> None:
    """iter_pending yields only concepts with verified: human:pending."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    _write_concept(
        bundle / "a.md",
        {
            "type": "Document",
            "title": "A",
            "verified": "human:pending",
            "status": "unverified",
        },
    )
    _write_concept(
        bundle / "b.md",
        {
            "type": "Document",
            "title": "B",
            "verified": "human:reviewed",
            "status": "verified",
        },
    )
    _write_concept(
        bundle / "c.md",
        {
            "type": "Document",
            "title": "C",
            "verified": "human:pending",
            "status": "unverified",
        },
    )
    paths = list(iter_pending(bundle))
    names = sorted(p.name for p in paths)
    assert names == ["a.md", "c.md"]


def test_approve_flips_verified_and_status(tmp_path: Path) -> None:
    """approve() sets verified: human:reviewed and status: verified."""
    p = tmp_path / "x.md"
    _write_concept(
        p,
        {
            "type": "Document",
            "title": "X",
            "verified": "human:pending",
            "status": "unverified",
        },
    )
    approve(p)
    fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---")[1])
    assert fm["verified"] == "human:reviewed"
    assert fm["status"] == "verified"
    assert fm["reviewed_by"] == "human"
    assert fm["reviewed_via"] == "headcleaner review"
    assert "reviewed_at" in fm


def test_reject_flips_verified_and_status(tmp_path: Path) -> None:
    """reject() sets verified: human:rejected and status: rejected."""
    p = tmp_path / "x.md"
    _write_concept(
        p,
        {
            "type": "Document",
            "title": "X",
            "verified": "human:pending",
            "status": "unverified",
        },
    )
    reject(p, reasons=["bad data", "needs source"])
    fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---")[1])
    assert fm["verified"] == "human:rejected"
    assert fm["status"] == "rejected"
    assert fm["rejection_reasons"] == ["bad data", "needs source"]


def test_review_tui_no_pending_returns_zero(tmp_path: Path) -> None:
    """run_review_tui returns zeros when no pending concepts exist."""
    bundle = tmp_path / "okf"
    bundle.mkdir()
    summary = run_review_tui(bundle)
    assert summary == {"approved": 0, "rejected": 0, "skipped": 0, "quit": 1}
