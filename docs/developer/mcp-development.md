# MCP development

This page documents the headcleaner MCP server: the protocol used, the tool implementations, and the conventions for adding new tools.

## The MCP standard

The Model Context Protocol is a JSON-RPC-based protocol for tool use. Headcleaner speaks MCP over stdio: the client starts the server as a subprocess, sends JSON-RPC requests on the subprocess's stdin, and reads responses on stdout. Stderr is reserved for the server's own logging.

The pinned MCP version is `mcp==1.29.0`. The compatibility shim lives under `mcp.server.fastmcp.FastMCP`. The server uses the standard tool registration mechanism provided by the FastMCP API.

## The server module

The MCP server lives in `src/headcleaner/mcp.py`. The entry point is the `mcp` Click command in `src/headcleaner/cli.py`, which constructs the FastMCP server, registers every tool, and runs the stdio loop.

## The tools

The server exposes the tools documented in the [MCP tool reference](../reference/mcp-tool-reference.md). The implementations all share the same conventions:

- Every tool returns a structured envelope with `schema_version`, `tool`, `ok`, `data`, `warnings`, and `errors`.
- Every tool that returns content includes the source citation and trust state in the `data` field.
- Every tool that can fail returns a structured error with a stable `code`.
- Every tool is read-only; no tool writes to the bundle, the index, or any other state.

## Adding a new tool

The recipe for adding a new MCP tool:

1. Decide whether the tool belongs in headcleaner's MCP surface. The criteria are: is the underlying functionality read-only? does it fit the citation-first contract? does it not duplicate an existing tool's capability?
2. Implement the tool function in `src/headcleaner/mcp.py`. The function takes a bundle path plus any tool-specific parameters. It returns a dict matching the envelope shape.
3. Register the tool with the FastMCP server using the `@mcp.tool()` decorator. The decorator accepts the tool's name, description, and parameter schema.
4. Add a test in `tests/test_mcp.py`. The minimum coverage is: the tool appears in the tool list, a successful call returns the expected envelope, a failure call returns the expected error code.
5. Add the tool to the [MCP tool reference](../reference/mcp-tool-reference.md). Document parameters, return shape, and safety properties.

## Tool signature conventions

Tool signatures follow these conventions:

- The first parameter is always `bundle: Path`. The MCP client passes the bundle path as a string; the server converts to `Path`.
- Optional parameters use `Optional[T] = None` and are documented in the parameter schema.
- Parameters that are enums use `Literal["a", "b", "c"]` so the schema correctly enumerates the allowed values.
- The return type is `dict[str, Any]`. The dict must include the envelope fields.

## Error handling

When a tool call fails, the envelope's `ok` is `false` and `errors` is non-empty. Each error is a dict with `code`, `message`, and optional `details`. The codes are stable across versions; clients can switch on them programmatically.

The most common error codes:

- `INDEX_NOT_FOUND` — the search index does not exist for the bundle.
- `BUNDLE_NOT_FOUND` — the bundle directory does not exist or is not readable.
- `INVALID_QUERY` — the search query had invalid FTS5 syntax.
- `CONCEPT_NOT_FOUND` — a specific concept ID did not match any concept in the bundle.
- `POLICY_INVALID` — a policy file could not be parsed.
- `INTERNAL_ERROR` — an unexpected error occurred; this is the catch-all.

## Stdout and stderr discipline

The MCP server writes JSON-RPC responses to stdout and logs to stderr. Headcleaner's logging is configured to write to stderr at WARN level or below; INFO and DEBUG messages do not appear by default. This means the client can rely on stdout being pure JSON-RPC.

If you add a tool that needs to print diagnostic information, use `print(..., file=sys.stderr)`. Never print to stdout outside the JSON-RPC response loop.

## Real-server testing

The MCP tests use a real MCP client (the `mcp` Python library's test client) and a real headcleaner server (spawned in-process). The tests do not mock the protocol layer; they exercise the full request/response cycle. This is what gives the contract tests their authority.

The test file is `tests/test_mcp.py`. Each test:

- Spawns the server in-process.
- Connects a client.
- Calls the tool with a known bundle and parameters.
- Asserts the envelope shape and the data fields.
- Closes the client and server.

## Compatibility

The server pins `mcp==1.29.0`. The compatibility shim is `MCPServer` in `src/headcleaner/mcp.py`, which wraps `mcp.server.fastmcp.FastMCP` to expose the same tool names as the original server. New tools should use the FastMCP decorator pattern; the shim is for backward compatibility with existing tests and clients.

## What to read next

The [MCP overview](../integrations/mcp-overview.md) is the conceptual background. The [MCP client setup](../integrations/mcp-client-setup.md) has per-assistant configuration recipes. The [MCP tool reference](../reference/mcp-tool-reference.md) documents every tool the server exposes.