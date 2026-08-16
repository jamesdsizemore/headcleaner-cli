"""HeadCleaner TUI — omp-inspired animated terminal interface.

Visual language:
  - rounded box-drawing panels (╭╮╰�) per file result
  - powerline segments (▕) in the header/footer with per-segment neon color
  - neon cyberpunk palette: cyan primary, pink active, purple info
  - lightning-bolt jar (⚡) as the brand mark in the header
  - bottom status bar styled like omp's segmented footer

Modeled on omp's `packages/tui/src/` (can1357/oh-my-pi) but rewritten for
Textual + Python; no Nerd Font required.
"""
from __future__ import annotations

import threading
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Log, ProgressBar, Static

from . import __version__
from .emit.manifest import FileResult
from .run import RunOptions, run_pipeline
from .theme import (
    BG_PANEL,
    FG_MUTED,
    FG_TEXT,
    ICON_DONE,
    ICON_FAIL,
    ICON_PENDING,
    ICON_RUN,
    ICON_SKIP,
    ICON_SUCCESS,
    LOGO_BOLT,
    LOGO_SMALL,
    NEON_CYAN,
    NEON_CYAN_DIM,
    NEON_PINK,
    NEON_PINK_DIM,
    NEON_PURPLE,
    NEON_PURPLE_DIM,
    SPINNER_FRAMES,
    STATUS_ACTIVE,
    STATUS_FAILED,
    STATUS_INFO,
    STATUS_OK,
    STATUS_SKIPPED,
    paint,
    panel_row,
    panel_top,
    segment,
    visible_width,
)


