"""`headcleaner review` (Eng #3) — interactive TUI for human sign-off.

Walks every concept in an OKF bundle that still has
`verified: human:pending` and lets the human:

- **(a)pprove** — flip to `verified: human:reviewed`, set `reviewed_at`
- **(r)eject** — set `verified: human:rejected`, append a `rejection_reasons` list
- **(s)kip** — leave as pending, move to next
- **(q)uit** — exit the TUI (already-approved changes persist)

The TUI uses Textual with a single-screen per-concept layout:
header, body preview, and a fixed footer with the four keys.

Usage:
    headcleaner review <bundle-dir>
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_concept(path: Path) -> tuple[dict, str, str] | None:
    """Return (frontmatter, body, full_text) for a concept, or None."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    if "type" not in fm:
        return None
    body = text[m.end():]
    return fm, body, text


def _write_concept(path: Path, fm: dict, body: str, original_text: str) -> None:
    """Re-emit the concept preserving structure."""
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{yaml_text}\n---\n{body}", encoding="utf-8")


def iter_pending(bundle_root: Path) -> Iterable[Path]:
    """Yield every concept path with `verified: human:pending`."""
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in {"index.md", "log.md", "attestation.json"}:
            continue
        rec = _read_concept(md_path)
        if rec is None:
            continue
        fm, _, _ = rec
        if fm.get("verified") == "human:pending":
            yield md_path


