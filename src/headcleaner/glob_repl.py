"""Interactive glob REPL — Textual UI with live match count (Eng #44 full impl).

When `headcleaner convert --include <glob>` matches zero files, instead
of silently doing nothing, launch this mini-REPL where the user can
refine the glob interactively and see the live count of matching files.

Public entry points:
    - `count_matches(root, glob)` — fnmatch-based file count
    - `launch_repl(root, initial_glob="*")` — runs the Textual app or
      falls back to a plain-mode REPL when Textual isn't available.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path


def count_matches(root: Path, glob: str) -> int:
    """Return the number of files under `root` whose name matches `glob`."""
    if not root.is_dir():
        return 0
    n = 0
    for p in root.rglob("*"):
        if p.is_file() and fnmatch.fnmatch(p.name, glob):
            n += 1
    return n


def list_matches(root: Path, glob: str, limit: int = 20) -> list[Path]:
    """Return up to `limit` files under `root` matching `glob`."""
    if not root.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and fnmatch.fnmatch(p.name, glob):
            out.append(p)
            if len(out) >= limit:
                break
    return out


# ---------------------------------------------------------------------------
# Textual app (preferred path)
# ---------------------------------------------------------------------------


def launch_repl(root: Path, initial_glob: str = "*") -> str:
    """Launch the interactive glob REPL.

    Returns the final accepted glob (so the caller can re-run the convert
    with `--include <returned-glob>`).
    """
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Input, Static, Footer, ListView, ListItem, Label
        from textual.containers import Vertical
        from textual.binding import Binding
    except ImportError:
        return _repl_plain(root, initial_glob)

    from . import theme as _theme

    class GlobApp(App):
        CSS = """
        Screen { background: #111111; color: #E5E5E5; }
        #prompt { color: #22D3EE; padding: 1 2; text-style: bold; }
        #count { color: #A855F7; padding: 0 2; }
        #samples { padding: 1 2; color: #E5E5E5; }
        #hint { color: #EC4899; padding: 1 2; }
        """

        BINDINGS = [
            Binding("enter", "accept", "Accept"),
            Binding("ctrl+c", "quit", "Quit"),
            Binding("escape", "quit", "Quit"),
        ]

        def __init__(self, root: Path, initial_glob: str) -> None:
            super().__init__()
            self.root = root
            self.current_glob = initial_glob
            self._accepted: str | None = None

        def compose(self) -> ComposeResult:
            from textual.widgets import Input as _Input

            yield Static(f"Glob REPL — root: {self.root}", id="prompt")
            yield _Input(value=self.current_glob, placeholder="*.pdf", id="glob-input")
            yield Static("", id="count")
            yield Static("", id="samples")
            yield Static(
                "Enter = accept  Ctrl+C/Esc = quit  (type a glob; count updates live)",
                id="hint",
            )
            yield Footer()

        def on_mount(self) -> None:
            _theme.set_theme("neon")
            self.query_one("#glob-input").focus()
            self._refresh()

        def on_input_changed(self, event) -> None:
            self.current_glob = event.value
            self._refresh()

        def _refresh(self) -> None:
            n = count_matches(self.root, self.current_glob)
            samples = list_matches(self.root, self.current_glob, limit=8)
            count_text = f"{n} file{'s' if n != 1 else ''} matching  {self.current_glob!r}"
            try:
                self.query_one("#count", Static).update(_theme.paint(count_text, _theme.NEON_PINK))
                sample_lines = "\n".join(str(p.relative_to(self.root)) for p in samples)
                if n > len(samples):
                    sample_lines += f"\n... ({n - len(samples)} more)"
                self.query_one("#samples", Static).update(sample_lines or "(no matches)")
            except Exception:
                pass

        def action_accept(self) -> None:
            self._accepted = self.current_glob
            self.exit()

        def action_quit(self) -> None:
            self.exit()

    app = GlobApp(root, initial_glob)
    app.run()
    return app._accepted or initial_glob


def _repl_plain(root: Path, initial_glob: str) -> str:
    """Plain-mode REPL fallback (no Textual)."""
    current = initial_glob
    while True:
        n = count_matches(root, current)
        samples = list_matches(root, current, limit=10)
        print(f"\n[glob-repl] {n} file{'s' if n != 1 else ''} matching {current!r}")
        for s in samples:
            print(f"  {s.relative_to(root)}")
        if n > len(samples):
            print(f"  ... ({n - len(samples)} more)")
        print()
        print("[enter]=accept  [q]=quit  new glob: ", end="")
        try:
            line = input().strip()
        except EOFError:
            break
        if line == "":
            return current
        if line.lower() in {"q", "quit", "exit"}:
            return current
        current = line
