# Serve development

This page documents the headcleaner local HTTP server: the framework used, the endpoint implementations, and the conventions for adding new endpoints.

## The serve module

The serve module lives in `src/headcleaner/serve.py`. The entry point is the `serve` Click command in `src/headcleaner/cli.py`, which constructs the FastAPI app and runs it with uvicorn.

## The framework

The HTTP server uses FastAPI for routing and request validation, and uvicorn for the ASGI runtime. The pinned versions are in `pyproject.toml` and `uv.lock`; the server uses the locked versions.

The server binds to `127.0.0.1` by default and accepts only loopback connections. Binding to a non-loopback interface requires explicit `--host` argument; the server does not check environment variables to make that decision.

## The endpoints

The endpoints are documented in the [Serve API reference](../reference/serve-api-reference.md). The implementations all share the same conventions:

- Every endpoint accepts a `bundle` path; the server validates it before any work is done.
- Every endpoint that returns content includes the source citation and trust state in the response.
- Every endpoint that can fail returns a structured error envelope with a stable `code`.
- Every endpoint is read-only; no endpoint mutates the bundle, the index, or any other state.

## Adding a new endpoint

The recipe for adding a new HTTP endpoint:

1. Decide whether the endpoint belongs in headcleaner's HTTP surface. The criteria are: is the underlying functionality read-only? does it fit the citation-first contract? does it not duplicate an existing endpoint's capability?
2. Implement the endpoint function in `src/headcleaner/serve.py`. The function is a FastAPI path operation decorated with `@app.get("/api/...")`. It accepts the bundle path plus any endpoint-specific query parameters and returns a JSON-serializable response.
3. Add the endpoint to the `app` object. The server constructs the app at startup; adding the endpoint is as simple as defining the function and decorating it.
4. Add a test in `tests/test_serve.py`. The minimum coverage is: the endpoint is reachable, a successful call returns the expected shape, a failure call returns the expected error code, the endpoint never writes to the bundle.
5. Add the endpoint to the [Serve API reference](../reference/serve-api-reference.md). Document URL shape, query parameters, response shape, and error codes.

## Endpoint conventions

Endpoint functions follow these conventions:

- The bundle path is passed as a query parameter `bundle=...` or path parameter `{bundle}`. The server converts it to `Path` and validates it.
- Optional query parameters use FastAPI's `Optional[T] = None` syntax and are documented in the OpenAPI schema automatically.
- Parameters that are enums use `Literal["a", "b", "c"]` so the schema correctly enumerates the allowed values.
- The return type is `dict[str, Any]`. FastAPI serializes it to JSON automatically.

## Error handling

When an endpoint returns an error, the response body is the error envelope documented in the [Serve API reference](../reference/serve-api-reference.md). The HTTP status code is appropriate to the error:

- `400` for malformed input (invalid FTS5 syntax, invalid path).
- `404` for missing resources (index not found, concept not found).
- `500` for internal errors.

The `code` field is stable across versions and is the right thing to switch on programmatically.

## The shared search function

The HTTP server and the CLI share the same `search` function from `src/headcleaner/search.py`. The endpoint function is a thin wrapper that parses query parameters, calls `search`, and serializes the result. There is no divergent implementation between the CLI and the HTTP surface.

This sharing is enforced by the tests: `tests/test_serve.py` and `tests/test_search.py` both call `search` directly and compare results to ensure consistency.

## What to read next

The [serve overview](../integrations/serve-overview.md) is the conceptual background. The [Serve API reference](../reference/serve-api-reference.md) is the complete endpoint reference. The [chunking and indexing developer guide](chunking-and-indexing.md) covers the search implementation.