def approve(path: Path) -> None:
    """Flip `verified: human:pending` → `human:reviewed`, set reviewed_at."""
    rec = _read_concept(path)
    if rec is None:
        return
    fm, body, _ = rec
    fm["verified"] = "human:reviewed"
    fm["status"] = "verified"
    fm["reviewed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm["reviewed_by"] = "human"
    fm["reviewed_via"] = "headcleaner review"
    _write_concept(path, fm, body, _)


def reject(path: Path, reasons: list[str] | None = None) -> None:
    """Flip `verified: human:pending` → `human:rejected`, record reasons."""
    rec = _read_concept(path)
    if rec is None:
        return
    fm, body, _ = rec
    fm["verified"] = "human:rejected"
    fm["status"] = "rejected"
    fm["rejected_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    fm["rejected_by"] = "human"
    fm["rejected_via"] = "headcleaner review"
    if reasons:
        fm["rejection_reasons"] = list(reasons)
    _write_concept(path, fm, body, _)


# ---------------------------------------------------------------------------
# Textual TUI
# ---------------------------------------------------------------------------

def run_review_tui(bundle_root: Path) -> dict[str, int]:
    """Launch the review TUI. Returns a summary {approved, rejected, skipped, quit}.

    If no pending concepts are found, prints a notice and returns zeros.
    """
    pending = list(iter_pending(bundle_root))
    if not pending:
        print(f"[review] no `verified: human:pending` concepts in {bundle_root}")
        return {"approved": 0, "rejected": 0, "skipped": 0, "quit": 1}

    # Try to use Textual; if it fails (e.g. no display), fall back to plain REPL.
    try:
        from textual.app import App
        from textual.widgets import Static, Footer, Header
        from textual.containers import Vertical
        from textual.binding import Binding
    except ImportError:
        return _review_repl(pending)

    from . import theme as _theme

    class ReviewApp(App):
        CSS = """
        Screen { background: #111111; color: #E5E5E5; }
        #title { color: #22D3EE; text-style: bold; padding: 1 2; }
        #meta { color: #A855F7; padding: 0 2; }
        #body { padding: 1 2; color: #E5E5E5; }
        #hint { color: #EC4899; padding: 1 2; text-style: bold; }
        """

        BINDINGS = [
            Binding("a", "approve", "Approve"),
            Binding("r", "reject", "Reject"),
            Binding("s", "skip", "Skip"),
            Binding("q", "quit", "Quit"),
            Binding("n", "next_concept", "Next"),
            Binding("p", "prev_concept", "Prev"),
        ]

        def __init__(self, concepts: list[Path]) -> None:
            super().__init__()
            self.concepts = concepts
            self.index = 0
            self.summary = {"approved": 0, "rejected": 0, "skipped": 0, "quit": 0}

        def compose(self):
            yield Header(show_clock=False)
            yield Static("", id="title")
            yield Static("", id="meta")
            yield Static("", id="body")
            yield Static("", id="hint")
            yield Footer()

        def on_mount(self) -> None:
            _theme.set_theme("neon")
            self._refresh()

        def _refresh(self) -> None:
            if not self.concepts:
                self.exit()
                return
            path = self.concepts[self.index]
            rec = _read_concept(path)
            if rec is None:
                self.index += 1
                self._refresh()
                return
            fm, body, _ = rec
            self.query_one("#title", Static).update(
                _theme.paint(f"[{self.index + 1}/{len(self.concepts)}] ", _theme.NEON_CYAN)
                + _theme.paint(str(fm.get("title") or path.stem), _theme.NEON_PINK, bold=True)
            )
            meta = (
                f"path: {path}\n"
                f"type: {fm.get('type', '?')}\n"
                f"verified: {fm.get('verified', '?')}\n"
                f"status: {fm.get('status', '?')}\n"
            )
            self.query_one("#meta", Static).update(_theme.paint(meta, _theme.NEON_PURPLE))
            preview = body[:1200] + ("\n... (truncated)" if len(body) > 1200 else "")
            self.query_one("#body", Static).update(preview)
            self.query_one("#hint", Static).update(
                _theme.paint("a=approve  r=reject  s=skip  n=next  p=prev  q=quit", _theme.FG_MUTED)
            )

        def action_approve(self) -> None:
            approve(self.concepts[self.index])
            self.summary["approved"] += 1
            self.index = min(self.index + 1, len(self.concepts) - 1)
            self._refresh()

        def action_reject(self) -> None:
            reject(self.concepts[self.index])
            self.summary["rejected"] += 1
            self.index = min(self.index + 1, len(self.concepts) - 1)
            self._refresh()

        def action_skip(self) -> None:
            self.summary["skipped"] += 1
            self.index = min(self.index + 1, len(self.concepts) - 1)
            self._refresh()

        def action_next_concept(self) -> None:
            self.index = min(self.index + 1, len(self.concepts) - 1)
            self._refresh()

        def action_prev_concept(self) -> None:
            self.index = max(self.index - 1, 0)
            self._refresh()

        def action_quit(self) -> None:
            self.summary["quit"] = 1
            self.exit()

    app = ReviewApp(pending)
    app.run()
    return app.summary


def _review_repl(pending: list[Path]) -> dict[str, int]:
    """Fallback plain-mode REPL when Textual isn't available."""
    summary = {"approved": 0, "rejected": 0, "skipped": 0, "quit": 0}
    for i, path in enumerate(pending):
        rec = _read_concept(path)
        if rec is None:
            continue
        fm, body, _ = rec
        print(f"\n[{i + 1}/{len(pending)}] {fm.get('title') or path.name}")
        print(f"  path:     {path}")
        print(f"  type:     {fm.get('type', '?')}")
        print(f"  verified: {fm.get('verified', '?')}")
        print(f"  ---")
        for line in body.splitlines()[:30]:
            print(f"  {line}")
        if len(body.splitlines()) > 30:
            print(f"  ... ({len(body.splitlines()) - 30} more lines)")
        choice = input("  [a]pprove / [r]eject / [s]kip / [q]uit: ").strip().lower()
        if choice == "a":
            approve(path)
            summary["approved"] += 1
        elif choice == "r":
            reject(path)
            summary["rejected"] += 1
        elif choice == "q":
            summary["quit"] = 1
            break
        else:
            summary["skipped"] += 1
    return summary