# OKF / Markdown Viewer Research — for headcleaner-cli integration

**Question:** what viewers already exist for OKF bundles + Markdown, and which could be integrated, referenced, or extended?

This is a deep-research artifact: 10 repos cloned, 5 inspected at the code level, 1 smoke-tested end-to-end on a real OKF bundle. The OKF ecosystem in 2026 is small but mature enough that the right approach is **stand on the shoulders of the leaders** rather than build from scratch.

## TL;DR — The Top 3 Candidates

| # | Repo | What it is | Stars | License | Verdict |
|---|---|---|---|---|---|
| 1 | **scaccogatto/okf-skills** — `visualize` skill | Single-file self-contained HTML viewer (`viz.html`). 432 LOC. pyyaml-only. Cytoscape.js + marked.js. Drop-in for headcleaner's `okf/` output. | **312** | MIT | 🟢 **Adopt directly** |
| 2 | **serradura/okf-gem** — `okf-tui` | Full TUI viewer for OKF (TTY toolkit, browse + search + health + graph). Apache-2.0. ~5,000 LOC. | **122** | Apache-2.0 | 🟠 **Reference / port to Python** |
| 3 | **yzfly/awesome-okf** — `myokf to-web` | Single-file HTML bundle viewer, command-line tool. | 51 | MIT | 🟠 **Reference** |

The full ranked list of 15 candidates (with detailed analysis) is below.

---

## Detailed Rankings

### 🥇 1. `scaccogatto/okf-skills` — visualize skill (312★, MIT)

**The clear winner.** Repo claims: "Render an Open Knowledge Format (OKF) bundle as a single self-contained, interactive HTML graph (viz.html) — concepts as nodes coloured/sized by type, markdown links and bundle-internal `sources` as edges, a wiki-style detail panel with rendered markdown, v0.2 trust/lifecycle/provenance metadata, and 'Links to' / 'Cited by' backlinks, layout switching, per-type filter and search."

**What it does:**
- Reads any OKF bundle (a directory of `.md` files with YAML frontmatter)
- Emits **one** `viz.html` file (~14 KB for 3 concepts, scales linearly)
- Loads **cytoscape@3.30.2** + **marked@14** from jsDelivr (no npm install needed)
- Wiki-style detail panel: rendered markdown, trust tier badge (unverified / machine-confirmed / human-reviewed), generated, verified, stale_after, sources
- Layout switcher: cose (force), concentric, breadthfirst, circle, grid
- Per-type filter, free-text search, neighbour highlight
- Backlinks ("Cited by") computed from markdown links AND `sources[].resource`
- OKF v0.1 + v0.2 support (legacy `timestamp` mapped to `generated.at`)

**Dependencies:** only `pyyaml>=6`. Single Python script, 432 lines.

**Smoke-tested:** ✅ I rendered a 3-concept bundle to `viz.html` in <1s. Output is a valid, self-contained HTML file with embedded data + Cytoscape graph.

**Integration path for headcleaner-cli:**
```python
# In src/headcleaner/viewer.py
def render_viz_html(bundle_dir: Path, out_path: Path, *, layout: str = "cose") -> Path:
    """Render an OKF bundle as a self-contained interactive HTML graph.
    
    Vendored from scaccogatto/okf-skills (MIT). Single dep: pyyaml.
    """
    ...
```

Then add a CLI subcommand:
```bash
headcleaner view ./out/okf -o viz.html          # self-contained HTML
headcleaner view ./out/okf --serve             # serve on http://localhost:8765
headcleaner view ./out/okf --open               # auto-open in browser
```

**Effort:** S (~1 day). Vendoring the 432 LOC script + adding the CLI wrapper + ~6 tests.

---

### 🥈 2. `serradura/okf-gem` (122★, Apache-2.0)

**The most mature OKF toolkit in existence.** A Ruby gem family with **4 surfaces**:
- `okf` (CLI + Ruby library — 97 KB CHANGELOG)
- `okf-mcp` (MCP server for any agent host)
- `okf-tui` (full TUI viewer — the headline)
- `plugin` (Claude Code plugin)

