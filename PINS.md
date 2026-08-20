# Pins

This page records intentional compatibility pins. `pyproject.toml` and `uv.lock` remain authoritative; update this page in the same change whenever a pin is added, changed, or removed.

## Interpreter

- `.python-version`: Python **3.12**.
- Supported range: `>=3.12,<3.14` in `pyproject.toml`.
- Verification baseline: Python 3.13 through `uv run --no-sync --python 3.13`.

## Direct package pins

| Package | Pin | Reason / owner |
|---|---:|---|
| `rapidfuzz` | `3.14.5` | Phase 2 deterministic fuzzy matching surface. |
| `sentence-transformers` | `6.0.0` | Phase 2 local embedding integration surface. |
| `qdrant-client` | `1.19.0` | Phase 2 vector-store integration surface. |
| `mcp` | `1.29.0` | Phase 2 MCP protocol integration surface. |

## Pin changes

A pin change requires: rationale in [BACKLOG.md](BACKLOG.md), update here and in [DEPENDENCIES.md](DEPENDENCIES.md), `uv lock --check`, affected compatibility docs, and the current phase documentation audit.
