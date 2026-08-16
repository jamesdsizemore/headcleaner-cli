"""Markdown cleanup heuristics (v0.8.0).

Borrowed from the any2md 12-stage cleanup pipeline (rocklambros/any2md, MIT).
Reimplemented for headcleaner with simpler signatures and zero dependencies
beyond the standard library + BeautifulSoup (already in our deps tree).

Each function is a pure `text -> text` transform so they're trivial to
compose, test, and selectively enable.

Stages (in canonical order):

  T1. nfc_normalize              — Unicode NFC; LF line endings
  T2. strip_soft_hyphens         — U+00AD soft hyphens
  T3. normalize_ligatures        — fi/fl/etc. ligatures -> ascii
  T4. normalize_quotes_dashes    — curly quotes/dashes -> ascii
  T5. collapse_whitespace        — runs of spaces/tabs -> single space
  T6. decode_html_entities       — &amp; &lt; etc. (iterates until stable)
  T7. repair_line_wraps          — hard-wrapped lines -> joined paragraphs
  T8. dehyphenate                — "exam-\\nple" -> "example"
  T9. dedupe_toc_block           — drop a TOC that repeats later in the doc
  T10. strip_repeated_byline     — repeated author/title lines
  T11. strip_orphan_punctuation  — lone `|`, `>`, etc. lines
  T12. enforce_heading_hierarchy — H1 -> H2 -> H3 must not skip levels

The runner (`clean_text`) applies all 12 by default. Pass a `stages` list
to enable a subset.
"""
from __future__ import annotations

import html
import re
import unicodedata
from typing import Callable

# ---------------------------------------------------------------------------
# T1 — Unicode NFC + LF
# ---------------------------------------------------------------------------

def nfc_normalize(text: str) -> str:
    """Normalize to Unicode NFC and force LF line endings.

    Why: macOS/Windows tools emit CRLF or NFD; LLM-friendly Markdown is
    LF + NFC everywhere.
    """
    return unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")


# ---------------------------------------------------------------------------
# T2 — Soft hyphens
# ---------------------------------------------------------------------------

_SOFT_HYPHEN = "\u00AD"

def strip_soft_hyphens(text: str) -> str:
    """Remove U+00AD (soft hyphen) characters that sneak through PDF→MD."""
    return text.replace(_SOFT_HYPHEN, "")


# ---------------------------------------------------------------------------
# T3 — Ligatures
# ---------------------------------------------------------------------------

_LIGATURES = {
    "\ufb01": "fi",  # fi
    "\ufb02": "fl",  # fl
    "\ufb03": "ffi",  # ffi
    "\ufb04": "ffl",  # ffl
    "\ufb05": "st",  # long s + t
    "\ufb06": "st",  # st
    "\u00A0": " ",  # nbsp -> space
    "\u2009": " ",  # thin space -> space
    "\u200A": " ",  # hair space -> space
}

def normalize_ligatures(text: str) -> str:
    """Replace Unicode ligatures + non-breaking spaces with their ASCII form."""
    for src, dst in _LIGATURES.items():
        text = text.replace(src, dst)
    return text


# ---------------------------------------------------------------------------
# T4 — Curly quotes + dashes
# ---------------------------------------------------------------------------

_QUOTES_DASHES = {
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201C": '"',  # left double quote
    "\u201D": '"',  # right double quote
    "\u2013": "-",  # en dash
    "\u2014": "--",  # em dash
    "\u2026": "...",  # ellipsis
}

def normalize_quotes_dashes(text: str) -> str:
    """Replace typographic quotes and dashes with ASCII."""
    for src, dst in _QUOTES_DASHES.items():
        text = text.replace(src, dst)
    return text


# ---------------------------------------------------------------------------
# T5 — Collapse whitespace
# ---------------------------------------------------------------------------

_RUN_OF_WS = re.compile(r"[ \t]+")
_RUN_OF_BLANKS = re.compile(r"\n{3,}")

