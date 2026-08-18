"""Pipeline runner — the non-TUI core.

This module does the actual work: walk → route → normalize → emit.
Both the plain CLI mode and the Textual TUI call into `run_pipeline()`.

Batch 2 enhancements (#14, #15, #16, #17):
  - **#14 Parallel pipeline** — `--jobs N` for `concurrent.futures.ProcessPoolExecutor`
  - **#15 Streaming manifest** — incremental JSONL append + final JSON
  - **#16 Idempotent cache** — skip files whose sha256 matches prior run's manifest
  - **#17 Resumable runs** — interrupted runs pick up where they left off

Batch 6 enhancement (#7):
  - **Multi-concept adapters** — PST/OST adapters returning one dict per
    message override `extract_messages()`. The runner detects this and
    emits one OKF concept per message instead of one per source file.
"""

from __future__ import annotations

import datetime as _dt
import json
import multiprocessing
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

from .diagnostics import Diagnostic, ExtractionMetrics, compute_confidence
from .emit import manifest as manifest_emit
from .emit import markdown as md_emit
from .emit import okf as okf_emit
from .emit import okf_index
from .emit.manifest import FileResult, RunRecord
from .engine_plan import build_engine_plan
from .engines.base import Adapter, AdapterError
from .jsonlog import emit_json_event  # Batch 4 / Eng #43
from .normalize import normalize
from .router import engine_capabilities, get_adapter
from .walk import walk


@dataclass
class RunOptions:
    input_root: Path
    output_root: Path
    fmt: str = "both"  # "md" | "okf" | "both"
    ocr: bool = False
    include_glob: list[str] | None = None
    exclude_glob: list[str] | None = None
    continue_on_error: bool = True
    write_okf_index: bool = True

    # Batch 2: parallelism + caching + resume
    jobs: int = 1  # 1 = sequential; >1 = process pool
    use_cache: bool = True  # skip files with unchanged sha256

    # Batch 3: Obsidian vault sync + future flags
    obsidian_compat: bool = False  # add flat fields to OKF frontmatter

    # Batch 4: OKF ecosystem
    enriched_index: bool = False  # show description + word count in index.md (Eng #38)
    write_log: bool = False  # append a dated entry to <bundle>/log.md (Eng #37)
    write_bundle_manifest: bool = False  # aggregate across runs into bundle.manifest.json (Eng #39)
    dry_run: bool = False  # Eng #42 — emit what would convert without writing
    json_output: bool = False  # Eng #43 — emit one JSON line per event on stdout

    # Contract 1.3: deterministic engine-selection policy (execution wiring follows).
    requested_engine: str | None = None
    allow_fallback: bool = False
    allow_network: bool = False

    # v0.8.0: heuristic cleanup pipeline (12 stages borrowed from any2md)
    clean_md: bool = False

    # Eng #41: per-engine sub-progress. Called with
    #   (engine_name, current_page, total_pages) for any adapter that
    #   reports sub-progress (PDF, multi-message adapters).
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
        # asdict + json ensure consistent field names for nested diagnostics.
        f.write(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True) + "\n")


# ---- Multi-concept adapter dispatch (Eng #7) ---------------------------------


def _is_multi_concept(adapter) -> bool:
    """True if the adapter overrides Adapter.extract_messages (multi-concept per source)."""
    return type(adapter).extract_messages is not Adapter.extract_messages


def _make_sf(path: Path, relpath: str | Path) -> object:
    """Build a small file-facts object that matches the ShapeFile ducktype."""
    return type(
        "SF", (), {"path": path, "relpath": Path(relpath), "size_bytes": path.stat().st_size}
    )()


def _per_message_relpath(source: Path, relpath: str, idx: int) -> str:
    """Derive a per-message relpath like `<relparent>/<stem>-0001.md`."""
    src = Path(relpath)
    parent = str(src.parent)
    if parent == ".":
        return f"{source.stem}-{idx:04d}.md"
    return f"{parent}/{source.stem}-{idx:04d}.md"


