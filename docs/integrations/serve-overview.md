# Serve overview

Headcleaner ships a small local HTTP server that exposes the search, chunk, and graph APIs over HTTP. The server is intended for local use and binds to `127.0.0.1` by default. This page explains when to use the HTTP server, what it gives you, and how to keep it safe.

## When to use the HTTP server

Use the HTTP server when you want a long-running local process that your other tools can connect to. The server is read-only and unauthenticated; it is designed to be started on your own machine and used by your own scripts.

The most common reasons to use the HTTP server:

- You have a long-running workflow that periodically polls headcleaner for new content. The HTTP server lets your poll loop connect over HTTP rather than invoking a CLI command each time.
- You are writing a small web-based viewer for your converted output and you want to query headcleaner from JavaScript. The HTTP server's `/api/search` endpoint is the easiest way to do this.
- You want to integrate headcleaner with a tool that prefers HTTP over a subprocess. Some tools have better HTTP support than subprocess support.

## What the server is not

The HTTP server is not a public service. It is not authenticated, it does not implement rate limiting, and it does not log access. It is designed to be started on `127.0.0.1` and consumed by tools running on the same machine.

If you bind the server to a non-loopback interface — for example, `0.0.0.0` to make it reachable from another machine on your network — anyone who can reach the port can read your converted output. There is no authentication layer that would prevent this. Do not bind to a non-loopback interface without first adding authentication and authorization at the network layer (a reverse proxy with basic auth, a VPN, or similar).

## Starting the server

The basic command is:

```bash
uv run --no-sync --python 3.13 headcleaner serve --bundle BUNDLE --host HOST --port PORT
```

`BUNDLE` is the OKF bundle directory. `HOST` is the bind host; the default is `127.0.0.1` and that is the right choice for almost every use case. `PORT` is the bind port; the default is `8765` and you can change it to any port that is not in use.

The server runs until interrupted. Send SIGINT (Ctrl+C) to stop it.

## Endpoints

The server exposes a small set of endpoints documented in the [Serve API reference](../reference/serve-api-reference.md). The most useful ones are:

- `/api/health` — confirms the server is alive and reports its version.
- `/api/search` — the same search the CLI uses, with the same filters.
- `/api/chunks` — list chunks for the bundle.
- `/api/concept/{concept_id}` — get the full content of a single concept.
- `/api/graph` — get the knowledge graph.
- `/api/manifest` and `/api/report` — get the run manifest and report.
- `/api/claims` and `/api/dedupe` — get the claim and dedupe analyses.

All endpoints return JSON. Errors return a structured envelope with a stable `code` field that you can switch on programmatically.

## A small example

The simplest use of the server is a curl-based search:

```bash
curl 'http://127.0.0.1:8765/api/search?q=Project+Atlas&limit=10'
```

The response is a JSON object with a `hits` array, each hit carrying the chunk ID, concept path, ordinal, rank, excerpt, citation, and trust state. The `citation` block is the source URI and SHA-256 hash; you can use it to verify the result by opening the source file at the recorded path and checking the hash.

## Health checks

The `/api/health` endpoint is designed for monitoring. A healthy server returns `status: ok` with a non-empty `version` field. A server that has lost access to its bundle returns `status: error` with a `code` of `BUNDLE_NOT_FOUND`. Wire your monitoring to fail on any non-`ok` response.

## Where to read next

The [Serve API reference](../reference/serve-api-reference.md) is the complete reference. The [tutorial on local search](../tutorials/local-search.md) walks through using the server alongside the CLI and MCP surfaces. The [configuration reference](../reference/configuration-reference.md) documents the policy file you can pass to exclude graph edge kinds.