def collapse_whitespace(text: str) -> str:
    """Collapse runs of horizontal whitespace to a single space; cap blank lines at 2."""
    text = _RUN_OF_WS.sub(" ", text)
    text = _RUN_OF_BLANKS.sub("\n\n", text)
    return text


# ---------------------------------------------------------------------------
# T6 — HTML entities (iterative)
# ---------------------------------------------------------------------------

_HTML_ENTITY = re.compile(r"&(?:#x[0-9a-fA-F]+|#\d+|[a-zA-Z]+);")

def decode_html_entities(text: str, *, max_iters: int = 5) -> str:
    """Decode HTML entities iteratively until output stabilizes.

    any2md note: ``&amp;amp;`` -> ``&amp;`` -> ``&`` is fully decoded by
    looping. Default max 5 iterations is empirically enough.
    """
    for _ in range(max_iters):
        new = html.unescape(text)
        if new == text:
            return text
        text = new
    return text


# ---------------------------------------------------------------------------
# T7 — Repair line wraps (hard-wrapped text -> joined paragraphs)
# ---------------------------------------------------------------------------

def repair_line_wraps(text: str) -> str:
    """Re-join lines that are wrapped mid-sentence within a paragraph.

    A "paragraph" here is a run of lines with no blank line between them
    that don't start with a markdown structural marker (`#`, `>`, `-`,
    `*`, `+`, digit+`.`, `|`, or fenced code fence).
    """
    lines = text.split("\n")
    out: list[str] = []
    para: list[str] = []
    structural = re.compile(r"^(\s*#{1,6}\s|\s*>\s|\s*[-*+]\s|\s*\d+\.\s|\s*\||\s*```)")
    for line in lines:
        if not line.strip():
            if para:
                out.append(" ".join(para).rstrip())
                para = []
            out.append(line)
        elif structural.match(line):
            if para:
                out.append(" ".join(para).rstrip())
                para = []
            out.append(line)
        else:
            para.append(line.strip())
    if para:
        out.append(" ".join(para).rstrip())
    return "\n".join(out)


# ---------------------------------------------------------------------------
# T8 — Dehyphenate
# ---------------------------------------------------------------------------

_DEHYPHENATE = re.compile(r"(\w)-\n(\w)")

def dehyphenate(text: str) -> str:
    """Re-join words split across a line break with a hyphen."""
    return _DEHYPHENATE.sub(r"\1\2", text)


# ---------------------------------------------------------------------------
# T9 — Dedupe a TOC block that appears again later
# ---------------------------------------------------------------------------

def dedupe_toc_block(text: str, *, min_lines: int = 4) -> str:
    """Drop an early "table of contents" block that reappears verbatim later.

    Heuristic: if the first `min_lines` non-blank lines appear in the same
    order somewhere after the early block, drop the early block.
    """
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip()), None)
    if start is None:
        return text
    block: list[str] = []
    i = start
    while i < len(lines) and len(block) < min_lines:
        if lines[i].strip():
            block.append(lines[i].strip())
        i += 1
    if len(block) < min_lines:
        return text
    # Search for the *first line* of the block later in the document.
    # If we find it, verify the next len(block)-1 lines match too.
    later = lines[i:]
    # The first line of `block` may be a heading; skip it for the match.
    # We look for the *first non-heading* block line later in the doc.
    match_block = [ln for ln in block if not ln.startswith("#")]
    if len(match_block) < 2:
        return text
    repeat_idx: int | None = None
    for j, ln in enumerate(later):
        if ln.strip() == match_block[0]:
            ok = True
            for k in range(1, len(match_block)):
                jj = j + k
                if jj >= len(later) or later[jj].strip() != match_block[k]:
                    ok = False
                    break
            if ok:
                repeat_idx = j
                break
    if repeat_idx is not None:
        out = lines[:start] + lines[i:]
        return _RUN_OF_BLANKS.sub("\n\n", "\n".join(out))
    return text


    return text


