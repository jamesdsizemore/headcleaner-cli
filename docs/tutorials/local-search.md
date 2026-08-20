# Set up local search over your output

This tutorial takes you from a converted bundle to a searchable database and walks through the three surfaces headcleaner exposes for searching: the CLI, the local HTTP server, and the MCP server. The point of the lesson is to get comfortable moving between them, since they share the same underlying index.

## Outcome

You will have a searchable index, hands-on experience with the CLI and the HTTP server, and a working MCP connection you can use from a compatible AI coding assistant.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- A converted bundle. If you do not have one, run the [first-10-minutes tutorial](first-10-minutes.md) first.
- For the MCP section, a compatible AI coding assistant and the configuration template from the [MCP client setup](../integrations/mcp-client-setup.md) page.

## Step 1 — Build the index

You already did this in the first tutorial. If your bundle is fresh from the conversion step, run:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./my-folder.clean/okf
```

If the command prints a non-zero chunk count, the index is ready. The chunk count is the number of cited, searchable pieces in your bundle. For a folder with a few dozen mixed documents, you should see something between a few dozen and a few hundred chunks.

## Step 2 — Run CLI searches

Pick three phrases you know appear in your source files. For each, run a search and inspect the result:

```bash
uv run --no-sync --python 3.13 headcleaner search "phrase one" --bundle ./my-folder.clean
uv run --no-sync --python 3.13 headcleaner search "phrase two" --bundle ./my-folder.clean
uv run --no-sync --python 3.13 headcleaner search "phrase three" --bundle ./my-folder.clean
```

The first search that returns a result tells you two important things: the index is working, and the citation points back to the source file you expected. If a phrase you know is in a document returns no results, something is wrong with either the conversion (the body content was not extracted) or the chunking (the body content was chunked but the phrase landed in a chunk that did not get indexed). The [chunking and indexing developer guide](../developer/chunking-and-indexing.md) explains the chunking parameters.

## Step 3 — Add filters

Now narrow your search using filters. The five filters are `--tag`, `--type`, `--status`, `--path`, and `--source-sha`. Compose them to make your search specific:

```bash
uv run --no-sync --python 3.13 headcleaner search "phrase" --bundle ./my-folder.clean --type Document --status unverified
```

The filters intersect with the FTS5 query and with each other. The search returns only chunks whose concept matches the type filter, whose trust status matches the status filter, and whose text matches the query. This is how you answer questions like "show me every claim in unverified documents" without writing a custom query.

## Step 4 — Add the `--json` flag for structured output

When you want to consume results programmatically, add `--json`:

```bash
uv run --no-sync --python 3.13 headcleaner search "phrase" --bundle ./my-folder.clean --json > hits.json
```

The JSON output is a list of result objects with `chunk_id`, `concept_path`, `ordinal`, `rank`, `excerpt`, `citation`, `trust_state`, and `index_schema_version`. Each result is fully self-describing; you can pipe it to another tool without any extra parsing. The [result reference](../reference/result-reference.md) documents every field.

Open `hits.json` in your editor. Notice that the `citation` block includes both the source URI and the source SHA-256 hash. This is the property that lets you verify every result against its source file.

## Step 5 — Start the HTTP server

The HTTP server exposes the same search as the CLI, but as a REST endpoint. Start it in the background:

```bash
uv run --no-sync --python 3.13 headcleaner serve --bundle ./my-folder.clean --host 127.0.0.1 --port 8765
```

The command binds to `127.0.0.1`, which means it only accepts connections from your own machine. Do not bind it to `0.0.0.0`; the server is read-only and unauthenticated, and exposing it on a non-loopback interface would let anyone on your network read your converted output.

## Step 6 — Query the HTTP server

From another terminal, run:

```bash
curl 'http://127.0.0.1:8765/api/search?q=phrase&limit=10'
```

The response is the same JSON shape the CLI emits with `--json`. The HTTP API uses the same search implementation, the same filters (as query parameters), and the same deterministic ranking. You can use the CLI and the HTTP server interchangeably; the results will match.

If the connection is refused, the server is not running or is bound to a different host/port. Confirm with `curl 'http://127.0.0.1:8765/api/health'` — a healthy server returns a JSON object with a `status: ok` field.

## Step 7 — Connect an AI coding assistant

The MCP integration is what makes headcleaner useful inside an AI assistant's workflow. The setup is described in detail in the [MCP client setup](../integrations/mcp-client-setup.md) page; the short version is to add the following to your assistant's MCP configuration:

```json
{
  "mcpServers": {
    "headcleaner": {
      "command": "uv",
      "args": ["run", "--no-sync", "--python", "3.13", "headcleaner", "mcp"]
    }
  }
}
```

Once the assistant is connected, ask it to query your converted output:

```text
Find every reference to "Project Atlas" in the Q3 archive and summarize them with citations.
```

The assistant will issue one or more `okf_search` tool calls, read the cited responses, and produce an answer. The citations mean you can verify every claim the assistant makes by opening the source file at the path recorded in the citation block.

## Step 8 — Compare results across surfaces

Run the same query from all three surfaces and confirm the results are identical:

```bash
# CLI
uv run --no-sync --python 3.13 headcleaner search "phrase" --bundle ./my-folder.clean --json
# HTTP
curl 'http://127.0.0.1:8765/api/search?q=phrase&limit=20'
# MCP (through the assistant)
```

The three surfaces use the same underlying implementation. The result lists should be identical in ordering and content. If they are not, please open an issue with the three outputs side by side; this is the kind of inconsistency headcleaner's tests are designed to catch.

## What you have learned

You know how to build an index, search it from the CLI with filters and JSON output, query it over HTTP, and connect it to an AI assistant through MCP. You also know that the three surfaces are interchangeable and produce identical results.

## Where to go next

- [Working with AI assistants](../user-guide/working-with-ai-agents.md) — more on the MCP integration and what the assistant can do.
- [Search and context](../user-guide/search-and-context.md) — the conceptual background behind the search index.
- [MCP tool reference](../reference/mcp-tool-reference.md) — every tool the server exposes.