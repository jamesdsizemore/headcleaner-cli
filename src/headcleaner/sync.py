"""Dry-run-first source rename/deletion synchronization state and reconciliation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SyncRecord:
    source_sha256: str
    current_relpath: str
    prior_relpaths: tuple[str, ...]
    generated_paths: tuple[str, ...]
    generation: int
    output_hashes: dict[str, str]
    last_seen_at: str


def state_path(output_root: Path) -> Path:
    return output_root / ".headcleaner" / "sync.json"


def load_state(output_root: Path) -> list[SyncRecord]:
    path = state_path(output_root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("SYNC_STATE_CORRUPT") from exc
    return [
        SyncRecord(
            **{
                **item,
                "prior_relpaths": tuple(item["prior_relpaths"]),
                "generated_paths": tuple(item["generated_paths"]),
            }
        )
        for item in data
    ]


def save_state(output_root: Path, records: Iterable[SyncRecord]) -> Path:
    path = state_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, dir=path.parent
    ) as handle:
        json.dump([asdict(record) for record in records], handle, sort_keys=True)
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records_from_results(
    results: Iterable[Any],
    output_root: Path,
    *,
    previous: Iterable[SyncRecord] = (),
    seen_at: str,
) -> list[SyncRecord]:
    """Merge successful pipeline output ownership into durable sync state."""
    records = {(record.current_relpath, record.source_sha256): record for record in previous}
    for result in results:
        if result.status != "ok" or not result.sha256:
            continue
        generated_paths: list[str] = []
        output_hashes: dict[str, str] = {}
        for value in (result.md_path, result.okf_path):
            if not value:
                continue
            path = Path(value)
            if path.is_absolute():
                path = path.relative_to(output_root)
            relative = path.as_posix()
            output = output_root / path
            if output.is_file():
                generated_paths.append(relative)
                output_hashes[relative] = _hash(output)
        if not generated_paths:
            continue
        key = (result.relpath, result.sha256)
        prior = records.get(key)
        records[key] = SyncRecord(
            source_sha256=result.sha256,
            current_relpath=result.relpath,
            prior_relpaths=prior.prior_relpaths if prior else (),
            generated_paths=tuple(sorted(generated_paths)),
            generation=(prior.generation + 1) if prior else 1,
            output_hashes=output_hashes,
            last_seen_at=seen_at,
        )
    return [records[key] for key in sorted(records)]


def plan_sync(input_root: Path, output_root: Path) -> list[dict[str, Any]]:
    """Return the dry-run reconciliation plan used by CLI and watcher flows."""
    from .walk import sha256_of, walk

    sources = {
        source.relpath.as_posix(): source.sha256 or sha256_of(source.path)
        for source in walk(input_root)
    }
    return reconcile(load_state(output_root), sources, output_root, dry_run=True, apply=False)


def reconcile(
    records: Iterable[SyncRecord],
    current_sources: dict[str, str],
    output_root: Path,
    *,
    dry_run: bool = True,
    apply: bool = False,
    prune_generated: bool = False,
) -> list[dict[str, str]]:
    if apply and dry_run:
        dry_run = False
    if not dry_run and not apply:
        raise ValueError("SYNC_APPLY_REQUIRED")
    plan: list[dict[str, str]] = []
    updated: list[SyncRecord] = []
    for record in records:
        matching = sorted(
            path for path, sha in current_sources.items() if sha == record.source_sha256
        )
        if matching and matching[0] != record.current_relpath:
            plan.append({"status": "renamed", "from": record.current_relpath, "to": matching[0]})
            updated.append(
                replace(
                    record,
                    current_relpath=matching[0],
                    prior_relpaths=tuple(sorted({*record.prior_relpaths, record.current_relpath})),
                    generation=record.generation + 1,
                )
                if apply
                else record
            )
            continue
        if matching:
            plan.append({"status": "unchanged", "path": record.current_relpath})
            updated.append(record)
            continue
        conflicts = []
        for relative in record.generated_paths:
            output = output_root / relative
            if output.exists() and record.output_hashes.get(relative) != _hash(output):
                conflicts.append(relative)
        if conflicts:
            plan.append({"status": "SYNC_CONFLICT", "path": ",".join(conflicts)})
            updated.append(record)
        elif apply and prune_generated:
            for relative in record.generated_paths:
                output = output_root / relative
                if output.exists():
                    output.unlink()
            plan.append({"status": "pruned", "path": record.current_relpath})
        else:
            plan.append({"status": "deleted_candidate", "path": record.current_relpath})
            updated.append(record)
    if apply:
        by_identity = {(record.current_relpath, record.source_sha256): record for record in updated}
        save_state(output_root, [by_identity[key] for key in sorted(by_identity)])
    return plan