def _run_adapter(
    adapter,
    source: Path,
    relpath: str,
    ocr: bool,
    on_engine_progress: Callable[[str, int, int], None] | None,
    *,
    opts: RunOptions | None = None,
) -> list[tuple[str, dict]]:
    """Invoke an adapter and return a list of (relpath, extracted_dict) pairs.

    For most adapters, this is a single-element list. For multi-concept
    adapters (PST), each message gets its own (relpath, extracted_dict) pair.

    If ``opts.clean_md`` is True, the 12-stage heuristic cleanup pipeline
    (see headcleaner.heuristics) is applied to each extracted body_md before
    returning.
    """
    # Honor the OCR flag (PDF adapter only)
    if adapter.name == "pdf" and ocr and hasattr(adapter, "ocr"):
        adapter.ocr = True

    def _progress(cur: int, total: int) -> None:
        if on_engine_progress is not None:
            try:
                on_engine_progress(adapter.name, cur, total)
            except Exception:
                pass

    if _is_multi_concept(adapter):
        extracted_list = adapter.extract_messages(source, progress=_progress)
    else:
        extracted_list = [adapter.extract(source, progress=_progress)]

    # v0.8.0: optional heuristic cleanup pass (12 stages, borrowed from any2md)
    if opts is not None and getattr(opts, "clean_md", False):
        from .heuristics import clean_text

        extracted_list = [
            {**ext, "body_md": clean_text(ext.get("body_md", ""))} for ext in extracted_list
        ]

    pairs: list[tuple[str, dict]] = []
    for i, extracted in enumerate(extracted_list, start=1):
        if _is_multi_concept(adapter) and len(extracted_list) > 1:
            pairs.append((_per_message_relpath(source, relpath, i), extracted))
        else:
            pairs.append((relpath, extracted))
    return pairs


def _planned_adapters(source: Path, opts: RunOptions) -> list[tuple[Adapter, str]]:
    """Resolve the deterministic, policy-filtered adapter sequence for a source."""
    try:
        plan = build_engine_plan(
            source,
            engine_capabilities(),
            requested_engine=opts.requested_engine,
            allow_fallback=opts.allow_fallback,
            allow_network=opts.allow_network,
        )
    except ValueError as error:
        if str(error).startswith("unknown or incompatible engine:"):
            return []
        raise
    return [
        (adapter, attempt.reason)
        for attempt in plan.attempts
        if (adapter := get_adapter(source, requested_engine=attempt.engine)) is not None
    ]


def _run_planned_adapters(
    adapters: list[tuple[Adapter, str]], source: Path, relpath: str, opts: RunOptions
) -> tuple[Adapter, list[tuple[str, dict]], list[str], list[Diagnostic]]:
    """Run planned adapters, retrying only typed AdapterError failures."""
    attempts: list[str] = []
    diagnostics: list[Diagnostic] = []
    last_error: AdapterError | None = None
    for adapter, reason in adapters:
        attempts.append(adapter.name)
        try:
            pairs = _run_adapter(
                adapter, source, relpath, opts.ocr, opts.on_engine_progress, opts=opts
            )
        except AdapterError as error:
            diagnostics.append(
                Diagnostic(
                    code="ENGINE_ATTEMPT_FAILED",
                    severity="warning",
                    message=f"Engine {adapter.name} could not extract the source",
                    evidence={"engine": adapter.name, "reason": reason, "error": str(error)},
                )
            )
            last_error = error
            continue
        diagnostics.append(
            Diagnostic(
                code="ENGINE_ATTEMPT_SUCCEEDED",
                severity="info",
                message=f"Engine {adapter.name} extracted the source",
                evidence={"engine": adapter.name, "reason": reason},
            )
        )
        return adapter, pairs, attempts, diagnostics
    if last_error is not None:
        raise last_error
    raise AdapterError("no adapter")


