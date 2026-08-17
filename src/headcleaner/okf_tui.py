"""OKF bundle TUI viewer (v0.12.0).

A whole-frame, flicker-free terminal UI for browsing an OKF bundle.

Architecture follows `serradura/okf-tui` (Apache-2.0, 122 stars) — the
upstream's key insight: paint the entire screen on every state change,
not widget-by-widget diffs. Each repaint is "cursor home, print N rows"
— every row overwrites the one beneath it exactly. No flicker, no diff
machinery.

Three panes:

- Left: concept list (id, type, title, status badge)
- Right: detail panel (frontmatter, body preview, links, trust)
- Footer: key hints

Keys:
  j/k or ↓/↑ : move selection
  /           : filter by substring (then Enter to apply, Backspace to clear)
  q           : quit (also Ctrl+C / Ctrl+D)

Activated via `headcleaner view <bundle> --tui`.
"""

from __future__ import annotations

import shutil
import sys
from datetime import date
from pathlib import Path

from .viewer import build_with_unresolved


def _term_size(default: int = 80) -> tuple[int, int]:
    """Return (rows, cols) of the terminal; default on no-tty."""
    try:
        s = shutil.get_terminal_size()
        return s.lines, s.columns
    except (OSError, ValueError):
        return 24, default


def _clip(s: str, limit: int) -> str:
    """Clip a string to `limit` display width (truncates with ellipsis)."""
    if limit <= 0:
        return ""
    if len(s) <= limit:
        return s
    if limit <= 3:
        return s[:limit]
    return s[: limit - 1] + "…"


def _pad(s: str, width: int) -> str:
    """Clip OR pad-to-width with spaces on the right.

    For whole-frame paint, every row must be exactly `width` display
    cells — short rows are padded with trailing spaces so the cursor
    advance lands at column width+1 and the next print starts on the
    next row without scrambling.
    """
    if width <= 0:
        return ""
    if len(s) >= width:
        return _clip(s, width)
    return s + " " * (width - len(s))


def _trust_badge(meta: dict, today: str) -> str:
    """§5.3 trust tier — derived from verified[].by prefix."""
    verified = meta.get("verified") or []
    if not verified:
        tier = "unverified"
    elif any((e.get("by", "")).startswith("human:") for e in verified):
        tier = "human-reviewed"
    else:
        tier = "machine-confirmed"
    stale = meta.get("stale_after", "") and today >= meta["stale_after"]
    deprecated = meta.get("status") == "deprecated"
    badges = [tier]
    if stale:
        badges.append(f"stale({meta['stale_after']})")
    if deprecated:
        badges.append("deprecated")
    return " ".join(badges)


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    lines = text.splitlines(keepends=True)
    if lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[i + 1 :])
    return text


