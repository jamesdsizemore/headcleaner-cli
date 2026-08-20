# Sync and watch

This page documents headcleaner's rename/deletion-safe sync state and the watcher that invokes sync in dry-run planning mode. It covers the data model, the reconciliation rules, the CLI commands, and the watcher's event handling.

## The sync module

The sync module lives in `src/headcleaner/sync.py`. The entry points are `plan_sync`, `reconcile`, `records_from_results`, `load_state`, and `save_state`.

## The state model

The sync state is a list of `SyncRecord` objects persisted to `<bundle>/.headcleaner/sync.json`. The write is atomic through temp+rename.

```python
@dataclass(frozen=True)
class SyncRecord:
    source_sha256: str
    current_relpath: str
    prior_relpaths: tuple[str, ...]
    generated_paths: tuple[str, ...]
    generation: int
    output_hashes: dict[str, str]        # relpath -> sha256
    last_seen_at: str
```

Records are keyed by `(current_relpath, source_sha256)` so identical-content files at different paths retain distinct lineage. The keying is what makes rename tracking possible: if a file's path changes but its SHA stays the same, the old record's lineage is preserved through `prior_relpaths`.

## Reconciliation rules

`reconcile` walks the previous state and the current sources (a dict of `relpath -> sha256`) and produces a plan. For each record:

- **Renamed**: a matching SHA exists at a different path. The plan records `{status: renamed, from, to}`. With `--apply`, the state is updated with the new path, an incremented generation, and the old path added to `prior_relpaths`.
- **Unchanged**: the matching SHA is at the recorded path. The plan records `{status: unchanged, path}` and the record is preserved.
- **Deleted candidate**: no matching SHA exists. The plan records `{status: deleted_candidate, path}` unless the generated outputs have been modified, in which case it records `{status: SYNC_CONFLICT, path}`.
- **Pruned**: with `--apply --prune-generated`, deleted candidates whose generated paths still exist and still match their recorded `output_hashes` are deleted from disk. Modified outputs are never deleted.

## Conflict refusal

If a generated file has been modified since the last sync (its current hash differs from `output_hashes[relative]`), `reconcile` reports `SYNC_CONFLICT` and refuses to prune it. The plan entry lists the conflicting path(s); the state is preserved as-is for that record.

This is the safety property the contract requires: `--prune-generated` never silently removes user-modified output.

## Pipeline integration

After every successful conversion run, the pipeline calls `records_from_results` to build `SyncRecord`s from the `FileResult` list, merges them with the previous state (keyed by `(current_relpath, source_sha256)`), increments generations, hashes owned generated paths, and calls `save_state`.

The pipeline records the state path and record count in the manifest's `options.sync` field. Downstream tools can read the state to know which source files were processed, which generated outputs headcleaner owns, and what hashes it expects them to have.

## The watcher

The watcher lives in `src/headcleaner/watch.py`. It uses `watchfiles` to observe the input folder and emits a normalized event list on each tick.

### Normalization

The watcher maintains a small in-memory buffer of pending events. On each tick, it normalizes the events by:

- Retaining `delete` events (even though the path no longer passes `is_file()` after the delete).
- Excluding events whose path is inside the output root (output writes must not be mistaken for source changes).
- Coalescing multiple events for the same path into a single event with the latest metadata.

The normalization is pure and testable: given an input event list and the output root, the normalized list is deterministic. The watcher tests do not require a live watcher; they call the normalizer directly.

### Sync invocation

The watcher's loop calls `plan_sync` (dry-run, no apply) and forwards the plan to the user. The user is expected to inspect the plan and run `headcleaner sync --apply` explicitly. The watcher never applies changes silently.

This is the contract: watch is dry-run planning mode; apply is a separate explicit command.

## ASCII: sync lifecycle

```text
   input folder                       .headcleaner/sync.json
        |                                     |
        | walk + sha256_of                    | load_state
        v                                     v
   +-----------+                        +-----------+
   | sources   | ---- compare ---->     | records   |
   +-----------+                        +-----------+
        |                                     |
        |                                     v
        |                              +-------------+
        |                              | reconcile   |
        |                              +-------------+
        |                                     |
        |                                     v
        |                              +-------------+
        +----------------------------> | plan        |
                                       +-------------+
                                              |
                                              v
                                       dry-run (default)
                                       apply (with --apply)
                                       + --prune-generated

                                       atomic write of new state
```

## What to read next

The [canonical model developer guide](canonical-model.md) documents the `SyncRecord` dataclass. The [architecture developer guide](architecture.md) explains how the sync module fits into the larger pipeline. The [safety overview](../safety/safety-overview.md) documents the safety invariants that sync enforces.