def _emit_one(
    opts: RunOptions,
    record: RunRecord,
    source: Path,
    msg_rp: str,
    engine_name: str,
    extracted: dict,
    md_root: Path,
    okf_root: Path,
    engine_attempts: list[str] | None = None,
    engine_diagnostics: list[Diagnostic] | None = None,
) -> FileResult:
    """Normalize + emit one adapter output dict. Returns the FileResult."""
    result = FileResult(
        source_path=str(source),
        relpath=msg_rp,
        engine=engine_name,
        sha256=None,
        md_path=None,
        okf_path=None,
        status="skipped",
        diagnostics=list(engine_diagnostics or []),
    )
    doc = normalize(_make_sf(source, msg_rp), extracted, engine=engine_name)
    result.sha256 = doc.source_sha256
    result.metrics = ExtractionMetrics(
        character_count=len(doc.body_md),
        engine_attempts=engine_attempts or [engine_name],
        confidence_inputs={"required_anchors_ok": True, "ocr_warning": False},
    )
    result.confidence, _ = compute_confidence(result.metrics)

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

    if opts.dry_run:
        result.status = "ok" if doc.body_md else "failed"
    else:
        result.status = "ok" if (result.md_path or result.okf_path) else "failed"
    return result


# ---- Per-file worker (used by ProcessPoolExecutor) ---------------------------


def _process_one(args: tuple[str, str, str, str, bool, bool]) -> list[dict]:
    """Worker for parallel mode.

    Returns a list of FileResult-like dicts (orchestrator converts back).
    To avoid pickling the adapter, we re-rode the adapter on the orchestrator
    side; the worker only confirms the source is processable and returns
    the extracted list of bodies for the orchestrator to emit.
    """
    source_str, relpath, engine_name, fmt, ocr, clean_md, requested_engine = args
    from .engines.base import AdapterError
    from .router import get_adapter as _get_adapter

    # Build a minimal RunOptions shim so heuristics can be enabled in the worker.
    class _OptsShim:
        pass

    _opts = _OptsShim()
    _opts.clean_md = clean_md

    source = Path(source_str)
    started = time.perf_counter()
    adapter = _get_adapter(source, requested_engine=requested_engine)
    if adapter is None:
        return [
            {
                "source_path": str(source),
                "relpath": relpath,
                "engine": engine_name,
                "sha256": None,
                "md_path": None,
                "okf_path": None,
                "status": "skipped",
                "error": "no adapter",
                "duration_seconds": time.perf_counter() - started,
            }
        ]

    try:
        pairs = _run_adapter(adapter, source, relpath, ocr, None, opts=_opts)
    except AdapterError as e:
        return [
            {
                "source_path": str(source),
                "relpath": relpath,
                "engine": engine_name,
                "sha256": None,
                "md_path": None,
                "okf_path": None,
                "status": "failed",
                "error": str(e),
                "duration_seconds": time.perf_counter() - started,
            }
        ]
    except Exception as e:
        return [
            {
                "source_path": str(source),
                "relpath": relpath,
                "engine": engine_name,
                "sha256": None,
                "md_path": None,
                "okf_path": None,
                "status": "failed",
                "error": f"{type(e).__name__}: {e}",
                "duration_seconds": time.perf_counter() - started,
            }
        ]

    elapsed_per_result = (time.perf_counter() - started) / max(1, len(pairs))
    return [
        {
            "source_path": str(source),
            "relpath": msg_rp,
            "engine": engine_name,
            "sha256": None,
            "md_path": None,
            "okf_path": None,
            "status": "ok",
            "duration_seconds": elapsed_per_result,
            "_extracted": extracted,
        }
        for msg_rp, extracted in pairs
    ]


# ---- Sequential pipeline (default) ----------------------------------------


