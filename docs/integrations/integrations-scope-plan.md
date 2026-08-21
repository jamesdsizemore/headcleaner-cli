# Integration Scope Plan

> **Status:** Research deliverable — not yet an implementation phase.
> **Author:** automated scope pass over 21 candidate repositories.
> **Audience:** the maintainer, to choose what enters the next implementation phase.
> **Source of truth:** `docs/integrations/research/` (per-repo `.meta.json`, `.readme.md`, `.tree.txt`).

This document reviews 21 third-party repositories as potential integrations for
`headcleaner` (the local-first document → Markdown/OKF v0.2 converter described in
[`../../README.md`](../../README.md) and [`../../AGENTS.md`](../../AGENTS.md)).

Each repo was verified by `gh repo view` (metadata), `gh api repos/<owner>/<name>/readme`
(full README), and `gh api repos/<owner>/<name>/contents` (top-level tree). Raw
artifacts live in `docs/integrations/research/` next to this document.

The scope pass produces:

1. A **scoring rubric** (5 axes, 0–5 each, 25 max) tuned to headcleaner's purpose.
2. **Ranked tiers** with one-line verdicts.
3. A **per-repo dossier** with: stars, language, license, pushed date, what it
   actually does (verified from README), how it would plug in (or not), and a
   recommended action.
4. A short **"integration shape"** map that names the seams we'd touch.

Nothing here is implemented. No source file changed. No phase advanced. This
document is the input to the next `BACKLOG.md` intake entry.

---

## How headcleaner integrates with anything

Before scoring, the seam map. Every external tool hits headcleaner through one
of these surfaces — and which one it hits determines the score.

| Seam | File | Contract |
|------|------|----------|
| **New document format** | `src/headcleaner/engines/<format>.py` | implements `Adapter` (one `extract()`, `name`, `extensions`), registered in `router.py:_ADAPTERS` |
| **New output format / post-processor** | `src/headcleaner/emit/<format>.py` | consumes `CanonicalDoc`, writes a file under the run root |
| **New policy / lint rule** | `src/headcleaner/lint.py` | returns `Finding` with severity |
| **New CLI subcommand** | `src/headcleaner/cli.py` | Click group, shares `theme.py` palette |
| **MCP tool** | `src/headcleaner/mcp/` | read-only by design, returns JSON with citations |
| **New surface (HTTP/serve)** | `src/headcleaner/serve*.py` | read-only, binds 127.0.0.1 |
| **External binary shim** | `src/headcleaner/engines/officecli.py` is the template | subprocess, JSON in, `CanonicalDoc` out |

