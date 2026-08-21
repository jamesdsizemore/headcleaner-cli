# The everyday workflow

This page is the practical story of how headcleaner fits into the work you actually do. It is not a complete reference — that lives in the [CLI reference](../reference/cli-reference.md) — but a guided walk through the moments when headcleaner pays off the most.

The four moments we will cover are: before you open a pull request, after you finish a session with an AI coding assistant, when you introduce headcleaner into a continuous integration pipeline, and when you are cleaning up an old project. Each moment has the same shape: a copy-paste command, a description of what headcleaner will do, an explanation of what a healthy result looks like, and a "what to do next" pointer.

## Before opening a pull request

You have finished a feature. Before you open the pull request, you want a clean conversion of the documents you touched, and you want the search index and graph to reflect the new content so reviewers and downstream tools see the latest state.

The minimal command sequence is:

```bash
uv run --no-sync --python 3.13 headcleaner convert ./documents ./documents.clean
uv run --no-sync --python 3.13 headcleaner index rebuild ./documents.clean/okf
```

The first command converts every supported document in `./documents` and writes the canonical output to `./documents.clean`. The second command rebuilds the local SQLite search index from the cited chunks the conversion produced.

What a healthy result looks like:

- The `convert` command finishes with one line per file plus a summary line that shows the count of `ok`, `skipped`, and `failed` files. A run that ends with zero `failed` and any number of `ok` (including zero, if the input folder was empty) is healthy.
- The `index rebuild` command prints the path to the rebuilt `index.sqlite3` and the count of chunks it indexed. A non-zero chunk count is the expected result for any folder that contained documents with body content.

What to do next:

- If you want to spot-check the conversion, open `./documents.clean/REPORT.md` and read the per-engine breakdown.
- If you want to verify the citations point to the right sources, run `headcleaner search` against the rebuilt index and pick a result — the citation block on the result shows the source URI and SHA-256 hash.
- If a file is in `failed` status, the [troubleshooting guide](troubleshooting.md) explains the most common reasons.

## After an AI coding session

You have spent the afternoon working with an AI coding assistant. The assistant may have created new documents, modified existing ones, or referenced sources it could not directly read. You want a clean conversion that captures the current state and an updated search index.

The shape of this moment is the same as the pre-PR moment, with one addition: you want headcleaner to tell you what changed since the last run, not just re-process everything.

```bash
uv run --no-sync --python 3.13 headcleaner convert ./documents ./documents.clean --no-cache
uv run --no-sync --python 3.13 headcleaner sync ./documents ./documents.clean --dry-run --json
```

The `--no-cache` flag forces headcleaner to re-extract every file rather than reusing cached results from a previous run. This is appropriate when the assistant may have rewritten files in place; the cached content might no longer match the file bytes.

The `sync --dry-run` command compares the current source files against headcleaner's sync state and reports what would change if you applied an update — without actually applying anything. Reading the JSON output tells you which files are unchanged, which are renamed, and which are deletion candidates.

What a healthy result looks like:

- The `convert --no-cache` run produces the same count of `ok` results as a non-cached run, and the byte-level output for files that did not change is identical to the previous run.
- The `sync --dry-run` plan lists `unchanged` for files that did not move and have the same source hash, `renamed` for files whose content matches a previous source at a different path, and `deleted_candidate` for files that the previous run knew about but that no longer exist.

What to do next:

- If the sync plan looks right, run `headcleaner sync ./documents ./documents.clean --apply` to update the durable sync state. The `--apply` flag is mandatory for any write; headcleaner will not silently modify your output.
- If you want to drop generated output that no longer corresponds to any source — for example, files the assistant created and then deleted — add `--prune-generated` to the apply command. The prune step will not touch any generated file whose current content does not match the recorded hash, so user edits are preserved.

## Introducing continuous integration

You want headcleaner to run automatically on every push or pull request so reviewers do not have to remember to run it. The minimal CI story is: a single job that runs `convert` plus `index rebuild`, fails the build on any `failed` file, and uploads the manifest as an artifact for debugging.

The reference workflow is described in detail in the [CI overview](../integrations/ci-overview.md), but the short version is:

