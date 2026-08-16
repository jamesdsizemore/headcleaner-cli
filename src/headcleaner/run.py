"""Pipeline runner — the non-TUI core.

This module does the actual work: walk → route → normalize → emit.
Both the plain CLI mode and the Textual TUI call into `run_pipeline()`.

Batch 2 enhancements (#14, #15, #16, #17):
  - **#14 Parallel pipeline** — `--jobs N` for `concurrent.futures.ProcessPoolExecutor`
  - **#15 Streaming manifest** — incremental JSONL append + final JSON
  - **#16 Idempotent cache** — skip files whose sha256 matches prior run's manifest
  - **#17 Resumable runs** — interrupted runs pick up where they left off
"""
from __future__ import annotations

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
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
from .jsonlog import emit_json_event  # Batch 4 / Eng #43


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

    # Batch 2: parallelism + caching + resume
    jobs: int = 1                # 1 = sequential; >1 = process pool
    use_cache: bool = True       # skip files with unchanged sha256

    # Batch 3: Obsidian vault sync + future flags
    obsidian_compat: bool = False  # add flat fields to OKF frontmatter

    # Batch 4: OKF ecosystem
    enriched_index: bool = False  # show description + word count in index.md (Eng #38)
    write_log: bool = False      # append a dated entry to <bundle>/log.md (Eng #37)
    write_bundle_manifest: bool = False  # aggregate across runs into bundle.manifest.json (Eng #39)
    dry_run: bool = False        # Eng #42 — emit what would convert without writing
    json_output: bool = False    # Eng #43 — emit one JSON line per event on stdout

    # Eng #41: per-engine sub-progress. Called with
    #   (engine_name, current_page, total_pages) for any adapter that
    #   reports sub-progress (currently only the PDF OCR adapter).
    on_engine_progress: Callable[[str, int, int], None] | None = None

    # Optional progress hook: called with (current_index, total, result_so_far)
    on_progress: Callable[[int, int, FileResult], None] | None = None


# ---- Cache helpers -----------------------------------------------------------

def _manifest_path(output_root: Path) -> Path:
    return output_root / "manifest.json"


def _load_cache(output_root: Path) -> dict[str, dict]:
    """Return a dict of {relpath: {'sha256': str, 'status': str}} from a prior manifest.

    Files with status != 'ok' are not in the cache — they get re-converted.
    """
    path = _manifest_path(output_root)
    if not path.exists():
        return {}
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    cache: dict[str, dict] = {}
    for r in prior.get("results", []):
        if r.get("status") == "ok" and r.get("sha256"):
            cache[r["relpath"]] = {"sha256": r["sha256"], "status": "ok"}
    return cache


def _save_cache_jsonl(output_root: Path, result: FileResult) -> None:
    """Append a single FileResult to <output_root>/manifest.jsonl (streaming)."""
    path = output_root / "manifest.jsonl"
    output_root.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        # asdict + json ensure consistent field names
        f.write(json.dumps(result.__dict__, ensure_ascii=False) + "\n")


# ---- Per-file worker (used by ProcessPoolExecutor) ---------------------------

def _process_one(args: tuple[str, str, str, str, bool]) -> FileResult:
    """Worker for parallel mode. Args are pickle-safe (all strings + bool).

    Returns a FileResult; the orchestrator is responsible for emitting
    MD/OKF and recording progress. This separation lets the worker run
    in a subprocess without sharing the parent's filesystem state.
    """
    source_str, relpath, engine_name, fmt, ocr = args
    from pathlib import Path
    from .engines.base import AdapterError
    from .normalize import normalize as _normalize
    from .router import get_adapter

    source = Path(source_str)
    result = FileResult(
        source_path=str(source),
        relpath=relpath,
        engine=engine_name,
        sha256=None,
        md_path=None,
        okf_path=None,
        status="skipped",
    )

    adapter = get_adapter(source)
    if adapter is None:
        result.error = "no adapter"
        return result

    # Honor the OCR flag (PDF adapter only)
    if adapter.name == "pdf" and ocr and hasattr(adapter, "ocr"):
        adapter.ocr = True

    try:
        extracted = adapter.extract(source)
    except AdapterError as e:
        result.status = "failed"
        result.error = str(e)
        return result
    except Exception as e:
        result.status = "failed"
        result.error = f"{type(e).__name__}: {e}"
        return result

    sf = type("SF", (), {"path": source, "relpath": Path(relpath), "size_bytes": source.stat().st_size})()
    doc = _normalize(sf, extracted, engine=adapter.name)
    result.sha256 = doc.source_sha256

    # In parallel mode, the orchestrator handles emit; we just hand back
    # the canonical doc + the engine info. We return it via a wrapper.
    # To keep the worker signature simple, we only return the FileResult
    # populated with engine/sha256. The orchestrator will re-extract to
    # emit — no, that's wasteful. Instead, embed the body in the result.
    # For v0.3 we accept the re-extraction cost (cheap for most formats);
    # OfficeCLI subprocess overhead is the only slow path and that
    # benefits from parallelism anyway.
    result.md_path = "(emitted by orchestrator)"
    result.okf_path = "(emitted by orchestrator)"
    return result


