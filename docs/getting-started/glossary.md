# Glossary

This page is the dictionary of terms headcleaner uses. Every word on this page is one you will see in the rest of the documentation or in headcleaner's own output. The definitions are written in plain English first; technical precision is added where it matters for safety or reproducibility.

## adapter

An **adapter** is the piece of headcleaner that knows how to read one specific file format. There is an adapter for Word, one for Excel, one for PDF, one for HTML, and so on. When you run `headcleaner convert`, headcleaner picks the right adapter for each file based on the file's extension. You do not pick the adapter directly; headcleaner does. If you want to influence which adapter handles a file, see the [routing and fallback developer guide](../developer/routing-and-fallback.md).

## bundle

A **bundle** is the output of a headcleaner run: the directory containing `_md/`, `okf/`, `manifest.json`, and `REPORT.md`. "Bundle" is a useful noun when you want to refer to the whole output as a unit rather than naming the directory.

## citation

A **citation** in headcleaner is the information that ties a piece of generated content back to the source it came from. The citation always includes the source file's URI (its location on disk) and the source file's SHA-256 hash (a unique fingerprint of its bytes). Some citations also include a page number or character span when the source format supports it. Citations are emitted into the YAML frontmatter of every converted file and into every chunk, search hit, and graph edge.

The reason citations exist is that headcleaner's output is only useful if you can always answer "where did this come from?" without guessing. The citation is how you answer that question deterministically.

## chunk

A **chunk** is a small piece of a converted document that headcleaner emits for search and retrieval. A chunk is typically a few paragraphs, a heading and its associated content, or a complete table or code block. Chunks are written to `chunks.jsonl` next to the OKF bundle and are what gets indexed when you run `headcleaner index rebuild`.

Chunks carry citations, which means a search hit always points back to a source file and a span inside that file. See the [chunking and indexing developer guide](../developer/chunking-and-indexing.md) for the algorithm and the data model.

## derived, derivative

A **derivative** in headcleaner is any artifact that is produced from the canonical output but is not itself the canonical output. The OKF bundle, the `_md/` Markdown, the chunks, the search index, the knowledge graph, the duplicate-family report, the claim-review report, and the sync state are all derivatives.

The important property of derivatives is that they can always be rebuilt from the canonical output. If you delete your search index, you can rebuild it with `headcleaner index rebuild` without losing any source data. If you delete your graph, you can rebuild it with `headcleaner graph` (or by re-running the conversion that produces it). This is why headcleaner's local search and graph are safe to experiment with — the worst case is you delete a derivative and rebuild it.

## embedding

An **embedding** is a way of representing a piece of text as a list of numbers, designed so that similar texts have similar number-lists. Headcleaner can compute embeddings for chunks using a local model from the Sentence Transformers library or an HTTP-based embedding provider. Embeddings are stored locally in a versioned cache and can optionally be uploaded to a remote vector database like Qdrant.

Embeddings are what power **semantic search**: searching by meaning rather than by keyword. If you search for "loan repayment terms" and find a paragraph that says "monthly amortization schedule," that is semantic search finding a match that keyword search would have missed.

Embeddings are never computed by default. You have to opt in by running `headcleaner index embed` and selecting a provider. See the [embeddings and vectors developer guide](../developer/embeddings-and-vectors.md) for the configuration steps.

## FTS5

**FTS5** is the name of the full-text search engine built into SQLite, the database format headcleaner uses for local search. "FTS5" stands for "Full-Text Search version 5." When headcleaner builds a search index, it creates a SQLite database with an FTS5 virtual table that lets you query the chunks by keyword with deterministic ranking. The whole database lives in `<bundle>/.headcleaner/index.sqlite3`.

## frontmatter

**Frontmatter** is the block of YAML at the top of every converted Markdown and OKF file. It is the structured part of the file that headcleaner controls: source URI, source hash, generation date, trust state, status, tags. The body of the file is the readable Markdown; the frontmatter is the machine-readable metadata.

In the OKF bundle, frontmatter uses OKF v0.2 vocabulary and includes the trust family fields. In the `_md/` output, frontmatter uses a small subset of OKF vocabulary plus headcleaner-specific fields. The OKF vocabulary notes are preserved at [`docs/_archive/legacy-docs/OKF_NOTES.md`](../_archive/legacy-docs/OKF_NOTES.md).

## graph

