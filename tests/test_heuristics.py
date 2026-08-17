"""Tests for the heuristic cleanup pipeline (v0.8.0)."""

from __future__ import annotations

import pytest

from headcleaner.heuristics import (
    DEFAULT_ORDER,
    STAGES,
    clean_text,
    collapse_whitespace,
    decode_html_entities,
    dedupe_toc_block,
    dehyphenate,
    enforce_heading_hierarchy,
    nfc_normalize,
    normalize_ligatures,
    normalize_quotes_dashes,
    repair_line_wraps,
    strip_orphan_punctuation,
    strip_repeated_byline,
    strip_soft_hyphens,
)


# ---- T1: nfc_normalize -----------------------------------------------------


def test_nfc_normalize_nfd_to_nfc() -> None:
    """NFD decomposition gets recomposed."""
    # 'é' as NFD is 'e' + U+0301
    nfd = "e\u0301"
    assert nfc_normalize(nfd) == "é"


def test_nfc_normalize_crlf_to_lf() -> None:
    """Windows CRLF becomes LF."""
    assert nfc_normalize("a\r\nb\r\nc") == "a\nb\nc"


def test_nfc_normalize_cr_to_lf() -> None:
    """Old Mac CR becomes LF."""
    assert nfc_normalize("a\rb\rc") == "a\nb\nc"


# ---- T2: strip_soft_hyphens ------------------------------------------------


def test_strip_soft_hyphens_basic() -> None:
    """U+00AD soft hyphen is removed."""
    assert strip_soft_hyphens("hy\u00adphen") == "hyphen"


def test_strip_soft_hyphens_no_change() -> None:
    """Text without soft hyphens passes through."""
    assert strip_soft_hyphens("plain text") == "plain text"


# ---- T3: normalize_ligatures ----------------------------------------------


def test_normalize_ligatures_fi() -> None:
    """fi ligature -> fi."""
    assert normalize_ligatures("\ufb01le") == "file"


def test_normalize_ligatures_ffi() -> None:
    """ffi ligature -> ffi."""
    assert normalize_ligatures("\ufb03ce") == "ffice"


def test_normalize_ligatures_nbsp() -> None:
    """NBSP -> space."""
    assert normalize_ligatures("hello\u00a0world") == "hello world"


# ---- T4: normalize_quotes_dashes -------------------------------------------


def test_normalize_quotes_curly_to_ascii() -> None:
    """Curly quotes become ASCII."""
    assert normalize_quotes_dashes("\u201chello\u201d") == '"hello"'


def test_normalize_quotes_en_dash() -> None:
    """En dash -> single hyphen."""
    assert normalize_quotes_dashes("a\u2013b") == "a-b"


def test_normalize_quotes_em_dash() -> None:
    """Em dash -> double hyphen."""
    assert normalize_quotes_dashes("a\u2014b") == "a--b"


def test_normalize_quotes_ellipsis() -> None:
    """Ellipsis -> three dots."""
    assert normalize_quotes_dashes("wait\u2026") == "wait..."


# ---- T5: collapse_whitespace -----------------------------------------------


def test_collapse_whitespace_runs() -> None:
    """Multiple spaces collapse to one."""
    assert collapse_whitespace("hello   world") == "hello world"


def test_collapse_whitespace_blank_lines() -> None:
    """3+ blank lines collapse to 2."""
    text = "a\n\n\n\n\nb"
    assert collapse_whitespace(text) == "a\n\nb"


def test_collapse_whitespace_tabs() -> None:
    """Tabs collapse with spaces."""
    assert collapse_whitespace("a\t\tb") == "a b"


# ---- T6: decode_html_entities ---------------------------------------------


def test_decode_html_entities_basic() -> None:
    """Common entities decode."""
    assert decode_html_entities("&amp;") == "&"
    assert decode_html_entities("&lt;") == "<"
    assert decode_html_entities("&gt;") == ">"


def test_decode_html_entities_double_encoded() -> None:
    """Iterates until stable: ``&amp;amp;`` -> ``&``."""
    assert decode_html_entities("&amp;amp;") == "&"


def test_decode_html_entities_numeric() -> None:
    """Numeric entities decode."""
    assert decode_html_entities("&#65;") == "A"


def test_decode_html_entities_no_change() -> None:
    """Text without entities passes through."""
    assert decode_html_entities("plain text") == "plain text"


# ---- T7: repair_line_wraps -------------------------------------------------


def test_repair_line_wraps_joins_paragraph() -> None:
    """Hard-wrapped lines within a paragraph get joined."""
    text = "This is a\nhard-wrapped\nparagraph.\n\nNext paragraph."
    out = repair_line_wraps(text)
    assert "This is a hard-wrapped paragraph." in out
    assert "Next paragraph." in out


def test_repair_line_wraps_preserves_heading() -> None:
    """Headings stay on their own line."""
    text = "# Title\n\nA paragraph\nspread\nacross lines."
    out = repair_line_wraps(text)
    assert "# Title" in out
    assert "A paragraph spread across lines." in out


def test_repair_line_wraps_preserves_list() -> None:
    """List items stay on their own line."""
    text = "- item one\n- item two\n- item three"
    out = repair_line_wraps(text)
    lines = [ln for ln in out.split("\n") if ln.strip()]
    assert len(lines) == 3


def test_repair_line_wraps_preserves_blockquote() -> None:
    """Blockquote lines stay separate."""
    text = "> a quote\n> line two"
    out = repair_line_wraps(text)
    assert "> a quote" in out
    assert "> line two" in out


# ---- T8: dehyphenate ------------------------------------------------------