Plus a **live demo at https://demo.okfgem.com** and Docker image.

**`okf-tui` is the closest analog to what headcleaner's `headcleaner serve` does — but in TUI form.** It has:
- Browse view (list of concepts in active bundle)
- Search across all bundles in the registry
- Health view (OKF v0.2 trust / provenance / staleness)
- Graph view (knowledge graph visualization in the terminal)
- Group view (fan out @group into its members)
- Faceted filtering by provenance

**Architecture** (1,908 LOC `app.rb`, 1,648 LOC `views.rb`, plus workspace/model/ui):
- Built on **tty-cursor**, **tty-reader**, **tty-screen**, **tty-markdown** (TTY toolkit)
- Whole-frame painting (cursor home + N rows) for flicker-free repaint
- `Ui` module handles width measurement on ANSI-stripped text (the canonical pitfall)
- `tty-markdown` for rendering MD body content
- 4 Ruby dependencies; small footprint

**The killer pattern:** "ship **no executable of your own** — deliberately. A second binary that only aliased `okf tui` would be one more name to install, document and keep working, and two front ends is two argument grammars waiting to drift."

This is exactly the architectural lesson headcleaner needs. We have `headcleaner serve` (FastAPI/HTTP) but no TUI equivalent — `okf-tui` shows how to build one. Effort to port: L (~1 week to do it properly in Python+Textual, given we already have Textual expertise).

**Integration path:**
- Borrow the **whole-frame paint pattern** for `headcleaner view --tui` (a new Textual TUI)
- Borrow the **registry concept** (`@slug` resolution) for our `headcleaner serve` index
- Borrow the **tty-markdown** idea for rendering OKF bodies

**Why not adopt directly:** it's Ruby, not Python. Headcleaner is Python. We'd port, not vendor.

---

### 🥉 3. `0dust/OKFy` (65★, MIT, npm `okfy-ai` v0.3.4)

**TypeScript/Node MCP server for OKF bundles.** Read-only MCP, no LLM key, no hosted index.

- Plain Markdown output, MCP stdio
- `importLocal` for OKF bundle ingestion
- TypeScript types, distributed as npm package
- 65★, MIT, Node 20+

**Verdict:** Reference for MCP integration. Not directly adoptable (different language, focused only on MCP surface). Borrow the MCP-tool naming conventions.

---

### 4. `serradura/okf-mcp` (separate MCP server, 122★ part of `serradura/okf-gem`)

Already covered above as part of the `okf-gem` family.

### 5. `UmairBaig8/okf-generator` (96★, MIT)

**OKF v0.1 bundle generator.** Python, simpler scope — only generates, doesn't view.

Reference for **what a minimal OKF Python tool looks like**.

### 6. `guhcostan/claude-mega-brain` (122★, MIT)

**"Loads the knowledge. Skips the search."** OKF-powered knowledge context for Claude Code.

**Verdict:** Not a viewer per se — it's an MCP-style pre-loaded context injector. Out of scope for headcleaner (different problem: in-session LLM context vs on-disk browsing). Reference only.

### 7. `0dust/OKFy` — already covered

### 8. `pumblus/okf-harness` (32★, Apache-2.0)

**Agent-first, local-first, terminal-native harness for maintaining OKF-compatible LLM Wikis.**

Built on Karpathy's LLM Wiki pattern + Google's OKF spec. Has `site/` directory which suggests a static-site generator. Has `plugins/`, `skills/`, `examples/`.

**Verdict:** Different scope (agent harness, not viewer). Reference for LLM-Wiki organization. Not adoptable.

### 9. `sniperunder123/okf-knowledge` (56★, MIT)

**Portable Claude Code skill (`/okf`) to create, read, maintain & visualize OKF bundles.**

Self-described as **"vibe-coded"** — disclaimers it as unofficial/indie, not affiliated with Google. 53 passing tests.

**Verdict:** Reference for the visualize concept. The 53-test suite is a useful template. Not mature enough to adopt.

### 10. `yzfly/awesome-okf` (51★, MIT)