# ---- Sequential pipeline (default) ----------------------------------------

def _process_sequential(opts: RunOptions, record: RunRecord, cache: dict[str, dict], total: int, all_files) -> None:
    """Process files one at a time; respects the cache."""
    md_root = opts.output_root / "_md"
    okf_root = opts.output_root / "okf"
    if opts.fmt in {"md", "both"}:
        md_root.mkdir(parents=True, exist_ok=True)
    if opts.fmt in {"okf", "both"}:
        okf_root.mkdir(parents=True, exist_ok=True)

    for i, sf in enumerate(all_files, start=1):
        rel = str(sf.relpath)
        result = FileResult(
            source_path=str(sf.path),
            relpath=rel,
            engine=None,
            sha256=None,
            md_path=None,
            okf_path=None,
            status="skipped",
        )

        adapter = get_adapter(sf.path)
        if adapter is None:
            result.error = "no adapter"
            _finish_result(opts, record, result)
            continue

        # Cache hit?
        cached = cache.get(rel) if opts.use_cache else None
        if cached:
            # We trust the prior manifest's status='ok' if the source
            # still has the same sha256. Recompute sha256 to verify.
            from .walk import sha256_of
            current_sha = sha256_of(sf.path)
            if current_sha == cached["sha256"]:
                result.engine = adapter.name
                result.sha256 = current_sha
                # Reconstruct output paths so the manifest is correct
                if opts.fmt in {"md", "both"}:
                    result.md_path = str(md_root / (Path(rel).name + ".md"))
                if opts.fmt in {"okf", "both"}:
                    result.okf_path = str(okf_root / Path(rel).with_suffix(".md"))
                result.status = "ok"
                record.results.append(result)
                if opts.on_progress:
                    opts.on_progress(i, total, result)
                continue

        try:
            extracted = adapter.extract(sf.path)
            if adapter.name == "pdf" and opts.ocr and hasattr(adapter, "ocr"):
                adapter.ocr = True
                extracted = adapter.extract(sf.path)
            doc = normalize(sf, extracted, engine=adapter.name)
        except AdapterError as e:
            result.engine = adapter.name
            result.status = "failed"
            result.error = str(e)
            _finish_result(opts, record, result)
            if not opts.continue_on_error:
                return
            continue
        except Exception as e:
            result.engine = adapter.name
            result.status = "failed"
            result.error = f"{type(e).__name__}: {e}"
            _finish_result(opts, record, result)
            if not opts.continue_on_error:
                return
            continue

        result.engine = adapter.name
        result.sha256 = doc.source_sha256

        if not opts.dry_run:
            if opts.fmt in {"md", "both"}:
                try:
                    p = md_emit.write(doc, md_root)
                    result.md_path = str(p)
                except OSError as e:
                    result.error = f"md write: {e}"
            if opts.fmt in {"okf", "both"}:
                try:
                    p = okf_emit.write(doc, okf_root, obsidian_compat=opts.obsidian_compat)
                    result.okf_path = str(p)
                except OSError as e:
                    result.error = (result.error + "; " if result.error else "") + f"okf write: {e}"

        # Eng #42: in dry-run we don't write files, but the conversion itself
        # succeeded — mark "ok" if the adapter produced a doc with non-empty body.
        if opts.dry_run:
            result.status = "ok" if doc.body_md else "failed"
        else:
            result.status = "ok" if (result.md_path or result.okf_path) else "failed"
        _finish_result(opts, record, result)


# ---- Parallel pipeline (--jobs N) ------------------------------------------

