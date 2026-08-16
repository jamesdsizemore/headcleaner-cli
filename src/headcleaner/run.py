"""Pipeline runner — the non-TUI core.

This module does the actual work: walk → route → normalize → emit.
Both the plain CLI mode and the Textual TUI call into `run_pipeline()`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .emit import manifest as manifest_emit
from .emit import markdown as md_emit
from .emit import okf as okf_emit
from .emit import okf_index
from .emit.manifest import FileResult, RunRecord
from .engines.base import AdapterError
from .normalize import normalize
from .router import get_adapter
from .walk import walk


@dataclass
class RunOptions:
    input_root: Path
    output_root: Path
    fmt: str = "both"            # "md" | "okf" | "both"
    ocr: bool = False
    include_glob: list[str] | None = None
    exclude_glob: list[str] | None = None
    continue_on_error: bool = True
    write_okf_index: bool = True

    # Optional progress hook: called with (current_index, total, result_so_far)
    on_progress: Callable[[int, int, FileResult], None] | None = None


def run_pipeline(opts: RunOptions) -> RunRecord:
    """Walk input, route, normalize, emit. Returns the RunRecord.

    Emits Markdown to <output_root>/_md/, OKF bundle to <output_root>/okf/,
    manifest.json to <output_root>/.
    """
    record = RunRecord(
        started_at=manifest_emit._utc_now_iso(),
        input_root=str(opts.input_root.resolve()),
        output_root=str(opts.output_root.resolve()),
        format=opts.fmt,
        options={
            "ocr": opts.ocr,
            "include_glob": opts.include_glob,
            "exclude_glob": opts.exclude_glob,
            "continue_on_error": opts.continue_on_error,
        },
    )

    md_root = opts.output_root / "_md"
    okf_root = opts.output_root / "okf"

    if opts.fmt in {"md", "both"}:
        md_root.mkdir(parents=True, exist_ok=True)
    if opts.fmt in {"okf", "both"}:
        okf_root.mkdir(parents=True, exist_ok=True)

    # Pre-scan to get a total count for progress
    all_files = list(walk(opts.input_root, include_glob=opts.include_glob, exclude_glob=opts.exclude_glob))
    total = len(all_files)

    for i, sf in enumerate(all_files, start=1):
        result = FileResult(
            source_path=str(sf.path),
            relpath=str(sf.relpath),
            engine=None,
            sha256=None,
            md_path=None,
            okf_path=None,
            status="skipped",
        )

        adapter = get_adapter(sf.path)
        if adapter is None:
            result.status = "skipped"
            result.error = "no adapter"
            record.results.append(result)
            if opts.on_progress:
                opts.on_progress(i, total, result)
            continue

        try:
            extracted = adapter.extract(sf.path)
            # Apply OCR opt-in for PDF
            if adapter.name == "pdf" and opts.ocr and hasattr(adapter, "ocr"):
                adapter.ocr = True
                extracted = adapter.extract(sf.path)
            doc = normalize(sf, extracted, engine=adapter.name)
        except AdapterError as e:
            result.engine = adapter.name
            result.status = "failed"
            result.error = str(e)
            record.results.append(result)
            if not opts.continue_on_error:
                record.finish()
                manifest_emit.write(record, opts.output_root)
                return record
            if opts.on_progress:
                opts.on_progress(i, total, result)
            continue
        except Exception as e:
            result.engine = adapter.name
            result.status = "failed"
            result.error = f"{type(e).__name__}: {e}"
            record.results.append(result)
            if not opts.continue_on_error:
                record.finish()
                manifest_emit.write(record, opts.output_root)
                return record
            if opts.on_progress:
                opts.on_progress(i, total, result)
            continue

        result.engine = adapter.name
        result.sha256 = doc.source_sha256

        if opts.fmt in {"md", "both"}:
            try:
                p = md_emit.write(doc, md_root)
                result.md_path = str(p)
            except OSError as e:
                result.error = f"md write: {e}"

        if opts.fmt in {"okf", "both"}:
            try:
                p = okf_emit.write(doc, okf_root)
                result.okf_path = str(p)
            except OSError as e:
                result.error = (result.error + "; " if result.error else "") + f"okf write: {e}"

        result.status = "ok" if (result.md_path or result.okf_path) else "failed"
        record.results.append(result)

        if opts.on_progress:
            opts.on_progress(i, total, result)

    if opts.fmt in {"okf", "both"} and opts.write_okf_index:
        okf_index.generate(okf_root)

    record.finish()
    manifest_emit.write(record, opts.output_root)
    return record
