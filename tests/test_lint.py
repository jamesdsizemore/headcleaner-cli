"""Tests for the post-conversion linter (lint.py)."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from headcleaner.lint import (
    LintSummary,
    Severity,
    check_markdown,
    check_okf,
    lint_directory,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _okf_ok(relpath: str = "x.txt") -> str:
    """Minimal valid OKF concept."""
    return textwrap.dedent(f"""\
        ---
        type: Document
        title: Sample
        description: Document derived from {relpath} via officecli.
        resource: file:///C:/tmp/{relpath}
        tags: [txt]
        status: unverified
        stale_after: '2027-02-15'
        sources:
          - uri: file:///C:/tmp/{relpath}
            kind: file
            sha256: 8c2f5d6e9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d
        generated: human:tester@host
        verified: human:pending
        ---

        # Sample

        Body content here.
        """)


# --- OKF rules --------------------------------------------------------------

def test_okf_passes_clean(tmp_path: Path) -> None:
    _write(tmp_path / "okf" / "x.md", _okf_ok())
    s = lint_directory(tmp_path)
    assert s.errors == 0, [f.format() for f in s.findings if f.severity == Severity.ERROR]


def test_okf_missing_type(tmp_path: Path) -> None:
    bad = "---\ntitle: x\n---\n\n# Body\n"
    _write(tmp_path / "okf" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert s.errors >= 1
    assert any(f.rule == "okf/type-required" for f in s.findings)


def test_okf_bad_sha256(tmp_path: Path) -> None:
    bad = _okf_ok().replace(
        "sha256: 8c2f5d6e9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d",
        "sha256: not-hex",
    )
    _write(tmp_path / "okf" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "okf/sources-sha256" for f in s.findings)


def test_okf_resource_not_file_uri(tmp_path: Path) -> None:
    bad = _okf_ok().replace("file:///C:/tmp/x.txt", "https://example.com/x.txt")
    _write(tmp_path / "okf" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "okf/resource-uri" for f in s.findings)


def test_okf_missing_status_warns(tmp_path: Path) -> None:
    bad = _okf_ok().replace("status: unverified\n", "")
    _write(tmp_path / "okf" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "okf/status-missing" for f in s.findings)
    assert s.warnings >= 1


def test_okf_empty_body(tmp_path: Path) -> None:
    bad = _okf_ok().replace("# Sample\n\nBody content here.\n", "")
    _write(tmp_path / "okf" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "okf/body-empty" for f in s.findings)


def test_okf_index_md_skipped(tmp_path: Path) -> None:
    _write(tmp_path / "okf" / "index.md", "# Documents\n\n- [a](a.md)\n")
    s = lint_directory(tmp_path)
    # index.md is generated; should produce zero findings even if not OKF-shaped
    assert s.errors == 0


# --- Markdown rules ---------------------------------------------------------

def test_md_orphan_fence(tmp_path: Path) -> None:
    bad = "---\ntitle: x\n---\n\n```text\nunclosed\n"
    _write(tmp_path / "_md" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "md/code-fence-orphan" for f in s.findings)


def test_md_heading_skip(tmp_path: Path) -> None:
    bad = "# H1\n\n### H3\n"
    _write(tmp_path / "_md" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "md/heading-skip" for f in s.findings)


def test_md_no_frontmatter_warns(tmp_path: Path) -> None:
    _write(tmp_path / "_md" / "x.md", "Just plain markdown.\n")
    s = lint_directory(tmp_path)
    assert any(f.rule == "md/frontmatter-missing" for f in s.findings)


def test_md_long_line_info(tmp_path: Path) -> None:
    bad = "---\ntitle: x\n---\n\n" + ("x" * 250) + "\n"
    _write(tmp_path / "_md" / "x.md", bad)
    s = lint_directory(tmp_path)
    assert any(f.rule == "md/line-length" for f in s.findings)


# --- Summary driver ---------------------------------------------------------

def test_lint_summary_counts(tmp_path: Path) -> None:
    _write(tmp_path / "okf" / "a.md", _okf_ok("a.txt"))
    _write(tmp_path / "okf" / "b.md", _okf_ok("b.txt"))
    bad = "---\ntitle: x\n---\n\nbody\n"  # missing type
    _write(tmp_path / "okf" / "c.md", bad)
    s = lint_directory(tmp_path)
    assert s.scanned == 3
    assert s.errors >= 1


def test_lint_directory_handles_missing_root(tmp_path: Path) -> None:
    s = lint_directory(tmp_path / "does-not-exist")
    assert s.scanned == 0