A repo that fits a **single seam** (e.g. "it could be a new engine") scores
higher than one that would require building a new seam (e.g. "it would be its
own daemon").

A repo that **violates the trust stance** scores zero on `Trust alignment`,
regardless of stars:

- `status: unverified` is mandatory after auto-conversion.
- `verified: human:pending` is mandatory until a human runs `headcleaner review`.
- `generated: human:<user>@<host>` is mandatory (no `agent:` or `model:` claiming review).
- Stale-after is 180 days, deterministic.

A candidate that would **fabricate** any of these (e.g. auto-set `verified`,
generate citations it can't back, or claim "AI reviewed" without a human signoff
mechanism) is a **reject**, not a "later."

---

## Scoring rubric (0–5 per axis, 25 max)

| Axis | What it measures |
|------|------------------|
| **Strategic fit** | Does it serve headcleaner's core job — convert documents to Markdown/OKF, lint them, or let humans/agents consume the result? |
| **Trust alignment** | Does it respect the never-auto-claim-review stance and treat sources as citable? Can it be wrapped without leaking fabricated provenance? |
| **Maturity** | Stars, recent pushes, releases, license clarity, tests/CI. |
| **Integration friction** | How many seams does it touch? How much glue code? Does it add a heavy runtime (binary, daemon, model, network)? |
| **Unique need** | Does headcleaner *actually* need this, or is it nice-to-have / duplicative of something already on disk? |

Thresholds: **20–25 strong candidate** (next-phase material); **15–19 watchlist**
(holds for a real user need); **10–14 decline-with-reason** (rejected but the
reason is recorded); **<10 reject** (no fit or actively contrary to stance).

---

## Ranked tiers

### Tier A — Strong candidate (score ≥ 20)

| Rank | Repo | ★ | Lang | Score | Recommended action |
|-----:|------|--:|------|------:|--------------------|
| 1 | `scaccogatto/okf-skills` | 324 | Python | **24** | Vendor the §11 conformance checker and the `viz.html` renderer as `headcleaner lint` rules and an optional `headcleaner viz` subcommand. This is the canonical OKF v0.2 toolchain; headcleaner already targets v0.2. |
| 2 | `rvben/rumdl` | 1,441 | Rust | **22** | Optional add-on engine for `headcleaner lint markdown`. Wraps a single Rust binary (`cargo install rumdl`); no Python deps; under MIT; actively released (v0.2.58). |
| 3 | `NanoNets/docstrange` | 1,528 | Python | **20** | Strong candidate *only* for hard cases (scanned PDFs, tables in image form, exotic Office formats) — call as a subprocess adapter the way we already call `officecli`. **Do not** let it touch `verified`/`generated`. |

### Tier B — Watchlist (15–19)

| Rank | Repo | ★ | Lang | Score | Why watchlist |
|-----:|------|--:|------|------:|---------------|
| 4 | `basnijholt/agent-cli` | 225 | Python | 19 | RAG chunking, transcription, hotkeys are orthogonal to headcleaner's purpose but the *chunking strategies* (`fixed-size`, `sliding-window`, `paragraph`, `recursive`, `header`, `semantic`) directly inform any future `headcleaner chunk` subcommand. Borrow the strategy taxonomy, do not import. |
| 5 | `messkan/rag-chunk` | 116 | Python | 18 | Same chunking strategies as above, plus token-accurate evaluation. Small surface, MIT, recently released (v0.3.0). Worth a single reading session before designing the chunk subcommand — not worth importing as a dep. |
| 6 | `parsehawk/parsehawk` | 62 | Python | 17 | Local-first document → structured JSON; same shape as headcleaner but JSON-first instead of Markdown/OKF-first. Overlap is real; integration story is "another adapter backend for tricky layouts" if a user needs JSON instead of MD. |
| 7 | `thombashi/pytablewriter` | 630 | Python | 17 | Multi-format table *writer* (CSV/Excel/Markdown/etc.). headcleaner emits Markdown already; `pytablewriter` would only matter if we add `--format csv|excel` to the emit pipeline. No current user need recorded. |
| 8 | `harshankur/officeParser` | 528 | TS | 16 | Office + PDF + RTF + EPUB parser with AST visualizer. Could replace or complement `officecli` for users on Windows where `officecli` is unavailable. Heavy dep (TS toolchain, large disk). Watch, do not act. |
| 9 | `coderaiser/putout` | 796 | JS | 15 | Linter + codemod framework for JS/TS/JSON/YAML/Markdown. Could feed `headcleaner lint` for source-tree Markdown; not the OKF/Markdown body that lint already covers. Different audience (devs editing prose vs. headcleaner's converted output). |

### Tier C — Decline-with-reason (10–14)

| Rank | Repo | ★ | Lang | Score | Reason |
|-----:|------|--:|------|------:|--------|
| 10 | `charmbracelet/glow` | 26,974 | Go | 14 | Gorgeous Markdown renderer for the terminal, but headcleaner already has a custom Textual TUI in the neon palette (cyan/pink/purple). Calling out to `glow` would re-introduce a second TUI palette, violate the color discipline in AGENTS.md, and add a Go binary on PATH. **Decline.** |
| 11 | `daaain/claude-code-log` | 1,197 | Python | 14 | Renders Claude Code transcripts to readable HTML/Markdown. Adjacent to headcleaner's *output* (we already render converted docs); not adjacent to its *input*. No current need to ingest Claude transcripts. **Decline** unless a user asks for a `headcleaner convert ~/.claude/projects` flag. |
| 12 | `ZeroSumQuant/claude-conversation-extractor` | 661 | Python | 13 | Same shape as `claude-code-log`; smaller surface, "claude-start"/"claude-extract" CLIs, last pushed 2026-01-02 (≈7 months stale). Less polished than `claude-code-log`. **Decline** for the same reason and note staleness. |
| 13 | `daaain/claude-code-log` & `ZeroSumQuant/...` overlap | — | — | — | Both target the same niche (Claude transcript export). If headcleaner ever ingests transcripts, pick **one**, and prefer `daaain/claude-code-log` (1.5.0 vs v1.1.2, pushed 2026-07-31 vs 2026-01-02, HTML + Markdown output vs Markdown-only). |
| 14 | `raphaelmansuy/code2prompt` | 882 | Python | 13 | Aggregates a source tree into a single Markdown prompt for an LLM. *Inverse* of headcleaner (we go document → Markdown; this goes repo → LLM prompt). Adjacent only if we ever expose an `LLM context package` MCP tool, and even then we can build a 200-line script without a dep. **Decline**. |
| 15 | `DavidWells/markdown-magic` | 866 | JS | 12 | Comment-block-driven Markdown regeneration. Wrong audience: rewrites the source `.md` based on code anchors; headcleaner writes the `.md` once and never touches the source. **License unclear** in the GitHub API metadata (no `licenseInfo.key` returned) — flag before any use. **Decline**. |
| 16 | `xberg-io/tree-sitter-language-pack` | 459 | Rust | 11 | Compiles 371 tree-sitter grammars; polyglot bindings. Could power a future `headcleaner lint code` for source-tree Markdown linting, but: (a) headcleaner doesn't lint source code today, (b) 1.1 GB of grammars is a heavy install, (c) we'd be re-inventing what `rumdl` already covers for Markdown bodies. **Decline**. |
| 17 | `al1-nasir/codegraph-cli` | 27 | Python | 11 | 27★, v2.1.1, April 2026. "AI-powered code intelligence" with multi-agent codegen — overlaps with `HelixDB`, `Wax`, and a half-dozen other graph-RAG tools in this list. Has no clear seam headcleaner doesn't already cover via the existing search/chunk/graph MCP server. **Decline**. |
| 18 | `christopherkarani/Wax` | 784 | Swift | 10 | Apple-Silicon-only shared single-file memory for agents. Apache-2.0, but **Swift-only** and Apple-only — headcleaner's install path covers macOS / Linux / Windows. Wrong runtime, wrong audience. **Decline**. |
| 19 | `HariSekhon/DevOps-Python-tools` | 823 | Python | 10 | 80+ DevOps CLI tools. Mega-collection; no single tool inside maps to a headcleaner seam. Last pushed 2026-02-03 (~6 months). Cherry-picking one tool is more work than writing it. **Decline**. |

### Tier D — Reject (<10, structurally wrong or contrary to stance)

| Rank | Repo | ★ | Lang | Score | Reason |
|-----:|------|--:|------|------:|--------|
| 20 | `HelixDB/helix-db` | 5,821 | Rust | 9 | Graph-vector database. Powerful, but headcleaner's local-first design uses SQLite/FTS5 + on-disk Markdown, not a separate DBMS process. Adding HelixDB would introduce a daemon, a schema language, and a runtime headcleaner currently has no need for. **Reject** unless a user explicitly asks for a multi-machine corpus. |
| 21 | `kestra-io/kestra` | 27,867 | Java | 7 | Full workflow orchestrator. The opposite of headcleaner: a JVM daemon, a YAML DSL, a web UI, a Docker dependency. headcleaner is intentionally a single static binary's worth of Python + a TUI. **Reject** as integration; could plausibly *call* `headcleaner` as a Kestra task, never the other way around. |
| 22 | `johnkerl/miller` | 10,001 | Go | 6 | CSV/TSV/JSON Swiss-army knife. Useful as a *user-side* shell tool, but headcleaner doesn't re-shape tabular data — it writes Markdown tables. Wrapping `mlr` inside an adapter would duplicate `engines/csv_json.py` for no clear gain. **Reject**. |

> Note: ranks 20–22 share Tier D because none scores 10. The cutoff is not a
> popularity contest; `miller` has 10k stars and `HelixDB` has 5.8k, both
> still rejected because they add weight headcleaner doesn't need.

---

## Per-repo dossiers

### 1. `scaccogatto/okf-skills` — ★324 / Python / MIT / pushed 2026-08-15 / `okf--v0.7.2`

**What it is.** The canonical OKF v0.2 toolchain for Claude Code, agents, and
plain CI. Ships as a Claude Code plugin, a `skills.sh`-discoverable skills pack,
and a GitHub Action. Components:

- `/okf:okf` skill — produce / maintain / consume bundles against the vendored
  v0.2 spec (`skills/okf/reference/SPEC.md`).
- `/okf:validate` skill — deterministic §11 conformance checker
  (`skills/validate/scripts/okf_validate.py`), runnable zero-config with `uv`.
- `/okf:visualize` skill — renders a bundle to a self-contained `viz.html`
  interactive graph (live demo: <https://scaccogatto.github.io/okf-skills/>).
- Composite `action.yml` for CI gating.
- Templates and a sample bundle (the same bundle behind the live demo).

**Why it scores 24.** headcleaner's `emit/okf.py` already targets OKF v0.2 with
the full trust family (`type`, `sources`, `verified`, `generated`, `stale_after`),
and `lint.py` already does §11-ish structural checks. `okf-skills` provides
(1) a battle-tested standalone validator we can vendor (a 200-line Python
script with PyYAML) and (2) a self-contained graph renderer we can wrap as
`headcleaner viz <bundle>` without writing the graph code ourselves. Same
license family (MIT/Apache-2.0), same spec, same trust semantics — its
`generated: {by, at}` and `verified[]` shape match headcleaner's existing
emitter 1:1.

**Integration shape.** Two small seams:

- `src/headcleaner/okf_validate.py` — calls the vendored script as a
  subprocess (or imports its logic) and maps its findings into
  `lint.Finding`.
- `src/headcleaner/okf_viz.py` — calls `okf_visualize.py` to emit
  `<bundle>/viz.html` and surfaces the path in the run report.

**Friction.** Low. Both scripts are single-file Python with `pyyaml` and
PEP 723 inline metadata; they run under `uv run` and have no transitive
dependencies to install. No network, no daemon, no model.

**Trust note.** `okf-skills` derives trust tier (`unverified` /
`machine-confirmed` / `human-reviewed`) *at render time* from
`generated`/`verified` — it does **not** store a tier as an opinion. That
matches headcleaner's stance exactly. Use it.

---

### 2. `rvben/rumdl` — ★1,441 / Rust / MIT / pushed 2026-08-19 / v0.2.58

**What it is.** A fast Markdown linter and formatter in Rust, "ruff for
Markdown." Ships as a single Rust binary (`cargo install rumdl`) and as a PyPI
wheel; CLI is `rumdl check .` / `rumdl fmt .` / `rumdl init`. 1,441★, MIT, weekly
releases, GitHub Action published.

**Why it scores 22.** headcleaner's `lint.py` already covers frontmatter
shape, code-fence pairing, heading hierarchy, and line length — all the things
OKF cares about. But the *prose* rules (MD033 no-inline-HTML, MD041
first-line-h1, MD024 duplicate-heading-suffix, etc.) are not in `lint.py`, and
`rumdl` has them in a fast, well-maintained package. Wrapping `rumdl` as an
optional `headcleaner lint markdown --engine rumdl` mode gives users a
Markdown-body linter without us maintaining the rule list.

**Integration shape.** One new file: `src/headcleaner/engines/md_rumdl.py`
(or simpler — a `--engine` flag on the existing `md.py` lint path). Subprocess
call, parse `rumdl check --format json` output, map to `lint.Finding`. Optional
via `pyproject.toml` extra (`headcleaner[rumdl]`).

**Friction.** Lowest of any tier-A candidate. Single binary, no Python
runtime deps, exit codes are stable, JSON output is documented. The only
concern is "yet another binary on PATH" — but the same complaint applies to
`officecli`, which we already depend on, and the install story
(`pip install rumdl` from PyPI or `cargo install rumdl`) is well-trodden.

**Trust note.** Pure Markdown rules; no source attribution, no claims about
provenance. Safe.

---

### 3. `NanoNets/docstrange` — ★1,528 / Python / MIT / pushed 2025-10-31 / no release tag

**What it is.** "Document → Markdown/JSON/CSV/HTML" converter with a 7B model
under the hood for layout understanding and OCR. Also ships an MCP server,
a local Web UI, and a cloud API (opt-in). 1,528★, MIT. **Last push 2025-10-31
(≈10 months stale).** No GitHub release tag — only PyPI versions.

**Why it scores 20, not 25.** The capability is genuinely useful for the
hard cases headcleaner's existing engines punt on: scanned PDFs, tables in
images, weird Office layouts. But:

- **It is a model call.** It runs a 7B model locally by default, with a cloud
  API as the "easy" path. headcleaner's stance is "deterministic, no model,
  no network, no claim of review." Wrapping `docstrange` as an adapter is fine
  *as long as* the adapter enforces: (a) trust fields on the OKF concept are
  set by headcleaner, not by `docstrange`; (b) the cloud API is opt-in and
  documented as such; (c) the local model path is the default and emits a
  clear provenance line in the manifest.
- **Staleness.** 10 months without a push is a yellow flag. PyPI may be more
  recent — verify before adopting.
- **License:** MIT, but verify the 7B model weights are not pulled in under a
  separate (more restrictive) license at install time.

**Integration shape.** One new file: `src/headcleaner/engines/docstrange.py`
implementing `Adapter`. `extract()` shells out to `docstrange extract <file>
--output-format markdown` and returns `CanonicalDoc`. All trust fields set by
`normalize.py`, not by `docstrange`.

**Friction.** Medium. Heavy dep (7B model ~4 GB, or cloud API key), high
disk, longer install. Should be an opt-in adapter behind a feature flag, not
a default engine.

**Trust note.** **Critical.** Do not let `docstrange` write `generated:` or
`verified:` into the OKF frontmatter. The adapter must override whatever
strings `docstrange` emits. Document this loudly in
`docs/safety/permissions.md`.

---

### 4. `basnijholt/agent-cli` — ★225 / Python / MIT / pushed 2026-08-19 / v0.102.4

**What it is.** "Local-first, AI-powered command-line agents": voice
transcription, RAG chunking, hotkeys, autocorrect, TTS/STT servers, macOS app,
memory proxy. 225★, MIT, very active.

**Why it scores 19, watchlist.** headcleaner is a *converter*; `agent-cli` is
a *consumer* (transcribe, autocorrect, RAG over your stuff). The overlap is
the chunking strategy taxonomy. `agent-cli` documents six strategies
(`fixed-size`, `sliding-window`, `paragraph`, `recursive-character`,
`header`, `semantic`) — that taxonomy is exactly what a future
`headcleaner chunk` subcommand would expose. Borrow the names and the
strategy list; don't import the dep.

**Trust note.** `agent-cli`'s `--autocorrect` and "edit clipboard content
with voice commands" paths are the opposite of headcleaner's stance — they
mutate user content based on model output. No trust overlap; treat as
documentation reference only.

---

### 5. `messkan/rag-chunk` — ★116 / Python / MIT / pushed 2026-01-18 / v0.3.0

**What it is.** Python CLI for "test, benchmark, and find the best RAG
chunking strategy for your Markdown documents." Six chunking strategies
(matches `agent-cli`'s), token-accurate via `tiktoken`, evaluates with
precision/recall/F1, exports JSON/CSV. 116★, MIT, v0.3.0.

**Why it scores 18, watchlist.** Same chunking story as #4 but smaller,
single-purpose, and explicitly about Markdown — closer to headcleaner's
output than `agent-cli`'s general transcript handling. If/when
`headcleaner chunk` exists, this is the *reference implementation* to read
before writing the real one. The evaluation harness (precision/recall/F1
against a test JSON) is also a pattern worth borrowing for
`headcleaner lint --experimental-chunk-check`.

**Trust note.** Pure chunking; no provenance or trust fields. Safe to
reference; do not depend on.

---

### 6. `parsehawk/parsehawk` — ★62 / Python / Apache-2.0 / pushed 2026-08-18 / v0.2.4

**What it is.** "Local-first document AI" — document → structured JSON.
Local model by default, opt-in cloud, CLI + REST API + Web UI. 62★,
Apache-2.0, active. README is short (176 lines) but the surface is clear.

**Why it scores 17, watchlist.** Strong overlap with #3 but JSON-first
instead of Markdown-first. For users who want a downstream JSON pipeline
(LangChain, jq, etc.) instead of OKF, this is the better fit. Could be a
parallel adapter (`headcleaner convert --engine parsehawk --format json`)
for that niche, leaving the OKF path to `officecli`/`pdf.py`/`html.py`.

**Trust note.** Same model-call concerns as #3. Apache-2.0 is friendlier
than MIT in some enterprise contexts but doesn't change the trust stance.

---

### 7. `thombashi/pytablewriter` — ★630 / Python / MIT / pushed 2026-07-27 / v1.2.1

**What it is.** Python library to write a *table* in 23 formats
(AsciiDoc/CSV/Elasticsearch/HTML/JSON/LaTeX/Markdown/NumPy/Excel/Pandas/
SQLite/TOML/TSV/YAML/...). 630★, MIT, v1.2.1.

**Why it scores 17, watchlist.** headcleaner already emits Markdown tables
through `engines/csv_json.py` + `emit/markdown.py`. If a user asks for
`--format csv` or `--format xlsx`, `pytablewriter` covers the matrix in one
import instead of N engine-specific writers. No current user need recorded;
hold.

**Trust note.** Pure serialization; no claims. Safe.

---

### 8. `harshankur/officeParser` — ★528 / TS / MIT / pushed 2026-08-18 / v7.8.0

**What it is.** Node.js + browser library that parses 12 office/PDF/RTF/EPUB
formats into a rich AST and re-generates 8 output formats (Markdown, HTML,
CSV, RTF, PDF, EPUB, plain text, RAG chunks). Live AST visualizer at
<https://harshankur.github.io/officeParser/>. 528★, MIT, v7.8.0, active.

**Why it scores 16, watchlist.** It is, in form, a TypeScript alternative to
headcleaner's `officecli.py` + `pdf.py` + `epub.py` + `rtf.py` combined.
Headcleaner's existing engines use `officecli` (a single binary) plus
specialized Python readers; `officeParser` is a pure-JS AST with a single
install footprint. The trade-off is "add Node.js to the install path" vs.
"add one more binary."

**Trust note.** Pure parsing, no claims. Safe. But the disk footprint is
the largest of any candidate (~48 MB + `node_modules`).

---

### 9. `coderaiser/putout` — ★796 / JS / MIT / pushed 2026-08-20 / v42.13.0

**What it is.** Pluggable JS/TS/JSON/SQL/YAML/TOML/Markdown/Ignore linter +
code transformer + formatter with a codemod engine. "ESLint replacement
with built-in code printer." 796★, MIT, v42.13.0, very active.

**Why it scores 15, watchlist.** Its *Markdown* support is real (rules exist,
transformations exist) but headcleaner's `lint.py` Markdown-body rules are
not the use case — headcleaner lints *converted output*, not hand-authored
prose. `putout` is the right answer for a different user (devs editing their
own README) and would only enter headcleaner via a `--lint-source` mode
that does not exist today.

**Trust note.** Pure AST rewriting; safe.

---

### 10. `charmbracelet/glow` — ★26,974 / Go / MIT / pushed 2026-08-16 / v3.0.0

**What it is.** Terminal Markdown reader; "render markdown on the CLI, with
pizzazz." Go, 27k★, MIT, v3.0.0.

**Why it scores 14, decline.** Gorgeous and popular, but headcleaner
already ships a Textual TUI in a custom neon-cyan/pink/purple palette (see
`src/headcleaner/theme.py` and the color discipline section of AGENTS.md).
Adding `glow` would introduce a second TUI palette, conflict with the
brand, and require shipping a Go binary on PATH. **No.**

---

### 11. `daaain/claude-code-log` — ★1,197 / Python / MIT / pushed 2026-07-31 / 1.5.0

**What it is.** Python CLI to convert Claude Code JSONL transcripts into
readable HTML or Markdown. 1,197★, MIT, 1.5.0, active. Supports
`--provider agy|codex` for non-Claude sources.

**Why it scores 14, decline.** Adjacent to headcleaner's *output* (we
already render converted docs to Markdown) but not its *input*. There is no
current user need to ingest Claude transcripts. **Hold** — if a future user
asks for "convert `~/.claude/projects` to OKF," `claude-code-log` is the
closest existing tool and the conversion would be a thin adapter.

---

### 12. `ZeroSumQuant/claude-conversation-extractor` — ★661 / Python / MIT / pushed 2026-01-02 / v1.1.2

**What it is.** Same shape as #11 with two CLIs (`claude-start` interactive
TUI, `claude-extract` plain CLI). 661★, MIT, v1.1.2.

**Why it scores 13, decline.** Strictly less polished than #11 (older,
single output format, no agy/codex provider support, ASCII-art marketing
tone in the README). If a transcript-ingestion subcommand ever ships,
**pick `daaain/claude-code-log`**, not this one.

---

### 13. `raphaelmansuy/code2prompt` — ★882 / Python / MIT / pushed 2026-07-07 / no release tag

**What it is.** "Comprehensive prompts from codebases" — repo →
single-Markdown-prompt for an LLM. Templating, GitHub Actions integration,
LLM CLI integration. 882★, MIT.

**Why it scores 13, decline.** Inverse of headcleaner (we go document →
Markdown; this goes repo → LLM prompt). Adjacent only via the
"build-a-context-package-for-an-agent" concept, which headcleaner's MCP
server already exposes (`assemble_context_package`). If a
`headcleaner llm-context` subcommand ever ships, the right shape is "fold a
headcleaner search result into a single prompt," which is a 200-line
script — not a 882★ dependency.

---

### 14. `DavidWells/markdown-magic` — ★866 / JS / license unclear / pushed 2026-07-27 / `markdown-magic@4.11.0`

**What it is.** Comment-block-driven Markdown rewriter ("keep README.md in
sync with code anchors"). 866★, monorepo with multiple packages.

**Why it scores 12, decline.** Wrong audience: rewrites the *source*
`.md` based on code anchors; headcleaner writes `.md` once from a
non-Markdown source and never touches the source. Also: **license is
unclear** — the GitHub API returns no `licenseInfo.key` for this repo,
which is a yellow flag for any dep. Decline.

---

### 15. `xberg-io/tree-sitter-language-pack` — ★459 / Rust / MIT / pushed 2026-08-20 / v1.15.2

**What it is.** Compiles 371 tree-sitter grammars; Rust + Python + Node.js
+ Go + Java + Ruby + Elixir + PHP + C# + WASM + Dart + Kotlin + Swift + Zig
+ CLI bindings. 459★, MIT, v1.15.2.

**Why it scores 11, decline.** 1.1 GB of grammar data to lint *source code*
that headcleaner doesn't lint. `rumdl` (#2) covers the Markdown-body case
in a single binary. The use case for this in headcleaner would be "lint
source-tree Markdown for syntax-correctness," which is a niche we don't
serve today.

---

### 16. `al1-nasir/codegraph-cli` — ★27 / Python / MIT / pushed 2026-04-08 / v2.1.1

**What it is.** "AI-powered code intelligence" with semantic search,
multi-agent codegen, impact analysis, CrewAI agents. 27★, MIT, v2.1.1.

**Why it scores 11, decline.** 27 stars is below the threshold we'd adopt
from cold. Overlaps with #18 (Wax), #20 (HelixDB), and our own MCP server's
graph tool. No clear seam headcleaner doesn't already cover.

---

### 17. `christopherkarani/Wax` — ★784 / Swift / Apache-2.0 / pushed 2026-08-20 / `waxmcp-v0.1.30`

**What it is.** Apple-Silicon-only, single-file shared memory layer for AI
agents. Foundation Models, Claude, Cursor, Codex, Hermes. 784★, Apache-2.0.

**Why it scores 10, decline.** **Swift-only, Apple-only.** headcleaner's
install path is macOS / Linux / Windows. Wrong runtime, wrong audience,
no seam.

---

### 18. `HariSekhon/DevOps-Python-tools` — ★823 / Python / MIT / pushed 2026-02-03 / no release tag

**What it is.** 80+ DevOps CLI tools in one mega-repo (AWS, GCP, Spark,
Hadoop, log anonymizer, data format converters, etc.). 823★, MIT.

**Why it scores 10, decline.** Cherry-picking one tool out of 80 is more
work than writing that tool. Last push ~6 months ago. Decline.

---

### 19. `HelixDB/helix-db` — ★5,821 / Rust / Apache-2.0 / pushed 2026-08-20 / v3.1.1

**What it is.** Graph-vector database for knowledge graphs and AI memory,
Rust, on object storage. 5,821★, Apache-2.0, v3.1.1, YC-launched.

**Why it scores 9, reject.** Powerful but wrong shape: a daemon, a schema
language, a storage backend. headcleaner's design uses SQLite/FTS5 for
search and on-disk Markdown for the canonical store. Adding HelixDB would
double the storage story, introduce a runtime, and require a migration
plan that has no user demand behind it. **Reject.**

---

### 20. `kestra-io/kestra` — ★27,867 / Java / Apache-2.0 / pushed 2026-08-20 / v1.3.30

**What it is.** Open-source orchestration & scheduling platform; JVM
daemon, YAML DSL, web UI, Docker-first. 27,867★, Apache-2.0.

**Why it scores 7, reject.** The opposite of headcleaner's shape. Kestra
could plausibly *call* `headcleaner` as a Kestra task (which is a fine
one-liner: `kestra task: headcleaner convert IN OUT`); headcleaner should
never *be* Kestra. Decline.

---

### 21. `johnkerl/miller` — ★10,001 / Go / BSD-2-Clause / pushed 2026-08-20 / v6.21.0

**What it is.** `awk`/`sed`/`cut`/`join`/`sort` for CSV/TSV/JSON. 10,001★,
BSD-2-Clause, v6.21.0.

**Why it scores 6, reject.** Useful as a *user-side* shell tool, but
headcleaner doesn't re-shape tabular data — it writes Markdown tables from
`CanonicalDoc` rows. Wrapping `mlr` would duplicate `engines/csv_json.py`
for no gain.

---

## Integration shape, if we adopt Tier A

If the next phase accepts Tier A, here is the minimum surface area to land
the three repos. None of this is committed; this is the proposed seam map.

### Tier A.1 — `okf-skills`

- **Vendor:** `skills/okf/reference/SPEC.md` (the verbatim OKF v0.2 spec) →
  `docs/reference/okf-v0.2-spec.md` with attribution.
- **Vendor:** `skills/validate/scripts/okf_validate.py` →
  `src/headcleaner/_okf_vendor/okf_validate.py` (vendored, not pip-installed).
- **New CLI:** `headcleaner okf validate <bundle> [--strict]` — calls the
  vendored script, returns the same `lint.Finding` list `lint.py` already
  produces, exit code 1 on error.
- **New CLI:** `headcleaner okf viz <bundle> [--out viz.html]` — calls
  `okf_visualize.py`, surfaces the path in the run report.
- **Tests:** round-trip a hand-rolled OKF bundle through `okf_validate.py`
  with both passing and failing cases.
- **Docs:** add `docs/integrations/okf-skills.md` with install steps, license
  attribution, and the vendored-script policy (vendored so headcleaner
  doesn't fail when the upstream plugin is uninstalled).

### Tier A.2 — `rumdl`

- **Optional dep:** add `rumdl = { version = ">=0.2,<1.0", optional = true }`
  to `pyproject.toml` under `[project.optional-dependencies]`.
- **New flag:** `headcleaner lint markdown --engine rumdl` — when set,
  `lint.py` calls `rumdl check --format json` and maps findings to
  `lint.Finding`. Default engine is the built-in `lint.check_markdown`.
- **Tests:** skip if `rumdl` is not on PATH; otherwise, fixture a Markdown
  file with one known MD033 violation and assert one error finding.
- **Docs:** add `docs/integrations/rumdl.md` listing the exact rules
  covered and how to disable.

### Tier A.3 — `docstrange`

- **Opt-in adapter:** `src/headcleaner/engines/docstrange.py` registered
  in `router.py:_ADAPTERS` *only* when `HEADCLEANER_ENABLE_DOCSTRANGE=1`
  is set (or `--experimental-docstrange` flag).
- **Trust override:** `normalize.py` must overwrite `generated:` and
  `verified:` from any `docstrange` output. Add a regression test that
  asserts `verified == "human:pending"` even if `docstrange` returns
  anything else.
- **Docs:** add `docs/integrations/docstrange.md` with the model and disk
  cost, the opt-in flag, and the explicit "do not let it touch trust
  fields" rule.
- **Why opt-in, not default:** `docstrange` ships a 7B model by default
  (~4 GB download). Default-on install would make `headcleaner convert`
  10× heavier and 10× slower for users who don't need it.

---

## What this document is not

- Not an implementation plan. No source file is touched.
- Not a phase audit. The active phase (Phase 2, documentation governance) is
  not advanced by this research deliverable; the next phase that *would*
  adopt any of these should create `docs/development/phase-audits/<phase>.json`
  with this document cited as evidence.
- Not a license opinion. Each integration needs its own license review at
  adoption time; this doc records the SPDX key from the GitHub API, which
  is a starting point, not a substitute.
- Not a final ranking. The user can override any verdict here. The scores
  are the rubric applied consistently; the recommendations are mine, not
  the rubric's.

---

## Next step

If you (the maintainer) agree with Tier A, the next move is to add an
intake row to [`../../BACKLOG.md`](../../BACKLOG.md):

```
| Tier A integrations | Vendor okf-skills validator + viz; wrap rumdl as optional lint engine; opt-in docstrange adapter. | Active-document coverage (OKF_NOTES or equivalent), integration pages, vendored-script policy. | intake |
```

…then create the corresponding `docs/development/phase-audits/<phase>.json`
before any source file changes, per `docs/development/DOCUMENTATION_GOVERNANCE.md`.

If you don't agree, edit the verdicts in this document — the raw artifacts
under `docs/integrations/research/` are the audit trail, not the verdicts.
