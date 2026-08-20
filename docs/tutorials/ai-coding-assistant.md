# Connect headcleaner to an AI coding assistant

This tutorial walks through connecting headcleaner to a compatible AI coding assistant through the Model Context Protocol. Once connected, the assistant can search your converted output, retrieve cited chunks, and reason about your documents without you having to copy-paste content into the chat.

## Outcome

You will have a working MCP connection between headcleaner and your chosen AI assistant, with at least one verified example of the assistant querying your converted output and producing a cited answer.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- A converted bundle and a built search index. The [first-10-minutes tutorial](first-10-minutes.md) and the [local-search tutorial](local-search.md) cover both steps.
- A compatible AI coding assistant. The MCP standard is supported by a growing list of assistants; check your assistant's documentation if you are not sure whether it supports MCP.

## Step 1 — Understand the connection

The connection works over stdio. The assistant starts headcleaner as a subprocess when it needs to call a tool, speaks the MCP protocol over the subprocess's stdin and stdout, and tears the subprocess down when it is finished. There is no TCP socket, no remote server, and no network call. Everything stays on your machine.

This is a security property, not just a convenience. Because headcleaner is a subprocess under your assistant's control, the assistant can call headcleaner's tools but headcleaner cannot call back. The connection is one-way: the assistant asks, headcleaner answers.

## Step 2 — Configure the assistant

The exact configuration depends on which assistant you use. The pattern, however, is always the same: tell the assistant the path to `uv`, the arguments to pass, and a name for the server.

The generic template, which works with most MCP-compatible assistants, looks like this:

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

The arguments matter. `--no-sync` prevents `uv` from checking the lockfile every time the assistant starts the server, which would slow down every tool call. `--python 3.13` ensures the right Python version is used regardless of what the assistant's default Python is.

If your assistant expects a per-server configuration file rather than a single global one, place the JSON above in the file the assistant expects. The [MCP client setup](../integrations/mcp-client-setup.md) page has the exact paths and formats for the most common assistants.

## Step 3 — Restart the assistant

After changing the configuration, restart the assistant so it picks up the new MCP server. The exact mechanism depends on the assistant; some require a full restart, others only a session refresh. The assistant's documentation will tell you which.

When the assistant starts, it should connect to the headcleaner MCP server automatically. The assistant's UI typically shows a list of available tools; you should see tools named `okf_search`, `okf_impact`, `okf_diff`, `okf_context`, and others. The full list is in the [MCP tool reference](../reference/mcp-tool-reference.md).

If the assistant does not show the tools, the connection failed. The most common reasons are:

- The `command` or `args` in the configuration is wrong. Test the command directly: `uv run --no-sync --python 3.13 headcleaner mcp` should start the MCP server and wait for input.
- The assistant is using a different Python than the one headcleaner expects. Confirm with `uv run --no-sync --python 3.13 headcleaner --version` from the same shell the assistant uses.
- The lockfile is out of date. Run `uv sync --locked --python 3.13` in the headcleaner folder.

## Step 4 — Try a simple query

Once the assistant is connected, give it a task that exercises the search index:

```text
Find every mention of "Project Atlas" in the Q3 archive. For each match, tell me the source file and the section heading it appears under.
```

The assistant will issue one or more `okf_search` tool calls and read the cited responses. It should produce an answer that lists each match with a citation. Verify one of the citations by opening the source file at the path the assistant reported and confirming the phrase appears where the citation says it does.

If the assistant produces an answer without citations, something is wrong. Headcleaner's tools always include citations; an answer without them means the assistant is either summarizing or hallucinating. Ask the assistant to "show me the tool calls you used" and confirm the citations in the tool responses.

## Step 5 — Try a multi-step query

Once a simple query works, try one that exercises multiple tools:

```text
For every document in the archive that mentions "Project Atlas", show me the graph neighborhood of that document up to depth 2, restricted to citation edges.
```

The assistant will first run an `okf_search` to find the documents, then run `okf_graph` for each one to fetch the graph neighborhood. The combined answer should include both the document list and the graph neighbors, all with citations.

If the assistant struggles with this kind of multi-step query, the issue is usually that the assistant's context window is too small for the combined response. The MCP server returns full citations for every chunk; if you have a very large archive, the per-chunk citations can add up. The [configuration reference](../reference/configuration-reference.md) documents the limits you can adjust.

## Step 6 — Use a context package

The most powerful tool the MCP server exposes is `okf_context`, which assembles a small cited context package around a topic or a chunk ID. Try:

```text
Build a context package around "loan amortization" with a 50KB byte budget.
```

The assistant will issue an `okf_context` call and receive back a Markdown or JSONL package that contains the most relevant cited chunks, ordered deterministically by score and concept path, up to the byte budget. The assistant can then use the package as input to its own reasoning.

The context package includes both the included chunks and the omitted chunks with their reasons. The omitted chunks are not silently dropped; they are reported so you can see what was left out and why.

## Step 7 — Confirm the safety properties

The MCP server is read-only. To confirm this, ask the assistant to do something it cannot do:

```text
Mark notes.docx as reviewed and change the verified field to human:reviewed.
```

The assistant will not be able to perform this action through headcleaner, because headcleaner does not expose a write tool over MCP. The assistant may suggest you perform the action manually by editing the file; that is the intended workflow. The safety property is that no MCP tool can silently modify your canonical output.

## What you have learned

You know how to configure a generic MCP client, confirm the connection, run simple and multi-step queries, and use the context package tool. You also know that the integration is read-only and that any modifications to canonical output happen out-of-band.

## Where to go next

- [Working with AI assistants](../user-guide/working-with-ai-agents.md) — the conceptual background.
- [MCP client setup](../integrations/mcp-client-setup.md) — per-assistant configuration recipes.
- [MCP tool reference](../reference/mcp-tool-reference.md) — every tool the server exposes.