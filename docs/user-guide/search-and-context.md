# Search and context

Once you have a converted output folder, the next thing most people want is to be able to search it. Headcleaner provides three ways to do that, and choosing the right one depends on what you are trying to accomplish.

The three ways are: a built-in CLI search that queries a local SQLite database, a local HTTP server that exposes the same search over a REST API, and an MCP server that exposes the same search to compatible AI coding assistants. All three share the same underlying database and the same search implementation, so results are consistent across the three surfaces. The difference is how you, or your tools, connect to headcleaner.

## What you are searching

Headcleaner does not search your original source files. It searches the cited chunks that the conversion produced. A chunk is a small piece of a converted document — typically a few paragraphs, a heading and its content, or a complete table or code block — that carries a citation back to the source it came from. Chunks live in `okf/chunks.jsonl` and are indexed into a local SQLite database at `<bundle>/.headcleaner/index.sqlite3`.

The reason chunks are the unit of search, rather than entire documents, is that you almost always want to find a specific passage, not a specific file. If you are looking for "the part of the Q3 report that talks about retention," you want to land on that paragraph with a citation back to the source, not on the entire Q3 report with the relevant paragraph buried somewhere inside.

## Building the search index

The search index is a derivative, so it is built from the canonical output and can be deleted and rebuilt at any time. To build it, run:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./my-folder.clean/okf
```

The command reads the chunks from `okf/chunks.jsonl`, validates them, builds a new SQLite database in a temporary file, runs an integrity check, and atomically replaces the previous database. If something goes wrong during the build, the previous index is preserved and headcleaner reports `INDEX_BUILD_FAILED`.

The build is fast for typical bundles — a few seconds for hundreds of chunks, longer for tens of thousands. If you change the conversion output (by editing a source file and re-running `headcleaner convert`), you can rebuild the index with `headcleaner index rebuild` to pick up the changes. There is also an `index update` command that does an incremental refresh; the difference is mostly performance on very large bundles.

## Querying the index from the CLI

The simplest way to search is from the command line:

```bash
uv run --no-sync --python 3.13 headcleaner search "retention" --bundle ./my-folder.clean
```

The `search` command takes a query string and an optional bundle path, and prints one line per result. Each line shows the source concept path and a short excerpt. For machine-readable output, add `--json`:

```bash
uv run --no-sync --python 3.13 headcleaner search "retention" --bundle ./my-folder.clean --json
```

The JSON output is a list of result objects, each with `chunk_id`, `concept_path`, `ordinal`, `rank`, `excerpt`, `citation`, `trust_state`, and `index_schema_version`. The `citation` field includes the source URI and SHA-256 hash, so every result is traceable back to its source.

You can filter the results with optional flags:

- `--tag` restricts results to chunks tagged with the given tag.
- `--type` restricts results to chunks belonging to concepts of the given type.
- `--status` restricts results by trust status.
- `--path` restricts results to concepts whose path starts with the given prefix.
- `--source-sha` restricts results to chunks from a specific source file.
- `--limit` controls how many results to return.

The filters compose, so you can ask for "tagged `legal`, type `Document`, status `unverified`, source SHA `aaa...`" and get back exactly that intersection.

## Querying the index over HTTP

If you want your tools to query the index over HTTP, headcleaner ships a small local server. Start it with:

```bash
uv run --no-sync --python 3.13 headcleaner serve --bundle ./my-folder.clean --host 127.0.0.1 --port 8765
```

The server binds to `127.0.0.1` by default, which means it only accepts connections from your own machine. Do not bind it to `0.0.0.0` unless you have explicitly configured authentication and authorization; the server is read-only and unauthenticated, and exposing it on a non-loopback interface would let anyone on your network read your converted output.

Once running, the server exposes `/api/search` and related endpoints. A simple request:

```bash
curl 'http://127.0.0.1:8765/api/search?q=retention&limit=10'
```

The HTTP API uses the same underlying search implementation as the CLI, with the same filters exposed as query parameters. The endpoint shapes are documented in the [Serve API reference](../reference/serve-api-reference.md).

## Querying the index through an MCP server

If you use a compatible AI coding assistant — Claude Code, Cursor, and others — you can connect headcleaner to it through the Model Context Protocol. The assistant can then ask headcleaner to search your converted output, retrieve a specific chunk by ID, or get diagnostics about a source file. The setup is described in detail in [Working with AI assistants](working-with-ai-agents.md) and the [MCP client setup](../integrations/mcp-client-setup.md).

The MCP server speaks the same search implementation as the CLI and HTTP server. The difference is that the assistant, not you, formulates the query and renders the results. This is convenient for tasks like "find me every reference to retention in the Q3 report and summarize them" because the assistant can chain multiple queries and read the citations itself.

## Filters and their semantics

The five filters (`--tag`, `--type`, `--status`, `--path`, `--source-sha`) all share one property: they intersect with each other and with the FTS5 query. This means a search with multiple filters returns only results that match all of them.

The filters do not interfere with the ranking. Results are still ranked by FTS5 `bm25` relevance, with a deterministic tie-break on `concept_path` and then `ordinal`. Two searches that return the same set of matching chunks will always return them in the same order, regardless of when you run them. This is the property that makes the search results reproducible across the CLI, the HTTP server, and the MCP server.

## When to use which surface

The three surfaces are not mutually exclusive. Most users do the following:

- Use the CLI search for ad-hoc queries during development. It is fast, requires no setup, and is easy to pipe into other shell tools.
- Use the HTTP server when they want a long-running process that their tools can connect to. The server is read-only and safe to leave running.
- Use the MCP server when they want an AI assistant to do the querying. The assistant handles the queries; you handle the prompt.

The underlying database is the same. You can switch between surfaces without rebuilding the index.

## What to read next

If you want to learn how to connect headcleaner to an AI coding assistant, read [Working with AI assistants](working-with-ai-agents.md). If you want a complete reference for the search command's options and exit codes, read the [CLI reference](../reference/cli-reference.md). If you want to understand how the chunks are produced and why they have the structure they do, read the [Chunking and indexing developer guide](../developer/chunking-and-indexing.md).