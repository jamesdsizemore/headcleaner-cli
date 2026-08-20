# Issues

This is the repository-owned issue and recovery ledger. Record real defects, failed verification, and operational blockers here as they occur. Do not use it to record private credentials or transient command noise.

## Open repository-owned issues

None.

## Resolved issues

| ID | First observed | Scope | Evidence | Owner | Status | Resolution |
|---|---|---|---|---|---|---|
| HC-20260820-001 | 2026-08-20 | Pydantic forward-reference and Starlette/httpx deprecation warnings in the full suite. | Focused MCP/serve regressions and a full `pytest -W error` run pass. | repository | resolved | Rebuilt FastMCP settings annotations after import and migrated test ASGI requests to `httpx.ASGITransport`. |

A closed issue remains in this file with its evidence and recovery; archive rather than delete when the ledger becomes large.
