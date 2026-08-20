# MCP overview

The headcleaner MCP server exposes headcleaner's tools to any compatible AI coding assistant. The server speaks the Model Context Protocol over stdio, which is the local-only transport the standard defines. This page explains what the MCP integration gives you, how it differs from the HTTP server, and when to use it.

## What you get

When an AI coding assistant is connected to headcleaner through MCP, the assistant can:

- Search your converted output using the same FTS5 search the CLI uses.
- Retrieve specific chunks by ID with full citation information.
- Walk the knowledge graph from any starting node, with policy filtering applied.
- Compare two Markdown files or two bundles element-by-element.
- Assemble a small cited context package around a topic or chunk.
- Read the run manifest, report, diagnostics, claim candidates, and dedupe analysis.

The assistant can read all of this. It cannot modify any of it. The MCP server is read-only by design; no MCP tool writes to the bundle, the index, or any other state.

## Why local

The MCP integration uses stdio rather than a network protocol because headcleaner's purpose is to give the assistant access to your local documents without sending those documents anywhere. Stdio means the assistant starts headcleaner as a subprocess, talks to it over the subprocess's stdin and stdout, and tears the subprocess down when it is finished. Nothing leaves your machine unless the assistant itself decides to send something to its own model provider.

This is a deliberate design choice and not a limitation of the protocol. The MCP standard supports both stdio and HTTP transports; headcleaner uses stdio because the integration's purpose is local-first.

## Why three surfaces

Headcleaner exposes the same functionality through three surfaces: the CLI, the local HTTP server, and the MCP server. They use the same underlying implementation; the difference is who is driving.

- **CLI** is for you. You type a query, headcleaner answers. Good for ad-hoc exploration and CI scripting.
- **HTTP server** is for your tools. You start the server, your scripts connect over HTTP. Good for long-running local services and for any tool that prefers HTTP.
- **MCP server** is for your AI assistant. The assistant starts headcleaner when it needs a tool, talks over stdio, and tears it down. Good for any workflow that involves a coding assistant.

All three return the same JSON for the same query, with the same citation fields. Switching between them is a matter of how you want to consume the data.

## Where MCP fits in your workflow

The most common use of the MCP integration is "let my coding assistant search my converted output while I work." The assistant reads the citations, reasons about the content, and produces an answer that you can verify by opening the source files.

The integration is also useful for batch operations that the assistant can perform on your behalf. For example, "find every duplicate candidate in this bundle and tell me which ones look like the same record" — the assistant can run the dedupe tool, read the results, summarize them, and cite the underlying documents.

The integration is not a replacement for the CLI or the HTTP server. It is a third surface for the same underlying functionality, designed for the case where the consumer is an AI assistant.

## What to read next

The [MCP client setup guide](mcp-client-setup.md) has the configuration template and per-assistant notes. The [MCP tool reference](../reference/mcp-tool-reference.md) documents every tool the server exposes. The [tutorial on connecting to an AI coding assistant](../tutorials/ai-coding-assistant.md) walks through the setup step by step.