A **graph** in headcleaner is a representation of how your documents relate to each other. Nodes in the graph are documents, chunks, entities (named things mentioned in your documents), and topics (headings). Edges are relationships: containment (a document contains a chunk), citation (a chunk cites a source), mention (a chunk mentions an entity or topic), and a few candidate kinds (related-to, duplicate-candidate, conflict-candidate) that headcleaner suggests but never asserts as fact.

The graph lives in `okf/graph.jsonl` and is rebuildable. See the [graph development developer guide](../developer/graph-development.md) for the data model.

## human:pending, human:reviewed

`human:pending` and `human:reviewed` are the two trust states headcleaner uses. Every auto-converted file starts in `human:pending`, which means "a machine produced this and no human has checked it." Changing the state to `human:reviewed` requires an explicit human action; headcleaner will never silently promote a file.

This is the safety guarantee at the heart of headcleaner. Auto-conversion is not review. If you feed headcleaner output to a downstream tool that requires human review (a regulatory archive, a publication pipeline, a legal hold), you must run the explicit review step yourself.

## index

The **index** is headcleaner's local search database. It lives at `<bundle>/.headcleaner/index.sqlite3` and contains the chunks from every converted document plus their tags, source hashes, and trust states. You build it with `headcleaner index rebuild` and you query it with `headcleaner search`. The index is a derivative — it can always be deleted and rebuilt from the canonical output.

## MCP

**MCP** stands for Model Context Protocol. It is a standard for letting AI coding assistants call tools on your local machine. Headcleaner ships an MCP server that exposes its tools to any MCP-compatible client (Claude Code, Cursor, and others). When you connect headcleaner to a coding assistant through MCP, the assistant can ask headcleaner to convert files, search the index, or read citations on your behalf.

The MCP server is local-only by default. It speaks to the client over stdin and stdout and never makes a network connection. See the [MCP client setup guide](../integrations/mcp-client-setup.md).

## OKF

**OKF** stands for Open Knowledge Format. It is a portable Markdown-plus-frontmatter format for knowledge artifacts. OKF v0.2 is the version headcleaner emits. An OKF bundle is one `index.md` plus one concept file per source, all in a directory. The format is designed so a knowledge-management tool that understands OKF can ingest a headcleaner output without knowing anything about headcleaner specifically.

## pipeline

The **pipeline** is the sequence of stages headcleaner runs to convert a folder: walk the folder to find source files, route each file to an adapter, normalize the adapter output into a canonical document, emit the canonical document as Markdown and OKF, and then emit derivatives (chunks, graph, dedupe report, claims report, sync state). The pipeline is described in detail in the [architecture developer guide](../developer/architecture.md).

## stale_after

`stale_after` is the date after which a converted file should be considered stale. Headcleaner sets this to 180 days after the conversion by default. The reason a freshness window exists is that source documents change, engines improve, and downstream readers deserve a signal that says "this might be out of date." When a document passes its `stale_after` date, the [claims](../developer/claims-and-policy.md) module emits a stale finding against it.

## sync state

**Sync state** is the record headcleaner keeps of every source-to-output mapping it knows about. It lives at `<bundle>/.headcleaner/sync.json`. When you re-run a conversion, headcleaner uses the sync state to detect renames, deletions, and unchanged files without re-doing work that does not need re-doing. The sync state is the foundation of the rename/deletion-safe sync workflow described in the [sync and watch developer guide](../developer/sync-and-watch.md).

## trust family

The **trust family** is the set of frontmatter fields that together describe how trustworthy a piece of output is. In OKF v0.2 the trust family includes `type`, `status`, `generated`, `verified`, `stale_after`, and `sources`. Together they answer "what is this, who made it, has a human checked it, is it still fresh, and where did it come from?" Headcleaner emits the full trust family on every file it produces.

## version

**Version** in headcleaner usually refers to one of three things:

- The **headcleaner version**, printed by `headcleaner --version`. This is the version of the CLI itself.
- The **schema version** of a derivative. Every derivative records its schema version so downstream tools know how to read it. The current OKF bundle schema is `1`; the chunk schema is `1`; the graph schema is `1`.
- The **algorithm version** of a derivative computation. The dedupe algorithm reports its version as `1`; the graph builder reports `1`. If the algorithm changes in a future release, the version increments and downstream tools can tell the new output apart from the old.