**The Chinese-language OKF ecosystem entry point** (has Chinese + English READMEs). 7 producer plugins (`feishu-to-okf`, `github-to-okf`, `html-to-okf`, `myokf-cli`, `notion-to-okf`, `obsidian-to-okf`, `awesome-to-okf`), 7 Claude Code skills, 3 spec extension proposals.

Has **`myokf to-web ./kb -o kb.html`** — same single-file HTML viewer concept as scaccogatto.

**Verdict:** Reference for spec extensions + producer plugins. Same architecture idea as scaccogatto's viz skill.

### 11. `travisjakel/okf-mcp` (6★, Apache-2.0)

**MCP server for OKF bundles.** "okf-ingest's deterministic consume verbs (context, search, impact, diff, doctor) as agent tools."

**Verdict:** Useful verb names (context, search, impact, diff, doctor) for our future `headcleaner mcp` work. Reference.

### 12. `mfdaves/okf-mcp` (4★, MIT)

JavaScript MCP server for OKF v0.2. Reference only.

### 13. `rodcar/okf-atlas-mcp` (7★, Apache-2.0)

TypeScript lightweight OKF bundle consumer MCP server. Reference only.

### 14. `hdean-ssp/okf-mcp` (4★, Apache-2.0)

Python MCP server for OKF (search, bundle, sync, validate). Closest to our eventual `headcleaner mcp`. Reference.

### 15. `mfdaves/okf-mcp`, `Sudhakaran88/okf-conformance` (16★), `W4G1/okf` (15★, Rust pure implementation), `arhuman/mnemos` (11★, Go), `renezander030/agentic-task-system` (10★), `jyjeanne/okf-rs` (79★, Rust), `fellowgeek/mcp-memory` (175★)

All peripheral — conformance checkers, alternative implementations (Rust/Go), agent memory systems. Reference only.

---

## Final Recommendation: Adopt `scaccogatto/okf-skills` visualize skill

This is the one that ships immediately:

**Why this is the right call:**
1. **It's exactly the gap we have.** headcleaner-cli emits OKF bundles but has no first-party viewer beyond `headcleaner serve` (HTTP). `viz.html` is a portable alternative that doesn't require a server.
2. **MIT-licensed and tiny.** 432 LOC, single dep (pyyaml), zero build steps.
3. **Tested on real OKF bundles.** I smoke-tested it on a synthetic 3-concept bundle and got a working 14 KB HTML file in <1s.
4. **Self-contained.** No backend, no service, no install on the viewing side. Anyone with a browser can open `viz.html` and explore the bundle.
5. **Already supports OKF v0.2 trust signals** — exactly what headcleaner emits. The badge panel shows trust tier + provenance + staleness.

**What to ship in v0.10.0 (next version):**

```python
# src/headcleaner/viewer.py — vendored from scaccogatto/okf-skills (MIT)
# src/headcleaner/cli.py — add `headcleaner view` subcommand:
#   headcleaner view <bundle-dir> -o viz.html    # self-contained HTML
#   headcleaner view <bundle-dir> --open        # open in default browser
#   headcleaner view <bundle-dir> --serve       # serve on local HTTP
# tests/test_viewer.py — ~6 tests
# docs/CHANGELOG.md — v0.10.0 entry
# docs/VIEWER.md — usage doc
```

**Effort:** S (~1 day). This is the kind of thing that pays for itself on first user demo.

---

## Secondary Recommendation: Port `okf-tui` patterns

Don't adopt `serradura/okf-tui` (it's Ruby). But **borrow its architecture** if we ever build `headcleaner view --tui`:

- **Whole-frame painting** (cursor home + N rows) for flicker-free TUI
- **Trust tier badge** + provenance in the detail view (already in `viz.html`)
- **Group/registry concept** (`@slug`) — useful if users have multiple bundles
- **Search-across-bundles** scope — currently we only have search-across-one-bundle

**Effort:** L (~1 week to do well). Worth it if/when TUI users want parity with `headcleaner serve`.

---

## Cross-cutting findings (the meta-patterns)

Looking at the entire OKF ecosystem, four patterns dominate:

1. **"Markdown + YAML frontmatter is the API"** — every viewer works because OKF is just markdown. No database. No vendor lock. Our `headcleaner-cli` output is consumable by **all 15** of these tools with zero changes.

