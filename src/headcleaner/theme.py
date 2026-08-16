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

# Default palette: neon (the user's spec from Batch 1)
PALETTE_NEON = {
    "primary": "#22D3EE",    # neon cyan
    "accent": "#EC4899",     # neon pink
    "secondary": "#A855F7",  # neon purple
    "primary_dim": "#0E7490",
    "accent_dim": "#9D174D",
    "secondary_dim": "#6B21A8",
    "bg": "#0A0A0A",
    "bg_panel": "#111111",
    "fg": "#E5E5E5",
    "muted": "#6B7280",
    "dim": "#374151",
}

# Backward-compat module-level constants — kept in sync with PALETTE_NEON.
NEON_CYAN = PALETTE_NEON["primary"]
NEON_PINK = PALETTE_NEON["accent"]
NEON_PURPLE = PALETTE_NEON["secondary"]
NEON_CYAN_DIM = PALETTE_NEON["primary_dim"]
NEON_PINK_DIM = PALETTE_NEON["accent_dim"]
NEON_PURPLE_DIM = PALETTE_NEON["secondary_dim"]
BG_BLACK = PALETTE_NEON["bg"]
BG_PANEL = PALETTE_NEON["bg_panel"]
FG_TEXT = PALETTE_NEON["fg"]
FG_MUTED = PALETTE_NEON["muted"]
FG_DIM = PALETTE_NEON["dim"]

PALETTE_LIGHT = {
    "primary": "#0EA5E9",    # sky-500 (cyan-ish, fits light bg)
    "accent": "#DB2777",     # pink-600
    "secondary": "#7C3AED",  # violet-600
    "primary_dim": "#0369A1",
    "accent_dim": "#9D174D",
    "secondary_dim": "#5B21B6",
    "bg": "#FFFFFF",
    "bg_panel": "#F3F4F6",
    "fg": "#1F2937",
    "muted": "#4B5563",
    "dim": "#9CA3AF",
}

PALETTE_DARK = {
    "primary": "#A78BFA",    # violet-400 (more muted for non-cyan-loving)
    "accent": "#F472B6",     # pink-400
    "secondary": "#22D3EE",  # cyan-400
    "primary_dim": "#7C3AED",
    "accent_dim": "#DB2777",
    "secondary_dim": "#0E7490",
    "bg": "#1F2937",         # gray-800
    "bg_panel": "#111827",   # gray-900
    "fg": "#F3F4F6",         # gray-100
    "muted": "#9CA3AF",
    "dim": "#4B5563",
}

PALETTE_MONO = {
    "primary": "#E5E5E5",
    "accent": "#FFFFFF",
    "secondary": "#A0A0A0",
    "primary_dim": "#A0A0A0",
    "accent_dim": "#FFFFFF",
    "secondary_dim": "#808080",
    "bg": "#000000",
    "bg_panel": "#0A0A0A",
    "fg": "#E5E5E5",
    "muted": "#A0A0A0",
    "dim": "#606060",
}

PALETTES = {
    "neon": PALETTE_NEON,
    "light": PALETTE_LIGHT,
    "dark": PALETTE_DARK,
    "mono": PALETTE_MONO,
}


def set_theme(name: str) -> dict[str, str]:
    """Switch the global palette. Returns the active palette dict."""
    global NEON_CYAN, NEON_PINK, NEON_PURPLE
    global NEON_CYAN_DIM, NEON_PINK_DIM, NEON_PURPLE_DIM
    global BG_BLACK, BG_PANEL, FG_TEXT, FG_MUTED, FG_DIM

    pal = PALETTES.get(name)
    if pal is None:
        raise ValueError(f"unknown theme {name!r}; choose from {list(PALETTES)}")

    # Backward-compatible module-level constants (kept names for older code).
    # New code should reference the palette dict directly.
    NEON_CYAN = pal["primary"]
    NEON_PINK = pal["accent"]
    NEON_PURPLE = pal["secondary"]
    NEON_CYAN_DIM = pal["primary_dim"]
    NEON_PINK_DIM = pal["accent_dim"]
    NEON_PURPLE_DIM = pal["secondary_dim"]
    BG_BLACK = pal["bg"]
    BG_PANEL = pal["bg_panel"]
    FG_TEXT = pal["fg"]
    FG_MUTED = pal["muted"]
    FG_DIM = pal["dim"]

    # Replace the headcleaner.theme module's paint helper with a no-op
    # when the theme is "mono" or "light" to avoid ANSI in those contexts.
    return pal


# Default palette name
_CURRENT_THEME = "neon"

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
