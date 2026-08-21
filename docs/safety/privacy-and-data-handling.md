# Privacy and data handling

This page documents what headcleaner does with the data you give it. The short answer: by default, nothing leaves your machine. The longer answer covers the specific cases where data does leave, what triggers each case, and how to audit it.

## The default: local only

A headcleaner run that does not pass any network-related flag performs no network calls. The conversion reads from your input folder, processes the data locally, and writes to your output folder. The search index lives in a local SQLite database. The knowledge graph, the dedupe analysis, and the claims analysis are all computed locally.

The only data that ever leaves your machine in the default configuration is the standard telemetry that your operating system or package manager may collect from `uv` itself. Headcleaner does not add to that.

## When data leaves your machine

There are exactly four situations in which headcleaner sends data off your machine. Each one requires explicit configuration.

### HTTP embedding provider

When you pass `--provider openai_compatible_http --endpoint URL --model MODEL --allow-network`, headcleaner sends each chunk's text to the configured endpoint to compute an embedding. The endpoint receives the text of every chunk in the corpus.

Mitigations:

- Pass `--provider local_sentence_transformer` to keep embedding local.
- Run `headcleaner redact BUNDLE` to inspect deterministic secret proposals
  locally. Add `--write-derivative` only when you explicitly want a separate
  `_redacted/` bundle; the canonical bundle stays unchanged. Review the proposal
  before embedding: redaction does not mark content reviewed or verified, and
  you should still avoid sending content you would not disclose to the endpoint.
- Audit the requests with a local HTTP proxy. The provider respects standard `HTTP_PROXY` and `HTTPS_PROXY` variables; pointing those at a logging proxy lets you see every request.

### Qdrant remote vector database

When you pass `--qdrant-endpoint URL --qdrant-collection NAME --allow-network`, headcleaner uploads the computed embeddings to the configured Qdrant collection. Each vector is sent with citation-safe metadata: the chunk ID, the model ID, and the dimension. The vector itself is the embedding; no chunk text is included in the payload.

Mitigations:

- Do not pass `--qdrant-endpoint` if you do not want remote uploads.
- Use a local Qdrant instance for development; the same `--qdrant-endpoint` flag points at localhost.

### MCP server

The headcleaner MCP server speaks stdio. It does not make network calls. The client (your AI coding assistant) may make its own network calls as part of its own operation, but those are the assistant's calls, not headcleaner's.

Mitigations:

- The MCP integration is local by design. If your assistant is configured to make network calls, that is the assistant's configuration, not headcleaner's.

### HTTP serve

The headcleaner HTTP server binds to `127.0.0.1` by default and accepts no external connections. If you bind to a non-loopback interface, anyone who can reach the port can read your converted output.

Mitigations:

- Bind only to `127.0.0.1`. Do not bind to `0.0.0.0` or to a public IP without adding authentication and authorization at the network layer.

## What headcleaner logs

Headcleaner emits three kinds of output:

- **Human-readable progress lines** on stdout. These include file paths and engine names. They do not include file contents.
- **Structured JSON events** on stdout when `--json` is passed. These include file paths, source hashes, and engine names. They do not include file contents.
- **Warnings and errors** on stderr. These include diagnostic codes and human-readable messages. They do not include file contents.

Headcleaner never logs the body content of any document, the text of any chunk, or the contents of any embedding vector. If you find a code path that does, please open an issue; this is a security property, not a nice-to-have.

## Audit trail

Every headcleaner run produces a manifest. The manifest is the audit trail. It records:

- When the run started and finished.
- What command was run and with what flags.
- Which files were processed and which were skipped.
- Which engine handled each file.
- What the source SHA-256 hash was for each file.
- What the duration was for each file.
- What diagnostics were emitted.

The manifest is the answer to "what did headcleaner do the last time it ran on this folder?" Keep it. Diff it between runs. Upload it to CI. It is the source of truth for what happened.

## Data minimization

Headcleaner's design follows a data minimization principle: every piece of data it persists is either required for the canonical output, required for a rebuildable derivative, or required for an audit trail. There is no telemetry, no analytics, no "phone-home," and no usage tracking.

If you find a place where headcleaner persists data that is not justified by one of these three categories, please open an issue.

## Where to read next

The [safety overview](safety-overview.md) is the single-page summary of the safety guarantees. The [permissions page](permissions.md) documents every flag that affects data leaving your machine. The [security model page](security-model.md) is the formal threat model.