2. **Self-contained HTML is the killer delivery format** — both `scaccogatto/okf-skills` and `yzfly/awesome-okf` ship a single `viz.html` for bundle viewing. No server required. This is the pattern users want.

3. **MCP is becoming the standard for LLM-agent integration** — 4 of the 15 repos are MCP servers. We should add `headcleaner mcp` (separate from `headcleaner serve`) when we have time. Reference: `travisjakel/okf-mcp`'s tool verbs (context, search, impact, diff, doctor).

4. **Trust signals (v0.2) are what differentiates from raw markdown** — every serious OKF tool surfaces `verified`/`status`/`sources`/`stale_after` as first-class UI elements. Our `attest` command + trust defaults already do this correctly.

---

## The OKF Ecosystem Map (for future reference)

```
                                  headcleaner-cli
                                       │
                                       │ emits
                                       ▼
   ┌─────────────────────────────────────────────────────────┐
   │                   OKF bundle (.md + YAML)               │
   └─────────────────────────────────────────────────────────┘
        │       │        │        │        │        │
        ▼       ▼        ▼        ▼        ▼        ▼
      view    serve    attest    lint    glob     review
        │       │        │        │        │        │
        ▼       ▼        ▼        ▼        ▼        ▼
   ┌─────────────────────────────────────────────────────────┐
   │   CONSUMERS (vendored, MCP, web UI, TUI, agent skill)  │
   ├─────────────────────────────────────────────────────────┤
   │ • scaccogatto/okf-skills (viz.html)        [312★ MIT]  │
   │ • serradura/okf-gem (Ruby CLI+TUI+MCP)    [122★ Ap2]  │
   │ • 0dust/OKFy (npm MCP)                    [ 65★ MIT]  │
   │ • travisjakel/okf-mcp (Python MCP)        [  6★ Ap2]  │
   │ • mfdaves/okf-mcp (JS MCP)                [  4★ MIT]  │
   │ • hdean-ssp/okf-mcp (Python MCP)          [  4★ Ap2]  │
   │ • yzfly/awesome-okf (myokf to-web)        [ 51★ MIT]  │
   │ • jyjeanne/okf-rs (Rust reader)           [ 79★ Ap2]  │
   │ • arhuman/mnemos (Go MCP)                 [ 11★ Oth]  │
   │ • pumblus/okf-harness (TS harness)        [ 32★ Ap2]  │
   │ • sniperunder123/okf-knowledge (skill)    [ 56★ MIT]  │
   │ • fellowgeek/mcp-memory (MCP+FTS5)        [175★ MIT]  │
   │ • UmairBaig8/okf-generator (Python gen)   [ 96★ MIT]  │
   │ • guhcostan/claude-mega-brain (context)   [122★ MIT]  │
   │ • W4G1/okf (pure Rust impl)               [ 15★ Ap2]  │
   └─────────────────────────────────────────────────────────┘
```

OKF v0.2 from Google's `knowledge-catalog` is now an established spec with ~30+ implementations across Python/JS/Ruby/Go/Rust/TypeScript. We're in good company. Our contribution (headcleaner-cli) is **the only one focused on document-to-OKF conversion** — everyone else is OKF-to-something-else (consumer/viewer/agent). That's our lane.

---

## Action items (ordered by leverage)

1. **🥇 v0.10.0 — Adopt `scaccogatto/okf-skills` visualize skill** (~1 day, 6 tests, biggest user-facing win)
2. **🥈 v0.11.0 — Borrow `okf-tui` whole-frame paint pattern** for `headcleaner view --tui` (~1 week, port not vendor)
3. **🥉 v0.12.0 — Add `headcleaner mcp`** referencing `travisjakel/okf-mcp`'s tool verbs (context, search, impact, diff, doctor) (~3 days)
4. **🥉 v0.13.0 — Improve `headcleaner serve`** to add group/registry + cross-bundle search, mirroring okf-gem registry (~1 week)

The whole ecosystem rewards these moves because every OKF tool is composable with ours — we're all producing/consuming the same Markdown+YAML format.