# ---------------------------------------------------------------------------
# T10 — Strip repeated byline
# ---------------------------------------------------------------------------

_REPEAT_LINE = re.compile(r"^(.{8,120})$", re.MULTILINE)

def strip_repeated_byline(text: str, *, min_repeats: int = 2) -> str:
    """Drop lines that appear 2+ times in the document (byline-like)."""
    matches = _REPEAT_LINE.findall(text)
    counts: dict[str, int] = {}
    for m in matches:
        counts[m] = counts.get(m, 0) + 1
    repeated = {line for line, c in counts.items() if c >= min_repeats}
    if not repeated:
        return text
    out_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped in repeated:
            out_lines.append("")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# T11 — Strip orphan punctuation
# ---------------------------------------------------------------------------

_ORPHAN_PUNCT = re.compile(r"^\s*[|>+\-=*#~]{1,3}\s*$", re.MULTILINE)

def strip_orphan_punctuation(text: str) -> str:
    """Drop lines that are just ``|``, ``>``, ``+``, etc. (from malformed Docling tables)."""
    return _ORPHAN_PUNCT.sub("", text)


# ---------------------------------------------------------------------------
# T12 — Enforce heading hierarchy
# ---------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s")

def enforce_heading_hierarchy(text: str) -> str:
    """Ensure heading levels don't skip — H1, H2, H3, ..., no jumping from H2 to H5.

    Re-anchors each heading to the previous heading level + 1 (capped at H6).
    """
    lines = text.split("\n")
    out: list[str] = []
    last_level = 0  # 0 = no heading seen yet
    for line in lines:
        m = _HEADING.match(line)
        if not m:
            out.append(line)
            continue
        level = len(m.group(1))
        if last_level == 0:
            # First heading becomes H1 regardless
            new_level = 1
        elif level > last_level + 1:
            new_level = last_level + 1
        else:
            new_level = level
        new_level = min(new_level, 6)
        out.append("#" * new_level + line[len(m.group(1)):])
        last_level = new_level
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Stage registry + runner
# ---------------------------------------------------------------------------

STAGES: dict[str, Callable[[str], str]] = {
    "nfc_normalize": nfc_normalize,
    "strip_soft_hyphens": strip_soft_hyphens,
    "normalize_ligatures": normalize_ligatures,
    "normalize_quotes_dashes": normalize_quotes_dashes,
    "collapse_whitespace": collapse_whitespace,
    "decode_html_entities": decode_html_entities,
    "repair_line_wraps": repair_line_wraps,
    "dehyphenate": dehyphenate,
    "dedupe_toc_block": dedupe_toc_block,
    "strip_repeated_byline": strip_repeated_byline,
    "strip_orphan_punctuation": strip_orphan_punctuation,
    "enforce_heading_hierarchy": enforce_heading_hierarchy,
}

DEFAULT_ORDER = [
    "nfc_normalize",
    "strip_soft_hyphens",
    "normalize_ligatures",
    "normalize_quotes_dashes",
    "decode_html_entities",
    "collapse_whitespace",
    "dehyphenate",
    "repair_line_wraps",
    "strip_orphan_punctuation",
    "strip_repeated_byline",
    "dedupe_toc_block",
    "enforce_heading_hierarchy",
]


def clean_text(text: str, *, stages: list[str] | None = None) -> str:
    """Apply the heuristic pipeline to ``text`` and return the cleaned version.

    Parameters
    ----------
    text : str
        The input Markdown / text.
    stages : list[str] | None
        Optional explicit list of stage names to run (default: ``DEFAULT_ORDER``).
    """
    if stages is None:
        stages = DEFAULT_ORDER
    for name in stages:
        fn = STAGES.get(name)
        if fn is None:
            raise KeyError(f"unknown stage {name!r}; known: {sorted(STAGES)}")
        text = fn(text)
    return text