def render_frame(
    bundle_dir: Path,
    *,
    selected: int = 0,
    filter_query: str = "",
    today: str | None = None,
    rows: int | None = None,
    cols: int | None = None,
) -> str:
    """Render the whole TUI frame as a single string.

    This is the **whole-frame paint** entry point — mirrors
    serradura/okf-tui's approach. The returned string, when printed
    after a cursor-home escape, overwrites the entire screen without
    flicker because every row is exactly `cols` display cells wide.

    Pure function (no tty writes) so it's easy to unit-test.
    `rows`/`cols` override terminal-detection (used by tests).
    """
    today = today or date.today().isoformat()
    if rows is None or cols is None:
        tr, tc = _term_size()
        rows = rows or tr
        cols = cols or tc
    # Layout: 1 row header, 1 row separator, rows-3 body, 1 row separator, 1 row footer.
    body_rows = max(5, rows - 3)
    left_w = max(20, cols // 3)
    right_w = cols - left_w - 3  # for " │ "

    # Ingest
    nodes, edges, unresolved = build_with_unresolved(bundle_dir)
    out_idx = {n["id"]: [] for n in nodes}
    in_idx = {n["id"]: [] for n in nodes}
    for e in edges:
        out_idx.setdefault(e["source"], []).append(e["target"])
        in_idx.setdefault(e["target"], []).append(e["source"])

    # Filter
    q = filter_query.lower().strip()
    visible = [
        n
        for n in nodes
        if (
            not q
            or q in n.get("title", "").lower()
            or q in n.get("id", "").lower()
            or q in n.get("type", "").lower()
        )
    ]
    selected = max(0, min(selected, len(visible) - 1)) if visible else 0

    out: list[str] = []
    # --- HEADER
    header = f"  headcleaner · {bundle_dir.resolve().name} · {len(nodes)} concepts · {len(edges)} links · {len(unresolved)} broken"  # noqa: E501
    if q:
        header += f"  · /{q}"
    out.append(_pad(header, cols))
    out.append(_pad("─" * cols, cols))

    # --- LEFT PANE
    body_lines: list[str] = []
    for i in range(body_rows):
        if i < len(visible):
            n = visible[i]
            marker = "▶ " if i == selected else "  "
            type_chip = n.get("type", "Untyped")[:8]
            line = f"{marker}{type_chip:<8} {_clip(n.get('title', ''), left_w - 12)}"
            body_lines.append(_clip(line, left_w))
        else:
            body_lines.append("")

    # --- RIGHT PANE (detail)
    detail_lines: list[str] = []
    if visible and 0 <= selected < len(visible):
        n = visible[selected]
        detail_lines.append(f"# {_clip(n.get('title', ''), right_w - 2)}")
        detail_lines.append(f"id: {n['id']}")
        detail_lines.append(f"type: {n.get('type', 'Untyped')}")
        if n.get("description"):
            detail_lines.append(f"desc: {_clip(n['description'], right_w - 5)}")
        if n.get("tags"):
            detail_lines.append(f"tags: {', '.join(n['tags'])[: right_w - 6]}")
        badge = _trust_badge(n, today)
        detail_lines.append(f"trust: {badge}")
        if n.get("status"):
            detail_lines.append(f"status: {n['status']}")
        if n.get("stale_after"):
            detail_lines.append(f"stale_after: {n['stale_after']}")
        gen = n.get("generated") or {}
        if gen.get("at") or gen.get("by"):
            detail_lines.append(f"generated: {gen.get('at', '')} by {gen.get('by', '')}")
        for v in n.get("verified") or []:
            detail_lines.append(f"verified: {v.get('at', '')} by {v.get('by', '')}")
        body_preview = _strip_frontmatter(n.get("body", "")).strip()
        if body_preview:
            detail_lines.append("")
            remaining = body_rows - len(detail_lines) - 4
            if remaining > 0:
                detail_lines.append("─" * min(right_w, 20))
                for line in body_preview.splitlines()[:remaining]:
                    detail_lines.append(_clip(line, right_w))
        outs = out_idx.get(n["id"], [])
        ins = in_idx.get(n["id"], [])
        if outs or ins:
            detail_lines.append("")
            if outs:
                detail_lines.append(f"→ links to: {', '.join(outs)[: right_w - 15]}")
            if ins:
                detail_lines.append(f"← cited by: {', '.join(ins)[: right_w - 15]}")
    else:
        detail_lines.append("(no concept selected)")

    while len(detail_lines) < body_rows:
        detail_lines.append("")
    detail_lines = detail_lines[:body_rows]

    for i in range(body_rows):
        out.append(_pad(body_lines[i], left_w) + " │ " + _pad(detail_lines[i], right_w))

    # --- FOOTER
    out.append(_pad("─" * cols, cols))
    footer = "  j/k move · / filter · q quit"
    out.append(_pad(footer, cols))

    return "\n".join(out) + "\n"


def run_tui(bundle_dir: Path) -> int:
    """Run the interactive OKF viewer loop. Returns exit code.

    Falls back to a single-frame print when stdout isn't a TTY (so
    `headcleaner view --tui | cat` still produces useful output).
    """
    if not sys.stdout.isatty():
        sys.stdout.write(render_frame(bundle_dir))
        return 0

    selected = 0
    filter_query = ""

    def repaint() -> None:
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write(
            render_frame(
                bundle_dir,
                selected=selected,
                filter_query=filter_query,
            )
        )
        sys.stdout.flush()

    repaint()

    if not sys.stdin.isatty():
        return 0

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("q", "\x03", "\x04"):
                break
            if ch == "\x1b":
                # Read rest of escape sequence
                seq = sys.stdin.read(2)
                if seq == "[B":
                    selected += 1
                elif seq == "[A":
                    selected -= 1
            elif ch == "j":
                selected += 1
            elif ch == "k":
                selected -= 1
            elif ch == "/":
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\nfilter: ")
                sys.stdout.flush()
                filter_query = sys.stdin.readline().rstrip("\n")
                selected = 0
                tty.setraw(fd)
            elif ch == "\x7f":
                filter_query = ""
                selected = 0
            repaint()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\x1b[H\x1b[2J")
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: headcleaner-okf-tui <bundle-dir>")
        raise SystemExit(2)
    raise SystemExit(run_tui(Path(sys.argv[1])))
