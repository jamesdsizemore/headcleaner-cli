"""Visual constants for the headcleaner TUI.

Modeled on omp's visual language (segment-based, box-drawing, powerline
separators), themed in a neon cyberpunk palette:

  - neon cyan   #22D3EE  — primary accent, headers, success
  - neon pink   #EC4899  — active selection, model/warnings
  - neon purple #A855F7  — secondary accent, info
  - near-black  #0A0A0A  — background
  - light grey  #E5E5E5  — body text
  - dark grey   #6B7280  — muted text
"""

from __future__ import annotations

# ANSI true-color hex palette
NEON_CYAN = "#22D3EE"
NEON_PINK = "#EC4899"
NEON_PURPLE = "#A855F7"
NEON_CYAN_DIM = "#0E7490"
NEON_PINK_DIM = "#9D174D"
NEON_PURPLE_DIM = "#6B21A8"
BG_BLACK = "#0A0A0A"
BG_PANEL = "#111111"
FG_TEXT = "#E5E5E5"
FG_MUTED = "#6B7280"
FG_DIM = "#374151"

# Status colors (no red/yellow per user spec)
STATUS_OK = NEON_CYAN
STATUS_ACTIVE = NEON_PINK
STATUS_INFO = NEON_PURPLE
STATUS_SKIPPED = FG_MUTED
STATUS_FAILED = NEON_PINK  # bright pink instead of red

# Box-drawing characters (omp's two themes)
class RoundedBox:
    tl = "╭"
    tr = "╮"
    bl = "╰"
    br = "╯"
    h = "─"
    v = "│"


class SharpBox:
    tl = "┌"
    tr = "┐"
    bl = "└"
    br = "┘"
    h = "─"
    v = "│"
    tee_down = "┬"
    tee_up = "┴"
    tee_right = "├"
    tee_left = "┤"
    cross = "┼"


# Tree connectors (omp's UNICODE_SYMBOLS tree.*)
TREE_BRANCH = "├─"
TREE_LAST = "└─"
TREE_VERTICAL = "│"
TREE_HOOK = "└─"

# Powerline-style separators
SEP_POWERLINE = "▕"
SEP_THIN = "│"
SEP_BLOCK = "▌"
SEP_SPACE = " "
SEP_PIPE = " │ "

# Brand mark — the lightning-bolt jar from the user's reference image.
# Textual can't embed a PNG inline, so we ship two ASCII variants the TUI
# can swap based on terminal width.
LOGO_LARGE = """
 ⚡  HEAD ◯ CLEANER �
 ⚡  ────────────── ⚡
"""
LOGO_SMALL = " ⚡ HEAD◯CLEANER "
LOGO_BOLT = "⚡"  # single glyph for tight spaces

# omp-style status icons (Unicode, no Nerd Font required)
ICON_SUCCESS = "✔"
ICON_FAIL = "✘"
ICON_WARN = "⚠"
ICON_INFO = "�"
ICON_PENDING = "⏳"
ICON_RUN = "⟳"
ICON_DONE = "●"
ICON_SKIP = "○"

# Spinner frames (omp's UNICODE_SYMBOLS spinner.activity)
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def paint(text: str, color: str, *, bold: bool = False, dim: bool = False) -> str:
    """Wrap text in ANSI true-color SGR codes for terminal output.

    Returns the text with escape sequences; safe to print to stdout/stderr
    when stdout is a TTY. Plain-mode callers should gate with `if sys.stdout.isatty()`.
    """
    bold_code = "1;" if bold else ""
    dim_code = "2;" if dim else ""
    if not color.startswith("#") or len(color) != 7:
        return text
    try:
        hex_ = color.lstrip("#")
        r, g, b = int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16)
    except ValueError:
        return text
    return f"\x1b[{bold_code}{dim_code}38;2;{r};{g};{b}m{text}\x1b[0m"


def segment(text: str, fg: str, *, bold: bool = False, icon: str | None = None) -> str:
    """One omp-style segment: optional icon + text in `fg` color."""
    if icon:
        text = f"{icon} {text}"
    return paint(text, fg, bold=bold)


def powerline(prev_fg: str | None, next_fg: str, *, separator: str = SEP_POWERLINE) -> str:
    """The omp-style powerline chevron between two colored segments.

    Painted with `prev_fg` as foreground (so it appears to come out of the prior
    block) and a thin background hint of `next_fg` would require 24-bit color,
    which we skip here for portability — instead we use a dim version of
    `next_fg` so the eye reads it as a transition.
    """
    if prev_fg is None:
        return paint(separator, next_fg)
    return paint(separator, next_fg, dim=True)


def banner(title: str, width: int = 80, *, box: type = RoundedBox) -> str:
    """Render an omp-style banner: �─ TITLE ─...─╮ across one line."""
    inner = f" {title} "
    rest = width - len(inner) - 2  # 2 = the two corner chars
    if rest < 0:
        rest = 0
    return (
        paint(box.tl + box.h, NEON_CYAN, bold=True)
        + paint(inner, NEON_PINK, bold=True)
        + paint(box.h * rest + box.tr, NEON_CYAN, bold=True)
    )


def panel_top(title: str, width: int = 80, *, box: type = RoundedBox) -> str:
    """Top edge of a panel: ╭─ title ─...─╮."""
    return banner(title, width=width, box=box)


def panel_bottom(width: int = 80, *, box: type = RoundedBox) -> str:
    return paint(box.bl + box.h * (width - 2) + box.br, NEON_CYAN)


def panel_row(content: str, width: int = 80, *, box: type = RoundedBox) -> str:
    """Wrap a content line with left+right vertical bars; pad to width."""
    pad = max(0, width - visible_width(content) - 2)
    return paint(box.v, NEON_CYAN) + content + (" " * pad) + paint(box.v, NEON_CYAN)


def visible_width(text: str) -> int:
    """Approximate visible width of a string, ignoring ANSI escapes."""
    import re
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))