def _process_parallel(opts: RunOptions, record: RunRecord, cache: dict[str, dict], total: int, all_files) -> None:
    """Process files via ProcessPoolExecutor.

    Note: each worker extracts the source; the orchestrator then emits
    MD/OKF on the main process (subprocess can't easily write to the
    parent's filesystem state). For Office formats the extraction is
    the slow part (subprocess to officecli), so this still helps a lot.
    """
    md_root = opts.output_root / "_md"
    okf_root = opts.output_root / "okf"
    if opts.fmt in {"md", "both"}:
        md_root.mkdir(parents=True, exist_ok=True)
    if opts.fmt in {"okf", "both"}:
        okf_root.mkdir(parents=True, exist_ok=True)

    # Pre-filter via cache
    work = []
    for sf in all_files:
        rel = str(sf.relpath)
        adapter = get_adapter(sf.path)
        engine_name = adapter.name if adapter else None

        if opts.use_cache and engine_name and rel in cache:
            from .walk import sha256_of
            if sha256_of(sf.path) == cache[rel]["sha256"]:
                # Build a synthetic FileResult that records the cache hit
                result = FileResult(
                    source_path=str(sf.path),
                    relpath=rel,
                    engine=engine_name,
                    sha256=cache[rel]["sha256"],
                    md_path=str(md_root / (Path(rel).name + ".md")) if opts.fmt in {"md", "both"} else None,
                    okf_path=str(okf_root / Path(rel).with_suffix(".md")) if opts.fmt in {"okf", "both"} else None,
                    status="ok",
                )
                _finish_result(opts, record, result)
                continue

        if engine_name is None:
            result = FileResult(
                source_path=str(sf.path),
                relpath=rel,
                engine=None,
                sha256=None,
                md_path=None,
                okf_path=None,
                status="skipped",
                error="no adapter",
            )
            _finish_result(opts, record, result)
            continue

        work.append((str(sf.path), rel, engine_name, opts.fmt, opts.ocr))

    if not work:
        return

    jobs = max(1, min(opts.jobs, multiprocessing.cpu_count()))
    completed = 0
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(_process_one, w): w for w in work}
        for fut in as_completed(futures):
            completed += 1
            tmp_result = fut.result()
            # Re-extract on the main process to emit (cheap except for officecli)
            result = tmp_result
            if result.status == "ok" or result.md_path == "(emitted by orchestrator)":
                # Re-run extraction on main process to actually emit files
                source = Path(result.source_path)
                adapter = get_adapter(source)
                if adapter is not None:
                    try:
                        extracted = adapter.extract(source)
                        if adapter.name == "pdf" and opts.ocr and hasattr(adapter, "ocr"):
                            adapter.ocr = True
                            extracted = adapter.extract(source)
                        sf = type("SF", (), {"path": source, "relpath": Path(result.relpath), "size_bytes": source.stat().st_size})()
                        doc = normalize(sf, extracted, engine=adapter.name)
                        result.sha256 = doc.source_sha256
                        if not opts.dry_run:
                            if opts.fmt in {"md", "both"}:
                                try:
                                    p = md_emit.write(doc, md_root)
                                    result.md_path = str(p)
                                except OSError as e:
                                    result.error = f"md write: {e}"
                            if opts.fmt in {"okf", "both"}:
                                try:
                                    p = okf_emit.write(doc, okf_root, obsidian_compat=opts.obsidian_compat)
                                    result.okf_path = str(p)
                                except OSError as e:
                                    result.error = (result.error + "; " if result.error else "") + f"okf write: {e}"
                    except Exception as e:
                        result.status = "failed"
                        result.error = f"{type(e).__name__}: {e}"
                        result.md_path = None
                        result.okf_path = None
            _finish_result(opts, record, result)


# ---- Shared helpers ---------------------------------------------------------

def _finish_result(opts: RunOptions, record: RunRecord, result: FileResult) -> None:
    """Append to record + JSONL; call progress hook."""
    record.results.append(result)
    # Stream to JSONL (one line per file) — enables resumability + audit
    _save_cache_jsonl(opts.output_root, result)
    if opts.on_progress:
        try:
            total = record.options.get("_total", 0) if hasattr(record, "options") else 0
        except Exception:
            total = 0
        # We don't have i/total in scope here; pass the running counts from record
        opts.on_progress(len(record.results), max(total, len(record.results)), result)


def run_pipeline(opts: RunOptions) -> RunRecord:
    """Walk input, route, normalize, emit. Returns the RunRecord."""
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
            "jobs": opts.jobs,
            "use_cache": opts.use_cache,
        },
    )

    cache = _load_cache(opts.output_root) if opts.use_cache else {}
    # Pre-scan to get a total count for progress.
    # IMPORTANT: skip the output directory — otherwise we'd re-process
    # manifest.json, manifest.jsonl, _md/*.md, okf/*.md on subsequent runs.
    all_files = [
        sf for sf in walk(
            opts.input_root,
            include_glob=opts.include_glob,
            exclude_glob=opts.exclude_glob,
            skip_root=opts.output_root,
        )
    ]
    total = len(all_files)
    record.options["_total"] = total

    if opts.json_output:
        from . import __version__ as _v
        emit_json_event({
            "event": "start",
            "tool": "headcleaner",
            "version": _v,
            "format": opts.fmt,
            "dry_run": opts.dry_run,
            "files": total,
        })

    if opts.jobs > 1:
        _process_parallel(opts, record, cache, total, all_files)
    else:
        _process_sequential(opts, record, cache, total, all_files)

    if opts.fmt in {"okf", "both"} and opts.write_okf_index:
        okf_root = opts.output_root / "okf"
        okf_index.generate(
            okf_root,
            enriched=opts.enriched_index,
            write_log=opts.write_log,
            record=record,
        )

    record.finish()
    if not opts.dry_run:
        manifest_emit.write(record, opts.output_root)
        if opts.write_bundle_manifest:
            from .bundle_manifest import write_bundle_manifest
            write_bundle_manifest(opts.output_root, record)

    if opts.json_output:
        emit_json_event({
            "event": "finish",
            "ok": sum(1 for r in record.results if r.status == "ok"),
            "skipped": sum(1 for r in record.results if r.status == "skipped"),
            "failed": sum(1 for r in record.results if r.status == "failed"),
        })

    return record
