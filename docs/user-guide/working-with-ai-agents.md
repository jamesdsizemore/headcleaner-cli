# Working with AI assistants

Headcleaner can talk to compatible AI coding assistants through the Model Context Protocol, which is a standard way for an assistant to call tools on your local machine. The setup is small and the value is large: once connected, the assistant can search your converted output, retrieve cited chunks, and reason about your documents without ever uploading them to a remote service.

This page introduces MCP without protocol jargon, walks through the connection setup, and gives you a few example prompts you can use once the assistant is connected.

## What MCP gives you in plain terms

A coding assistant that supports MCP can ask headcleaner questions while it works. Instead of you copy-pasting search results into the assistant, the assistant issues the query itself, reads the response (including the citations), and uses what it found. The assistant sees the same chunks you would see if you ran the search yourself; the difference is who is at the keyboard.

The protocol is local. The assistant speaks to headcleaner over stdin and stdout, or over a small local socket. Headcleaner does not connect to a remote service on your behalf; nothing about your documents leaves your machine unless the assistant itself decides to send something to its own model provider. The connection between the assistant and headcleaner is one tool call away from "type a question into your terminal."

## Which assistants work

The MCP standard is supported by a growing list of coding assistants. Headcleaner exposes the standard `headcleaner mcp` subcommand, which starts the MCP server over stdio. Any MCP-compatible client can connect to it.

This documentation deliberately does not name specific assistants with specific setup recipes. The reason is that assistant setup commands change frequently, and a recipe that worked last month may now be wrong. Instead, the [MCP client setup](../integrations/mcp-client-setup.md) page provides a generic stdio template you can adapt to whichever assistant you use. The template is the same shape regardless of which assistant you connect.

If you want to know whether your specific assistant supports MCP, check that assistant's own documentation. The MCP standard itself is the constant; the client integrations around it change.

## Connecting headcleaner

The headcleaner MCP server is `headcleaner mcp`. You start it with the same `uv run` invocation pattern you use for everything else:

```bash
uv run --no-sync --python 3.13 headcleaner mcp
```

When started directly, the command speaks MCP over stdio. Most MCP clients expect this exact pattern. The client configuration typically looks like:

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

The `uv` invocation ensures the right Python environment is used and that the lockfile-resolved dependency set is honored. The `--no-sync` flag prevents `uv` from trying to update the environment when the MCP server starts; that is important because MCP servers may be started frequently and you do not want each start to re-check the lockfile.

If you would rather not depend on `uv` for the MCP server, you can run `headcleaner mcp` from inside an already-activated virtual environment. The trade-off is that you need to make sure the right environment is active wherever the client starts the server.

## What the assistant can do once it is connected

The MCP server exposes headcleaner's tools under names that begin with `okf_`. The complete list is documented in the [MCP tool reference](../reference/mcp-tool-reference.md). The tools the assistant will reach for most often are:

- `okf_search`, which lets the assistant query the local search index with the same parameters as the CLI `search` command. The assistant can ask for chunks matching a phrase, filter by tag, type, status, path, or source SHA, and get back cited results.
- `okf_impact`, which lets the assistant explore the knowledge graph starting from a node. The assistant can walk the graph outward to a given depth, optionally filtered to a specific edge kind.
- `okf_diff`, which lets the assistant compare two Markdown files or two bundles element-by-element. This is useful when the assistant is reasoning about what changed between two versions of a document.
- `okf_context`, which lets the assistant assemble a small cited context package around a topic or a chunk ID, suitable for use as input to the assistant's own model.

The assistant can also ask headcleaner for the manifest of a bundle, the report of a run, and the schema versions of the various derivatives. The point of the integration is that the assistant has the same view of your documents that you do, without you having to copy-paste content into the chat.

## Example prompts

Once the assistant is connected, prompts that exercise the integration look like this:

- "Find every reference to retention in the Q3 report and summarize them with citations."
- "What documents in this bundle are duplicate candidates of each other?"
- "Compare the current version of `notes.docx.md` against the version from last week and tell me what changed."
- "Show me the graph neighbors of the topic `Q3 retention` and the chunk evidence behind each edge."
- "Build a context package around `loan amortization` with a 50KB byte budget."

For each of these, the assistant issues one or more `okf_*` tool calls, reads the cited responses, and produces an answer. The citations mean that whatever the assistant tells you, you can verify by opening the source file at the path recorded in the citation block.

## Safety: what the assistant cannot do

The MCP server is read-only. It does not expose any tool that modifies your source files, your canonical output, or your derivatives. The assistant can search, read, and assemble context; it cannot write.

If you want the assistant to make changes — for example, to mark a converted file as reviewed — you do that out-of-band by editing the file in your editor and committing the change. The assistant can suggest the change; it cannot perform it. This is the same safety guarantee that applies to headcleaner itself, and it is the reason the integration is safe to give to a coding assistant.

## What to read next

The [MCP client setup](../integrations/mcp-client-setup.md) page has a generic stdio template you can adapt to any compatible assistant. The [MCP tool reference](../reference/mcp-tool-reference.md) documents every tool the server exposes, including parameter shapes and return types. If you want to understand how the underlying search and graph are implemented, the [Chunking and indexing developer guide](../developer/chunking-and-indexing.md) and the [Graph development developer guide](../developer/graph-development.md) cover the contracts.