def _process_sequential(
    opts: RunOptions, record: RunRecord, cache: dict[str, dict], total: int, all_files
) -> None:
    """Process files one at a time; respects the cache."""
    md_root = opts.output_root / "_md"
    okf_root = opts.output_root / "okf"
    if opts.fmt in {"md", "both"}:
        md_root.mkdir(parents=True, exist_ok=True)
    if opts.fmt in {"okf", "both"}:
        okf_root.mkdir(parents=True, exist_ok=True)

    for i, sf in enumerate(all_files, start=1):
        rel = str(sf.relpath)
        adapters = _planned_adapters(sf.path, opts)
        adapter = adapters[0][0] if adapters else None
        if adapter is None:
            result = FileResult(
                source_path=str(sf.path),
                relpath=rel,
                engine=None,
                sha256=None,
                md_path=None,
                okf_path=None,
                status="skipped",
                error="no adapter",
                duration_seconds=0.0,
            )
            _finish_result(opts, record, result)
            continue

        # Cache hit?
        cached = cache.get(rel) if opts.use_cache else None
        if cached:
            from .walk import sha256_of

            current_sha = sha256_of(sf.path)
            if current_sha == cached["sha256"]:
                result = FileResult(
                    source_path=str(sf.path),
                    relpath=rel,
                    engine=adapter.name,
                    sha256=current_sha,
                    md_path=str(md_root / (Path(rel).name + ".md"))
                    if opts.fmt in {"md", "both"}
                    else None,
                    okf_path=str(okf_root / Path(rel).with_suffix(".md"))
                    if opts.fmt in {"okf", "both"}
                    else None,
                    status="ok",
                    duration_seconds=0.0,
                )
                record.results.append(result)
                if opts.on_progress:
                    opts.on_progress(i, total, result)
                continue

        started = time.perf_counter()
        try:
            adapter, pairs, attempts, diagnostics = _run_planned_adapters(
                adapters, sf.path, rel, opts
            )
        except AdapterError as e:
            result = FileResult(
                source_path=str(sf.path),
                relpath=rel,
                engine=adapter.name,
                sha256=None,
                md_path=None,
                okf_path=None,
                status="failed",
                error=str(e),
                duration_seconds=time.perf_counter() - started,
            )
            _finish_result(opts, record, result)
            if not opts.continue_on_error:
                return
            continue
        except Exception as e:
            result = FileResult(
                source_path=str(sf.path),
                relpath=rel,
                engine=adapter.name,
                sha256=None,
                md_path=None,
                okf_path=None,
                status="failed",
                error=f"{type(e).__name__}: {e}",
                duration_seconds=time.perf_counter() - started,
            )
            _finish_result(opts, record, result)
            if not opts.continue_on_error:
                return
            continue

        emitted = [
            _emit_one(
                opts,
                record,
                sf.path,
                msg_rp,
                adapter.name,
                extracted,
                md_root,
                okf_root,
                attempts,
                diagnostics,
            )
            for msg_rp, extracted in pairs
        ]
        elapsed_per_result = (time.perf_counter() - started) / max(1, len(emitted))
        for result in emitted:
            result.duration_seconds = elapsed_per_result
            _finish_result(opts, record, result)


# ---- Parallel pipeline (--jobs N) ------------------------------------------


