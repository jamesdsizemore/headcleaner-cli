# MCP client setup

This page explains how to connect a compatible AI coding assistant to headcleaner through the Model Context Protocol. The exact configuration depends on which assistant you use, but the underlying shape is the same.

This documentation deliberately avoids naming specific assistants with specific recipes. Assistant setup commands change frequently, and a recipe that worked last month may now be wrong. Instead, this page provides a generic stdio template that works with any MCP-compatible assistant, plus notes on what to look for in your assistant's own documentation.

## The generic template

The MCP configuration is a JSON object with one entry per server. The headcleaner server entry has three fields: a `command`, the `args` array, and an optional `name` (some clients use this as a display label).

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

The `command` is `uv`. The `args` tell `uv` to use the locked Python 3.13 environment without re-checking the lockfile and to invoke `headcleaner mcp`. This is the smallest correct invocation; do not add flags the assistant does not require.

Save this JSON in the file the assistant expects. Common locations include:

- A per-assistant config file in your home directory.
- A per-project config file in the repository where the assistant runs.
- A workspace-level config file the assistant manages itself.

Consult your assistant's documentation for the exact location.

## Why `uv run` and not `headcleaner` directly

Two reasons. First, `uv run` activates the locked Python environment, which is the only environment headcleaner is tested against. Running headcleaner against a different Python or a different set of dependencies may produce subtly different output. Second, `--no-sync` tells `uv` not to check the lockfile every time the assistant starts the server. The assistant may start the server many times per session; re-checking the lockfile each time would noticeably slow down every tool call.

## Confirming the connection

After saving the configuration, restart the assistant so it picks up the new MCP server. The assistant's UI typically shows a list of available tools when the connection is successful. You should see tools whose names start with `okf_`: `okf_search`, `okf_impact`, `okf_diff`, `okf_context`, and the rest documented in the [MCP tool reference](../reference/mcp-tool-reference.md).

If the tools do not appear, the connection failed. The most common reasons:

- The `command` or `args` in the configuration is wrong. Test the command directly from your shell: `uv run --no-sync --python 3.13 headcleaner mcp` should start the server and wait for input on stdin. If that works but the assistant cannot connect, the issue is the assistant's argument parsing, not headcleaner.
- The assistant is using a different Python than headcleaner expects. Confirm with `uv run --no-sync --python 3.13 headcleaner --version` from the same shell the assistant uses. If the assistant runs in a different shell environment, the path to `uv` may differ.
- The lockfile is out of date. Run `uv sync --locked --python 3.13` in the headcleaner folder before restarting the assistant.

## What to do once it is connected

The first thing to try is a simple query. Ask the assistant to find something in a folder you have converted. If the assistant can issue an `okf_search` call and read the cited response, the integration is working.

The [tutorial on connecting to an AI coding assistant](../tutorials/ai-coding-assistant.md) walks through the verification process in more detail. The [working with AI assistants](../user-guide/working-with-ai-agents.md) page is the conceptual background.

## Per-assistant notes

For specific assistants, the relevant things to look for in the assistant's documentation are:

- The exact location and name of the MCP configuration file. Some assistants use a global config; others use a per-project config; some support both.
- Whether the assistant expects a specific JSON shape for the server entry. Most assistants accept the generic template above, but a few require additional fields.
- How to restart the assistant or refresh its MCP connections. Most assistants pick up new MCP servers on restart, but a few support hot-reload.

If your assistant's documentation contradicts this page, follow the assistant's documentation. The generic template above is the fallback that always works.

## Security properties to remember

The MCP server is read-only. No tool modifies the bundle, the index, or any other state. The assistant can read your converted output; it cannot write to it. This is a deliberate property of the integration.

If you want the assistant to make changes — for example, to mark a converted file as reviewed — you do that out-of-band by editing the file in your editor. The assistant can suggest the change; it cannot perform it. The reason is that no programmatic interface can know whether you actually read the file; the human reviewer who marks the file is the one asserting "I read this and it is correct."

## Where to read next

The [MCP overview](mcp-overview.md) is the conceptual background. The [MCP tool reference](../reference/mcp-tool-reference.md) documents every tool. The [tutorial on connecting to an AI coding assistant](../tutorials/ai-coding-assistant.md) walks through the setup step by step.