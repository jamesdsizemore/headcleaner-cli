"""Live folder watcher — re-convert when files change.

`headcleaner watch <INPUT_DIR> [--output DIR] [--debounce <secs>]`

Watches the input directory using `watchfiles` (already a dependency of
textual). When any file's mtime or content changes, runs the same
pipeline as `headcleaner convert` against the changed file (incremental),
or the full folder if `--full` is passed.

Press Ctrl+C to stop. On a clean run exit, the watcher prints a summary.

The `watchfiles` import is deferred to call time so this module loads
cleanly even on minimal installs where the Rust extension is missing.
"""

from __future__ import annotations

import signal
import threading
from collections.abc import Callable
from pathlib import Path

from .run import RunOptions


class WatchfilesMissingError(RuntimeError):
    """Raised when the watchfiles Rust extension isn't available."""


def collect_watch_changes(changes: set[tuple[int, str]], *, output_root: Path) -> set[Path]:
    """Normalize a watchfiles batch without dropping deleted-source events."""
    pending: set[Path] = set()
    resolved_output = output_root.resolve()
    for event, path in changes:
        candidate = Path(path)
        try:
            candidate.relative_to(resolved_output)
            continue
        except ValueError:
            pass
        if event == 3 or candidate.is_file():
            pending.add(candidate)
    return pending


def watch_directory(
    opts,  # RunOptions — type-hinted loosely to avoid import cycles in tests
    *,
    debounce_ms: int = 500,
    on_change: Callable[[set[Path]], None] | None = None,
    on_run_complete: Callable[[object], None] | None = None,
) -> None:
    """Watch `opts.input_root` and re-convert on changes.

    Blocking call. Returns when interrupted with Ctrl+C.

    Args:
        opts: RunOptions controlling the convert behavior. `input_root` is
            watched; `output_root` is written to.
        debounce_ms: minimum interval between re-conversions, to avoid
            thrashing when many files change at once (e.g., a bulk copy).
        on_change: optional callback called with the set of changed paths
            before each re-conversion (for the TUI to display).
        on_run_complete: optional callback called with the RunRecord
            after each re-conversion completes. Used by the CLI to POST
            the manifest to a webhook URL.
    """
    try:
        from watchfiles import watch as wf_watch

        from . import __version__
        from .run import run_pipeline
        from .sync import plan_sync
    except ImportError as e:
        raise WatchfilesMissingError(
            "watchfiles (with Rust extension) is required for `headcleaner watch`. "
            f"Install with: uv add watchfiles. ({e})"
        ) from e

    input_root = opts.input_root.resolve()

    stop_event = threading.Event()

    def _stop(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    print(f"⚡ headcleaner {__version__} watching {input_root} (Ctrl+C to stop)")

    # Process events in batches separated by debounce_ms of quiet.
    # `watchfiles.watch()` returns a generator yielding sets of (path, event)
    # tuples where event is 1=created, 2=modified, 3=deleted.
    pending: set[Path] = set()

    for changes in wf_watch(str(input_root), stop_event=stop_event, step=max(50, debounce_ms)):
        pending.update(collect_watch_changes(changes, output_root=opts.output_root))

        if not pending:
            continue

        if on_change:
            on_change(set(pending))

        # Re-run the pipeline. We use a single fresh RunOptions so the
        # runner doesn't try to reuse stale state.
        run_opts = RunOptions(
            input_root=input_root,
            output_root=opts.output_root,
            fmt=opts.fmt,
            ocr=opts.ocr,
            include_glob=opts.include_glob,
            exclude_glob=opts.exclude_glob,
            continue_on_error=opts.continue_on_error,
            write_okf_index=opts.write_okf_index,
            jobs=opts.jobs,
            use_cache=opts.use_cache,
        )
        record = run_pipeline(run_opts)
        n_ok = sum(1 for r in record.results if r.status == "ok")
        n_failed = sum(1 for r in record.results if r.status == "failed")
        print(f"  ✓ {n_ok} ok · {n_failed} failed · {len(pending)} change(s)")
        try:
            sync_plan = plan_sync(input_root, opts.output_root)
        except ValueError as error:
            print(f"  sync planning failed: {error}")
        else:
            print(f"  sync dry-run: {len(sync_plan)} action(s)")
        if on_run_complete:
            try:
                on_run_complete(record)
            except Exception:
                pass
        pending.clear()