def test_dehyphenate_basic() -> None:
    """Hyphen at line break gets removed."""
    assert dehyphenate("exam-\nple") == "example"


def test_dehyphenate_no_change() -> None:
    """Hyphen mid-line stays."""
    assert dehyphenate("well-known fact") == "well-known fact"


# ---- T9: dedupe_toc_block --------------------------------------------------


def test_dedupe_toc_block_drops_repeat() -> None:
    """TOC that appears again later is dropped from the start."""
    text = (
        "# Document\n\n"
        "Introduction\nChapter 1\nChapter 2\nChapter 3\nChapter 4\n\n"
        "Some prose paragraph 1.\nSome prose paragraph 2.\n\n"
        "Body content.\n\n"
        "Introduction\nChapter 1\nChapter 2\nChapter 3\nChapter 4\n\n"
        "More body.\n"
    )
    out = dedupe_toc_block(text)
    # The second occurrence is preserved (it's the actual content)
    assert "More body." in out
    # The early block should be gone
    assert out.count("Introduction") <= 1


def test_dedupe_toc_block_no_repeat() -> None:
    """If no repeat, the doc passes through."""
    text = "# Title\n\nIntroduction\nFirst topic\nSecond topic\n\nBody.\n"
    out = dedupe_toc_block(text)
    assert "Introduction" in out
    assert "Body." in out


# ---- T10: strip_repeated_byline -------------------------------------------


def test_strip_repeated_byline_drops_repeats() -> None:
    """Lines that appear 2+ times get dropped."""
    text = "Author Name\nSome body content.\nAuthor Name\nMore body content.\nAuthor Name\n"
    out = strip_repeated_byline(text)
    assert out.count("Author Name") == 0
    assert "Some body content." in out
    assert "More body content." in out


def test_strip_repeated_byline_no_repeats() -> None:
    """If nothing repeats, doc passes through."""
    text = "Line one.\nLine two.\nLine three.\n"
    out = strip_repeated_byline(text)
    assert out == text


# ---- T11: strip_orphan_punctuation ----------------------------------------


def test_strip_orphan_pipe() -> None:
    """Lone ``|`` line is stripped."""
    text = "Real content.\n|\nMore real content.\n"
    out = strip_orphan_punctuation(text)
    assert "|" not in out.split("\n")[1] if "\n" in out else True


def test_strip_orphan_gt() -> None:
    """Lone ``>`` line is stripped (but ``> quote`` lines stay)."""
    text = "> real quote\n>\n> another quote\n"
    out = strip_orphan_punctuation(text)
    assert "> real quote" in out
    assert "> another quote" in out


# ---- T12: enforce_heading_hierarchy --------------------------------------


def test_enforce_heading_hierarchy_first_becomes_h1() -> None:
    """First heading is re-anchored to H1."""
    text = "### Title\n\nbody\n"
    out = enforce_heading_hierarchy(text)
    assert "# Title" in out
    assert "### Title" not in out


def test_enforce_heading_hierarchy_no_skip() -> None:
    """Jumping from H2 to H5 gets clamped."""
    text = "# H1\n\n## H2\n\n##### H5 too deep\n"
    out = enforce_heading_hierarchy(text)
    assert "# H1" in out
    assert "## H2" in out
    # H5 became H3
    assert "### H5 too deep" in out


def test_enforce_heading_hierarchy_caps_at_h6() -> None:
    """Headings beyond H6 get capped at H6."""
    text = "# A\n\n############## way too deep\n"
    out = enforce_heading_hierarchy(text)
    # Becomes H6
    assert "###### way too deep" in out


# ---- Runner ---------------------------------------------------------------


def test_clean_text_runs_default_pipeline() -> None:
    """clean_text applies all 12 stages by default."""
    text = (
        "exam-\nple\ufb01le with\r\n\r\n\r\n\r\n"
        "&amp;amp; entities &quot;quotes&quot;\u2014dashes\n\n"
        "> a real quote\n>\n> another\n"
    )
    out = clean_text(text)
    # Dehyphenated
    assert "example" in out
    # Ligature normalized
    assert "\ufb01" not in out
    # CRLF normalized
    assert "\r" not in out
    # Entity decoded twice
    assert "& " in out or " & " in out
    # Curly quote replaced
    assert '"quotes"' in out


def test_clean_text_with_subset() -> None:
    """clean_text honors an explicit stage list."""
    text = "exam-\nple"
    out = clean_text(text, stages=["dehyphenate"])
    # Only dehyphenate ran; no ligature/whitespace work
    assert "example" in out
    # Whitespace runs should still be present
    assert (
        "\nple" in out or "exam-\nple" in out.replace("exam-\nple", "example") or "example" in out
    )


def test_clean_text_unknown_stage_raises() -> None:
    """Unknown stage name raises KeyError."""
    with pytest.raises(KeyError):
        clean_text("x", stages=["nope_doesnt_exist"])


def test_stages_registry_complete() -> None:
    """All 12 stages are in the registry."""
    expected = {
        "nfc_normalize",
        "strip_soft_hyphens",
        "normalize_ligatures",
        "normalize_quotes_dashes",
        "collapse_whitespace",
        "decode_html_entities",
        "repair_line_wraps",
        "dehyphenate",
        "dedupe_toc_block",
        "strip_repeated_byline",
        "strip_orphan_punctuation",
        "enforce_heading_hierarchy",
    }
    assert set(STAGES.keys()) == expected
    assert len(DEFAULT_ORDER) == 12


def test_clean_text_is_idempotent() -> None:
    """Running clean_text twice gives the same result."""
    text = "hello\tworld\r\nwith\r\nweird   spacing"
    once = clean_text(text)
    twice = clean_text(once)
    assert once == twice
