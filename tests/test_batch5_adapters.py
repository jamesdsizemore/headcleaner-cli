"""Tests for Batch 5 format adapters: epub (#7), rtf (#8), odf (#9), msg (#10)."""

from __future__ import annotations

import zipfile
from pathlib import Path


from headcleaner.engines.epub import EpubAdapter
from headcleaner.engines.odf import OdfAdapter
from headcleaner.engines.rtf import RtfAdapter
from headcleaner.router import get_adapter


# ---------------------------------------------------------------------------
# Eng #8: RTF
# ---------------------------------------------------------------------------


def test_rtf_adapter_handles_simple_file(tmp_path: Path) -> None:
    """RTF: extracts plain text from a hand-rolled RTF file."""
    rtf = tmp_path / "x.rtf"
    rtf.write_bytes(
        b"{\\rtf1\\ansi\\ansicpg1252\\deff0 {\\fonttbl{\\f0 Arial;}}\\f0\\fs24 Hello world.\\par}"
    )
    a = RtfAdapter()
    assert a.supports(rtf)
    out = a.extract(rtf)
    assert "Hello world" in out["body_md"]
    assert out["metadata"]["format"] == "rtf"


def test_rtf_router_dispatches(tmp_path: Path) -> None:
    """RTF: router routes .rtf to RtfAdapter."""
    rtf = tmp_path / "doc.rtf"
    rtf.write_text("hello", encoding="utf-8")
    a = get_adapter(rtf)
    assert a is not None
    assert a.name == "rtf"


# ---------------------------------------------------------------------------
# Eng #9: ODF
# ---------------------------------------------------------------------------


def test_odf_router_dispatches_odt_ods_odp(tmp_path: Path) -> None:
    """ODF: router routes all three ODF extensions."""
    for ext in (".odt", ".ods", ".odp"):
        f = tmp_path / f"doc{ext}"
        f.write_bytes(b"")
        a = get_adapter(f)
        assert a is not None, f"{ext} not routed"
        assert a.name == "odf", f"{ext} routed to {a.name}"


def test_odf_fallback_path_extracts_text(tmp_path: Path) -> None:
    """ODF: when odfpy can't parse (corrupt file), fallback reads content.xml."""
    # Build a fake ODF-like zip that odfpy will reject but the fallback can read
    f = tmp_path / "broken.odt"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr(
            "content.xml", "<text:p>first paragraph</text:p><text:p>second paragraph</text:p>"
        )
    a = OdfAdapter()
    out = a.extract(f)
    assert "first paragraph" in out["body_md"]
    assert "second paragraph" in out["body_md"]
    assert out["metadata"]["format"] == "odf"
    assert out["metadata"].get("fallback") is True


# ---------------------------------------------------------------------------
# Eng #7: EPUB
# ---------------------------------------------------------------------------


def test_epub_router_dispatches(tmp_path: Path) -> None:
    """EPUB: router routes .epub to EpubAdapter."""
    f = tmp_path / "book.epub"
    f.write_bytes(b"")
    a = get_adapter(f)
    assert a is not None
    assert a.name == "epub"


def test_epub_fallback_extracts_chapters(tmp_path: Path) -> None:
    """EPUB: when ebooklib is missing, fallback walks the zip for HTML files."""
    # Build a minimal but non-empty epub-shaped zip
    f = tmp_path / "tiny.epub"
    with zipfile.ZipFile(f, "w") as zf:
        zf.writestr(
            "OEBPS/chap1.xhtml",
            "<html><body><h1>Chapter One</h1><p>It was a dark night.</p></body></html>",
        )
        zf.writestr(
            "OEBPS/chap2.xhtml",
            "<html><body><h2>Chapter Two</h2><p>The sun rose.</p></body></html>",
        )
    a = EpubAdapter()
    # Force fallback path by temporarily removing ebooklib from namespace
    import headcleaner.engines.epub as _epub_mod

    saved = _epub_mod.HAS_EBOOKLIB
    _epub_mod.HAS_EBOOKLIB = False
    try:
        out = a.extract(f)
    finally:
        _epub_mod.HAS_EBOOKLIB = saved
    assert "Chapter One" in out["body_md"]
    assert "dark night" in out["body_md"]
    assert out["metadata"]["format"] == "epub"
    assert out["metadata"].get("fallback") is True


# ---------------------------------------------------------------------------
# Eng #10: MSG
# ---------------------------------------------------------------------------


def test_msg_router_dispatches(tmp_path: Path) -> None:
    """MSG: router routes .msg to MsgAdapter."""
    f = tmp_path / "mail.msg"
    f.write_bytes(b"")
    a = get_adapter(f)
    assert a is not None
    assert a.name == "msg"


def test_msg_adapter_handles_missing_extract_msg(tmp_path: Path) -> None:
    """MSG: returns a clear error string when extract-msg is unavailable."""
    import headcleaner.engines.msg as _msg_mod

    saved = _msg_mod.HAS_EXTRACT_MSG
    _msg_mod.HAS_EXTRACT_MSG = False
    try:
        f = tmp_path / "mail.msg"
        f.write_bytes(b"")
        a = _msg_mod.MsgAdapter()
        out = a.extract(f)
    finally:
        _msg_mod.HAS_EXTRACT_MSG = saved
    assert "extract-msg" in out["body_md"]
    assert out["metadata"]["error"] == "extract-msg missing"


# ---------------------------------------------------------------------------
# Router integration: all 4 new extensions are in the registered set
# ---------------------------------------------------------------------------


def test_router_knows_four_new_extensions() -> None:
    """The router recognizes epub, rtf, odf (3 sub-extensions), and msg."""
    from headcleaner.router import registered_extensions

    exts = registered_extensions()
    assert ".epub" in exts
    assert ".rtf" in exts
    assert ".odt" in exts
    assert ".ods" in exts
    assert ".odp" in exts
    assert ".msg" in exts