class HeadCleanerApp(App):
    """Colorful animated TUI for a headcleaner conversion run."""

    CSS = f"""
    Screen {{ background: {BG_PANEL}; color: {FG_TEXT}; }}
    #title {{
      dock: top;
      height: 3;
      padding: 1 2;
      background: {BG_PANEL};
      color: {NEON_CYAN};
      text-style: bold;
    }}
    #progress-row {{ height: 3; padding: 0 2; }}
    ProgressBar > .bar--complete {{ background: {NEON_CYAN}; }}
    ProgressBar > .bar--indeterminate {{ background: {NEON_PINK}; }}
    #status-row {{
      dock: bottom;
      height: 1;
      padding: 0 2;
      background: #1a1a1a;
      color: {NEON_CYAN};
    }}
    Log {{
      border: round {NEON_CYAN};
      margin: 1 2;
      background: #0d0d0d;
    }}
    Footer {{ background: {BG_PANEL}; }}
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, opts: RunOptions) -> None:
        super().__init__()
        self.opts = opts
        self._finished = False
        self._final_summary = ""
        self._spinner_idx = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # omp-style title row: ⚡ HEAD◯CLEANER ─ walking ─ /path ─ ...
        title_line = (
            segment(LOGO_SMALL, NEON_PINK, bold=True)
            + " "
            + segment("walking", NEON_CYAN, dim=True)
            + " "
            + paint(str(self.opts.input_root), NEON_PURPLE)
        )
        yield Static(title_line, id="title")
        with Vertical(id="progress-row"):
            yield ProgressBar(total=100, show_eta=True, id="bar")
        # Eng #41: per-engine sub-progress row (updated via on_engine_progress)
        yield Static("", id="engine-row")
        yield Log(highlight=True, id="log")
        yield Static(self._status_bar_text(), id="status-row")
        yield Footer()

    def _status_bar_text(self) -> str:
        """omp-style segmented footer: ⚡ › cyan › pink › purple ── title ──"""
        return (
            segment(LOGO_BOLT, NEON_PINK, bold=True)
            + segment("›", NEON_CYAN_DIM)
            + segment("headcleaner", NEON_CYAN)
            + segment("›", NEON_PURPLE_DIM)
            + segment(f"v{__version__}", NEON_PURPLE)
            + segment("›", NEON_CYAN_DIM)
            + segment(self.opts.fmt.upper(), NEON_CYAN, bold=True)
            + segment("›", NEON_PINK_DIM)
            + segment(self._status_label(), STATUS_ACTIVE if not self._finished else STATUS_OK)
            + paint(
                f"─── {self.opts.output_root.name or 'out'} ───",
                NEON_CYAN_DIM,
                dim=True,
            )
        )

    def _status_label(self) -> str:
        if self._finished:
            return self._final_summary or "done"
        return f"{SPINNER_FRAMES[self._spinner_idx % len(SPINNER_FRAMES)]} running"

    def _tick_spinner(self) -> None:
        self._spinner_idx += 1
        try:
            self.query_one("#status-row", Static).update(self._status_bar_text())
        except Exception:
            pass

    def on_mount(self) -> None:
        self.title = "headcleaner"
        self.sub_title = f"→ {self.opts.output_root}"
        self._log(paint(LOGO_SMALL, NEON_PINK, bold=True) + paint(f"  v{__version__}", NEON_CYAN))
        self._log(
            segment("  input:  ", FG_MUTED, dim=True)
            + paint(str(self.opts.input_root), NEON_PURPLE)
        )
        self._log(
            segment("  output: ", FG_MUTED, dim=True)
            + paint(str(self.opts.output_root), NEON_PURPLE)
        )
        self._log(
            segment("  format: ", FG_MUTED, dim=True)
            + segment(self.opts.fmt, NEON_CYAN, bold=True)
            + paint("  (ocr=on)" if self.opts.ocr else "", NEON_PINK)
        )
        self._log(
            segment("  started ", FG_MUTED, dim=True)
            + paint(datetime.now().isoformat(timespec="seconds"), NEON_CYAN_DIM)
        )
        self._log("")

        # Spinner tick
        self.set_interval(0.08, self._tick_spinner)

        # Run the pipeline on a worker thread so the UI stays responsive
        t = threading.Thread(target=self._run_in_thread, daemon=True)
        t.start()

    def _run_in_thread(self) -> None:
        def hook(i: int, total: int, result: FileResult) -> None:
            self.call_from_thread(self._on_progress, i, total, result)

        def engine_hook(engine: str, cur: int, total: int) -> None:
            self.call_from_thread(self._on_engine_progress, engine, cur, total)

        # Wire engine progress if the opts supports it
        try:
            self.opts.on_engine_progress = engine_hook
        except AttributeError:
            pass

        try:
            record = run_pipeline(_OptsProxy(self.opts, hook))
            self._finished = True
            self.call_from_thread(self._on_finished, record)
        except Exception as e:
            self._finished = True
            self.call_from_thread(self._on_error, e)

    def _on_engine_progress(self, engine: str, cur: int, total: int) -> None:
        """Eng #41: per-engine sub-bar update. Renders into the engine row."""
        try:
            row = self.query_one("#engine-row", Static)
        except Exception:
            return
        if total > 0:
            pct = int(100 * cur / total)
            row.update(paint(f"⟫ {engine:<10} ", NEON_PURPLE) +
                       paint(f"[{'█' * (pct // 5):<20}] ", NEON_CYAN) +
                       paint(f"{cur}/{total}", FG_TEXT))
        else:
            row.update("")

    def _on_progress(self, i: int, total: int, result: FileResult) -> None:
        bar = self.query_one("#bar", ProgressBar)
        bar.update(total=max(total, 1), progress=i)

        status = self._format_result(i, total, result)
        self._log(status)
        try:
            self.query_one("#status-row", Static).update(self._status_bar_text())
        except Exception:
            pass

    def _on_finished(self, record) -> None:
        ok = sum(1 for r in record.results if r.status == "ok")
        skipped = sum(1 for r in record.results if r.status == "skipped")
        failed = sum(1 for r in record.results if r.status == "failed")
        self._final_summary = (
            f"{ICON_DONE} ok={ok} skipped={skipped} failed={failed}"
        )
        self._log("")
        self._log(
            segment("  ✓ done  ", NEON_CYAN, bold=True)
            + segment(f"ok=", NEON_CYAN)
            + paint(str(ok), NEON_CYAN, bold=True)
            + segment(" skipped=", FG_MUTED)
            + paint(str(skipped), FG_MUTED)
            + segment(" failed=", NEON_PINK)
            + paint(str(failed), NEON_PINK, bold=True)
        )
        self._log(
            segment("  manifest: ", FG_MUTED, dim=True)
            + paint(f"{record.output_root}/manifest.json", NEON_PURPLE)
        )
        try:
            self.query_one("#status-row", Static).update(self._status_bar_text())
        except Exception:
            pass

    def _on_error(self, exc: Exception) -> None:
        msg = (
            segment("  � pipeline crashed: ", STATUS_FAILED, bold=True)
            + paint(str(exc), NEON_PINK)
        )
        self._log(msg)
        self._final_summary = f"{ICON_FAIL} crashed"
        try:
            self.query_one("#status-row", Static).update(self._status_bar_text())
        except Exception:
            pass

    def action_quit(self) -> None:
        if self._finished:
            self.exit()
        # else: ignore

    def _format_result(self, i: int, total: int, r: FileResult) -> str:
        sym_color = {
            "ok": (ICON_SUCCESS, STATUS_OK),
            "skipped": (ICON_SKIP, STATUS_SKIPPED),
            "failed": (ICON_FAIL, STATUS_FAILED),
        }.get(r.status, ("?", FG_MUTED))
        sym, color = sym_color
        engine = paint(f"{r.engine or '-':>10}", NEON_PURPLE)
        idx = paint(f"[{i:>3}/{total}]", FG_MUTED, dim=True)
        relpath = paint(r.relpath, FG_TEXT)
        suffix = (
            " " + paint(r.error, STATUS_FAILED, dim=True) if r.error else ""
        )
        return (
            "  "
            + paint(sym, color, bold=True)
            + " "
            + idx
            + " "
            + engine
            + "  "
            + relpath
            + suffix
        )

    def _log(self, msg: str) -> None:
        log = self.query_one("#log", Log)
        log.write_line(msg)


class _OptsProxy:
    """Wraps RunOptions so we can install our progress hook without mutating the caller's copy."""
    def __init__(self, opts: RunOptions, hook) -> None:
        self._opts = opts
        self.on_progress = hook
        for k, v in vars(opts).items():
            if k != "on_progress":
                setattr(self, k, v)


def run_with_tui(opts: RunOptions) -> int:
    """Launch the Textual TUI; returns the process exit code."""
    app = HeadCleanerApp(opts)
    app.run()
    return 0
