# Routing and fallback

This page documents headcleaner's engine routing and fallback semantics. It explains how a source file becomes an adapter invocation, how engine plans are built, and when fallback is allowed.

## The routing table

The router lives in `src/headcleaner/router.py`. It maintains a tuple of adapter instances called `_ADAPTERS`. The order matters: the router walks the tuple in order and uses the first adapter whose `extensions` attribute includes the file's extension.

```python
_ADAPTERS: tuple[Adapter, ...] = (
    OfficeCliAdapter(),
    LibreOfficeAdapter(),
    PdfPlumberAdapter(),
    TesseractAdapter(),
    BeautifulSoupAdapter(),
    TxtAdapter(),
    EmlAdapter(),
    MsgAdapter(),
    PstAdapter(),
    # plugins appended here
)
```

To influence routing for a specific file, pass `--engine NAME`. To force the first-match engine and refuse fallback, pass `--no-fallback`. To refuse any network-capable engine even if the first-match requires it, pass `--no-network` (the default).

## Engine plans

The router does not call adapters directly. It builds an `EnginePlan` that records which adapters will be tried, in what order, and with what fallback rules. The plan is part of the audit trail and is reflected in the run manifest.

```python
@dataclass(frozen=True)
class EnginePlan:
    source: SourceRef
    requested_engine: str | None
    attempts: tuple[EngineAttempt, ...]
```

Each `EngineAttempt` records the engine name, the reason for the attempt, the outcome, and any diagnostic codes:

```python
@dataclass(frozen=True)
class EngineAttempt:
    engine: str
    reason: str
    outcome: str                         # ok | unavailable | failed | refused
    diagnostic_codes: tuple[str, ...]
```

The plan is built once per source file and is recorded in the manifest under the per-file result entry.

## Capabilities

Each adapter has an `EngineCapability` that describes what it requires:

```python
@dataclass(frozen=True)
class EngineCapability:
    name: str
    extensions: tuple[str, ...]
    requires_tools: tuple[str, ...]      # e.g. ("officecli",)
    network_mode: str                    # never | explicit
    priority: int                        # lower is higher priority
    supports_traits: frozenset[str]
```

The `requires_tools` is the set of external binaries the adapter needs (e.g. OfficeCLI for the DOCX adapter). The `network_mode` is `never` for adapters that never make network calls and `explicit` for adapters that can make network calls when explicitly configured. The `priority` is a tiebreaker for adapters that handle the same extensions.

## Fallback rules

Fallback is allowed only after a typed failure or low-confidence condition. The runner records each attempted engine but never executes an unavailable one, then considers the next declared candidate only when fallback is allowed.

The conditions that permit fallback:

- `AdapterError`: the adapter raised a typed exception during extraction.
- `ENGINE_REQUIRED_TOOL_UNAVAILABLE`: the adapter's required tool was not found.
- An explicit diagnostic code listed in `engine_plan.py` (e.g. `OCR_LOW_CONFIDENCE`).

The conditions that do not permit fallback:

- An untyped exception (e.g. a bare `RuntimeError`).
- A timeout.
- A network error in an adapter whose `network_mode` is `never`.

When fallback is not permitted, the source file is reported as `failed` and the runner moves to the next source file.

## ASCII: routing decision flow

```text
                  source file with extension X
                              |
                              v
                  +-----------------------+
                  | scan _ADAPTERS in     |
                  | priority order        |
                  +-----------------------+
                              |
              first adapter whose extensions match X
                              |
                              v
                  +-----------------------+
                  | adapter.requires_tools |
                  | all available?         |
                  +-----------------------+
                       |               |
                     yes              no
                       |               |
                       v               v
                  +-------+      +-----------------+
                  | execute |     | EngineAttempt   |
                  | adapter |     | outcome=        |
                  +-------+      | unavailable     |
                       |         +-----------------+
                  success?              |
                  /      \               v
              yes         no        next adapter in
                |          |        priority order
                v          v
          +---------+  +-------------+
          | Engine  |  | fallback    |
          | Attempt |  | allowed?    |
          | outcome |  +-------------+
          | = ok    |    /        \
          +---------+   yes         no
                              |          |
                              v          v
                       try next    record failed,
                       adapter     stop
```

## Building a plan with `--engine`

When you pass `--engine NAME`, the plan contains exactly one attempt: the named engine. The runner refuses to fall back to a different engine unless `--allow-fallback` is also passed. This is how you pin a specific engine for testing.

## Building a plan with `--no-fallback`

When you pass `--no-fallback`, the runner accepts exactly one attempt per source file. If the first attempt fails (typed or otherwise), the source is reported as `failed` and the runner moves on. This is how you enforce strict routing.

## Doctor and capabilities

`headcleaner doctor` reports which adapters are available based on the resolved toolchain. The output lists each adapter's name, its required tools, and whether they are present. If an adapter is reported as unavailable, the file extensions it handles will be skipped (with a message naming the missing tool) unless an alternative adapter handles the same extension with higher priority.

## What to read next

The [tool and engine development guide](tool-and-engine-development.md) walks through adding a new adapter. The [configuration development guide](configuration-development.md) covers the policy file format. The [architecture developer guide](architecture.md) explains how the router fits into the larger pipeline.