def _process_parallel(
    opts: RunOptions, record: RunRecord, cache: dict[str, dict], total: int, all_files
) -> None:
    """Process files via ProcessPoolExecutor. For multi-message adapters,
    the worker returns the full extracted list; the orchestrator re-emits
    on the main process (subprocess can't easily write to the parent's
    filesystem state)."""
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
        adapter = get_adapter(sf.path, requested_engine=opts.requested_engine)
        engine_name = adapter.name if adapter else None

        if opts.use_cache and engine_name and rel in cache:
            from .walk import sha256_of

            if sha256_of(sf.path) == cache[rel]["sha256"]:
                result = FileResult(
                    source_path=str(sf.path),
                    relpath=rel,
                    engine=engine_name,
                    sha256=cache[rel]["sha256"],
                    md_path=str(md_root / (Path(rel).name + ".md"))
                    if opts.fmt in {"md", "both"}
                    else None,
                    okf_path=str(okf_root / Path(rel).with_suffix(".md"))
                    if opts.fmt in {"okf", "both"}
                    else None,
                    status="ok",
                    duration_seconds=0.0,
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
                duration_seconds=0.0,
            )
            _finish_result(opts, record, result)
            continue

        work.append(
            (
                str(sf.path),
                rel,
                engine_name,
                opts.fmt,
                opts.ocr,
                opts.clean_md,
                opts.requested_engine,
            )
        )

    if not work:
        return

    jobs = max(1, min(opts.jobs, multiprocessing.cpu_count()))
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(_process_one, w): w for w in work}
        for fut in as_completed(futures):
            results = fut.result()
            for r_dict in results:
                source = Path(r_dict["source_path"])
                if r_dict["status"] == "ok" and "_extracted" in r_dict:
                    emission_started = time.perf_counter()
                    result = _emit_one(
                        opts,
                        record,
                        source,
                        r_dict["relpath"],
                        r_dict["engine"],
                        r_dict["_extracted"],
                        md_root,
                        okf_root,
                    )
                    result.duration_seconds = float(r_dict.get("duration_seconds") or 0.0) + (
                        time.perf_counter() - emission_started
                    )
                else:
                    # Failed or synthetic — convert dict back to FileResult
                    result = FileResult(
                        source_path=r_dict["source_path"],
                        relpath=r_dict["relpath"],
                        engine=r_dict["engine"],
                        sha256=r_dict["sha256"],
                        md_path=r_dict["md_path"],
                        okf_path=r_dict["okf_path"],
                        status=r_dict["status"],
                        error=r_dict.get("error"),
                        duration_seconds=r_dict.get("duration_seconds"),
                    )
                _finish_result(opts, record, result)


# ---- Shared helpers ---------------------------------------------------------


def _finish_result(opts: RunOptions, record: RunRecord, result: FileResult) -> None:
    """Append to record + JSONL; call progress hook."""
    record.results.append(result)
    if opts.json_output:
        emit_json_event(
            {
                "event": "file",
                "index": len(record.results),
                "total": record.options.get("_total", 0),
                **asdict(result),
            }
        )
    # Stream to JSONL (one line per file) — enables resumability + audit
    _save_cache_jsonl(opts.output_root, result)
    if opts.on_progress:
        try:
            total = record.options.get("_total", 0) if hasattr(record, "options") else 0
        except Exception:
            total = 0
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
    all_files = [
        sf
        for sf in walk(
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

        emit_json_event(
            {
                "event": "start",
                "tool": "headcleaner",
                "version": _v,
                "format": opts.fmt,
                "dry_run": opts.dry_run,
                "files": total,
            }
        )

    if opts.jobs > 1 and not opts.allow_fallback:
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

        # Conversion report (v0.13.x — bonus item)
        from .emit.report import write_report

        try:
            started = _dt.datetime.fromisoformat(record.started_at)
            finished = _dt.datetime.fromisoformat(record.finished_at)
        except (TypeError, ValueError):
            started = finished = _dt.datetime.now()
        write_report(
            opts.output_root / "REPORT.md",
            [
                {
                    "relpath": r.relpath,
                    "engine": r.engine or "",
                    "status": r.status,
                    "sha256": r.sha256,
                    "error": r.error,
                    "duration_seconds": r.duration_seconds,
                }
                for r in record.results
            ],
            started_at=started,
            finished_at=finished,
            bundle_root=opts.input_root,
        )

    if opts.json_output:
        emit_json_event(
            {
                "event": "finish",
                "ok": sum(1 for r in record.results if r.status == "ok"),
                "skipped": sum(1 for r in record.results if r.status == "skipped"),
                "failed": sum(1 for r in record.results if r.status == "failed"),
            }
        )

    return record