```yaml
- name: Convert documents
  run: uv run --no-sync --python 3.13 headcleaner convert ./documents ./out --json > events.jsonl
- name: Rebuild search index
  run: uv run --no-sync --python 3.13 headcleaner index rebuild ./out/okf
- name: Upload artifacts
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: headcleaner-output
    path: |
      out/REPORT.md
      out/manifest.json
      events.jsonl
```

What a healthy CI run looks like:

- The `convert` step exits with code zero, writes one JSON event per file to `events.jsonl`, and ends with a summary event whose `event` field is `finish`.
- The `index rebuild` step exits with code zero and prints a non-empty chunk count if the bundle contained chunks.

What to do next:

- If you want headcleaner to fail CI when policy rules are violated, add `headcleaner policy test ./out --pack my-pack` and let the policy exit codes drive the CI step.
- If you want headcleaner to also produce a search index for downstream tools, the `index rebuild` step does it; the index file is small and rebuildable, so storing it in CI is optional.
- For detailed GitHub Actions walkthrough, see the [GitHub Actions integration](../integrations/ci-overview.md).

## Cleaning up an old project

You have inherited a folder of mixed documents — old reports, scans of paper records, exported email threads — and you want a clean, searchable archive. The shape of this moment is the longest, because you usually want all four of the user-facing capabilities: conversion, search, graph, and dedupe.

The recommended sequence is:

```bash
uv run --no-sync --python 3.13 headcleaner doctor
uv run --no-sync --python 3.13 headcleaner convert ./archive ./archive.clean --format both
uv run --no-sync --python 3.13 headcleaner index rebuild ./archive.clean/okf
uv run --no-sync --python 3.13 headcleaner graph ./archive.clean/okf --json > graph.json
uv run --no-sync --python 3.13 headcleaner dedupe ./archive.clean/okf --threshold 0.85 --json > dedupe.json
```

The `doctor` step confirms your environment has the optional tools you need (OfficeCLI for Office files, Tesseract for scans, and so on). The `convert` step produces the canonical output. The `index rebuild` step makes the content searchable. The `graph` step builds a knowledge graph and writes it to `graph.jsonl` inside the bundle; piping it to `graph.json` is optional and just lets you keep a copy outside the bundle. The `dedupe` step finds exact and near-duplicate documents and emits a candidate list.

What a healthy run looks like:

- The `doctor` step prints `GO`.
- The `convert` step's per-engine breakdown shows mostly `ok`, with `skipped` only for files whose format has no installed engine.
- The `index rebuild` step prints a chunk count proportional to the amount of body content.
- The `graph` step prints a non-zero node count and edge count.
- The `dedupe` step prints a `families` count and an empty or non-empty `candidates` list, depending on whether any near-duplicates were found.

What to do next:

- Open `./archive.clean/REPORT.md` to see the per-engine breakdown. If many files are in `skipped`, that is your signal to install an optional tool and re-run.
- Open `./archive.clean/okf/index.md` to see the auto-generated directory index.
- Run `headcleaner search` to spot-check the rebuilt index. Try a phrase you know appears in one of your documents.
- Review the dedupe output as a candidate list. Headcleaner does not delete or merge anything; it just reports. If two documents look like the same record, you decide what to do.

## The single thing to remember

If you remember nothing else from this page, remember this: **headcleaner does not touch your source files.** Every command above writes to a directory you name; nothing in your source folder is modified. The output is rebuildable, so you can experiment freely — delete the search index, delete the graph, delete the dedupe report — and rerun the appropriate command to regenerate them.

That property is the foundation of every workflow described above. It is also the foundation of the safety model documented in the [Safety overview](../safety/safety-overview.md). When you trust that headcleaner will not silently modify your world, you can use it confidently in the moments that matter.

## Where Phase 3 fits

After `convert` and before `review`, run `headcleaner readiness BUNDLE` and `headcleaner review-queue BUNDLE --json` to see what is gated and what is queued for human review. After `review`, run `headcleaner attest BUNDLE --in-toto PATH` to produce a deterministic in-toto Statement you can hand to a downstream system. None of these commands change `verified:` — that still happens only through `headcleaner review`.