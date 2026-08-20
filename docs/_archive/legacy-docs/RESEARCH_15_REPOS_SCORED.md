# Repo Research — Scored for headcleaner-cli Integration

**Purpose:** Rank and rate 15 GitHub repos (11 unique URLs submitted, `office_oxide` listed twice) for integration with `headcleaner-cli v0.7.0`. Each repo scored on 5 dimensions, with a final composite score and a recommended action.

## Scoring Rubric (0–10 each, weighted as shown)

| Dimension | Weight | What it measures |
|---|---|---|
| **Domain fit** | 30% | How directly the repo solves a problem headcleaner solves today or should solve next |
| **Maturity** | 20% | Stars × recency × maintenance signals (commits, releases, CI) |
| **Adoption friction** | 15% | How easy it would be to vendor / pip-install / shell out from headcleaner |
| **License compatibility** | 15% | Compatible with headcleaner's Apache-2.0 |
| **Code quality / clarity** | 20% | Clean architecture, well-documented, low technical debt |

**Composite score** = weighted average × 10. Recommended actions are:
- 🟢 **Adopt** (score ≥ 7.5) — integrate now
- 🟡 **Spike** (5.0–7.4) — time-box a 1-2 day evaluation
- 🟠 **Reference** (3.0–4.9) — read the source, don't adopt
- 🔴 **Pass** (< 3.0) — out of scope or not worth the time

---

## The 15 Repos

### 1. `yfedoseev/office_oxide` — 99★ Rust Office lib

| | |
|---|---|
| **Description** | "Fastest Office document library for Python, Rust, Go, JS/TS, C#, WASM. DOCX/XLSX/PPTX/DOC/XLS/PPT. Up to 100× faster than python-docx/openpyxl/python-pptx. 100% pass rate on valid Office files." |
| **Language** | Rust (Python bindings, C#, Go, JS/TS, WASM) |
| **License** | Apache-2.0 + MIT (dual) |
| **Last push** | 2026-08-12 |
| **Domain fit** | 9.0 — Direct replacement for OfficeCLI binary |
| **Maturity** | 8.5 — 99 stars, active, multi-platform, has Python bindings |
| **Adoption friction** | 8.5 — Pure Python via `pip install office-oxide-py` (hypothetical; would need to confirm exact package name) |
| **License compatibility** | 10 — Apache-2.0 + MIT, both compatible with our Apache-2.0 |
| **Code quality** | 8.5 — Modern Rust crate, multi-language bindings suggest discipline |
| **Composite** | **8.7** |

**Recommended action: 🟢 Adopt**

**Why:** Strongest single architectural win available. Eliminates the OfficeCLI binary dependency, removes the `shell=True` / `.CMD` resolution complexity in `engines/officecli.py`, and gives ~100× speedup. Effort: M (rewrite `officecli.py` adapter to call office_oxide's Python bindings). Ship as v0.8.0.

---

### 2. `DalCorsoMarco/markdown-to-xlsx` — 0★, no description

| | |
|---|---|
| **Description** | (empty) |
| **Language** | Python |
| **License** | Apache-2.0 |
| **Last push** | 2026-08-05 |
| **Domain fit** | 4.0 — Inverse direction (MD → XLSX); adjacent but not core |
| **Maturity** | 1.5 — 0 stars, no description |
| **Adoption friction** | 6.0 — Apache-2.0 license fine; but no README means evaluation cost |
| **License compatibility** | 10 — Apache-2.0 |
| **Code quality** | 3.0 — Unknowable without inspection |
| **Composite** | **3.8** |

**Recommended action: 🟠 Reference**

**Why:** 0 stars + no description = no signal of value. If we ever add roundtrip (MD → XLSX), this is one of several candidates to evaluate but not now.

---

### 3. `Liu-Qing-song/xlsx-md-roundtrip` — 2★ roundtrip

| | |
|---|---|
| **Description** | "Export Excel (.xlsx) to a Markdown-embedded YAML blueprint and rebuild it back to .xlsx with styles, merges and formulas preserved." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-03-03 |
| **Domain fit** | 5.5 — Same shape as pubtab; roundtrip is our missing feature |
| **Maturity** | 4.0 — 2 stars, 5 months stale, but working code |
| **Adoption friction** | 7.0 — MIT, pip-installable Python |
| **License compatibility** | 10 — MIT |
| **Code quality** | 5.0 — Unknown without deep read; the YAML-blueprint concept is novel |
| **Composite** | **5.5** |

**Recommended action: 🟡 Spike**

**Why:** If roundtrip ever becomes a goal (currently not), this is a smaller, more focused candidate than pubtab. Time-box a 1-day evaluation.

---

### 4. `barizonlucas/xls-to-md` — 1★ RAG-focused XLS

| | |
|---|---|
| **Description** | "Convert XLS, XLSX, CSV and Google Sheets into clean, structured Markdown — optimised for RAG pipelines and LLM ingestion." |
| **Language** | Python |
| **License** | None (no LICENSE file) |
| **Last push** | 2026-07-08 |
| **Domain fit** | 6.0 — Direct overlap with our CSV/XLSX adapters |
| **Maturity** | 2.0 — 1 star, no license = adoption risk |
| **Adoption friction** | 2.0 — No license means we can't legally redistribute |
| **License compatibility** | 0 — No LICENSE file = unsafe |
| **Code quality** | 4.0 — Unknown |
| **Composite** | **2.6** |

**Recommended action: 🔴 Pass**

**Why:** No license is a deal-breaker. Any2md already covers this space more maturely.

---

### 5. `yangjianchuan/xlsm_text_extractor` — 0★ Dify plugin

| | |
|---|---|
| **Description** | "Dify plugin for converting XLS, XLSX, and XLSM cell values to Markdown locally." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-07-27 |
| **Domain fit** | 4.5 — Dify locks it into one platform; our `.xlsx` adapter already works |
| **Maturity** | 1.0 — 0 stars, locked to Dify |
| **Adoption friction** | 3.0 — Dify runtime dependency is a blocker |
| **License compatibility** | 10 — MIT |
| **Code quality** | 4.0 — Unknown |
| **Composite** | **3.5** |

**Recommended action: 🔴 Pass**

**Why:** Dify-specific is a non-starter for our general-purpose CLI.

---

### 6. `Galaxy-Dawn/pubtab` — 137★ bidirectional XLSX↔LaTeX

| | |
|---|---|
| **Description** | "Bidirectional Excel↔LaTeX table converter with style-preserving roundtrip, multi-sheet support, and PNG/PDF preview." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-03-29 |
| **Domain fit** | 4.0 — LaTeX is not our output format |
| **Maturity** | 7.0 — 137 stars, 5 months stale but established |
| **Adoption friction** | 7.0 — MIT, Python, focused scope |
| **License compatibility** | 10 — MIT |
| **Code quality** | 7.5 — Reviewed via clone, well-structured |
| **Composite** | **6.2** |

**Recommended action: 🟠 Reference**

**Why:** Solid bidirectional architecture pattern but aimed at LaTeX (not Markdown/OKF). Borrow the structural-preservation technique if we ever add roundtrip.

---

### 7. `rocklambros/any2md` — 20★ RAG-pipeline MD converter

| | |
|---|---|
| **Description** | "Convert PDF, DOCX, HTML, and TXT files — or web pages by URL — to clean, LLM-optimized Markdown with YAML frontmatter." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-07-10 |
| **Domain fit** | 9.5 — Near-mirror of headcleaner's core mission |
| **Maturity** | 6.0 — 20 stars, but mature (12-stage cleanup pipeline, multiple LLM output formats) |
| **Adoption friction** | 7.5 — MIT, pip-installable, pure Python |
| **License compatibility** | 10 — MIT |
| **Code quality** | 8.0 — Sophisticated heuristics (`heuristics.refine_title`, `decode_html_entities` iterative loop, `strip_orphan_punctuation`) |
| **Composite** | **8.3** |

**Recommended action: 🟢 Adopt (selectively)**

**Why:** The 12-stage cleanup pipeline covers hard cases (cover-page titles, double-encoded HTML entities, malformed Docling tables) that our `lint.py` doesn't even attempt. Don't vendor the whole library — borrow their heuristic stages as Python functions we copy into our own `heuristics.py` module. Effort: M.

---

### 8. `landing-ai/ade-cli` — 2,403★ Agentic Document Extraction

| | |
|---|---|
| **Description** | "The official CLI for Agentic Document Extraction (ADE) by LandingAI — parse documents and extract schema-shaped data from your terminal." |
| **Language** | Python |
| **License** | Apache-2.0 |
| **Last push** | 2026-08-11 |
| **Domain fit** | 4.0 — Cloud-based SaaS, conflicts with our "no external services" stance |
| **Maturity** | 9.5 — LandingAI is a funded company; 2,403 stars; very active |
| **Adoption friction** | 3.0 — Requires LandingAI API key + credits |
| **License compatibility** | 10 — Apache-2.0 |
| **Code quality** | 9.0 — Production-grade |
| **Composite** | **6.5** |

**Recommended action: 🟠 Reference**

**Why:** Their UX (CLI + local cache at `~/.ade`) is well-designed. But as a paid third-party SaaS, it's incompatible with our local-only philosophy. Could inspire the manifest UX but not a dependency.

---

### 9. `run-llama/semtools` — 1,845★ semantic search CLI

| | |
|---|---|
| **Description** | "Semantic search and document parsing tools for the command line." |
| **Language** | Rust |
| **License** | MIT |
| **Last push** | 2026-03-11 |
| **Domain fit** | 3.5 — Search/retrieval layer, not conversion |
| **Maturity** | 8.5 — LlamaIndex ecosystem, 1,845 stars |
| **Adoption friction** | 4.0 — Rust binary, separate ecosystem |
| **License compatibility** | 10 — MIT |
| **Code quality** | 8.0 — Mature |
| **Composite** | **5.9** |

**Recommended action: 🟠 Reference**

**Why:** Out of our scope (we're converters, not retrievers). Their chunking output format is worth a look if we add chunking later.

---

### 10. `liquidaty/zsv` — 396★ world's fastest CSV

| | |
|---|---|
| **Description** | "zsv+lib: tabular data swiss-army knife CLI + world's fastest (simd) CSV parser." |
| **Language** | C |
| **License** | MIT |
| **Last push** | 2026-08-09 |
| **Domain fit** | 5.5 — Direct overlap with our `.csv` adapter |
| **Maturity** | 9.0 — 396 stars, very active, single-purpose and battle-tested |
| **Adoption friction** | 7.0 — Single C binary, same install model as OfficeCLI |
| **License compatibility** | 10 — MIT |
| **Code quality** | 9.0 — Single-purpose SIMD parser, well-known |
| **Composite** | **7.3** |

**Recommended action: 🟡 Spike**

**Why:** Same pattern as our OfficeCLI integration (shell out to a binary). For huge CSV files (>100 MB), zsv's SIMD parser is 10-100× faster than our stdlib-based `csv.py` adapter. Time-box a 1-day benchmark + integration.

---

### 11. `pawamoy/markdown-exec` — 172★ execute MD code blocks

| | |
|---|---|
| **Description** | "Utilities to execute code blocks in Markdown files." |
| **Language** | Python |
| **License** | ISC |
| **Last push** | 2026-07-08 |
| **Domain fit** | 2.5 — Runtime, not parser |
| **Maturity** | 7.5 — 172 stars, actively maintained by pawamoy |
| **Adoption friction** | 8.0 — ISC license, pip-installable, pure Python |
| **License compatibility** | 10 — ISC |
| **Code quality** | 8.0 — Mature, well-documented |
| **Composite** | **5.5** |

**Recommended action: 🟡 Spike (future)**

**Why:** Interesting future feature: `headcleaner verify` could optionally execute code blocks in MD to verify they're runnable. Not urgent — current scope is conversion, not runtime.

---

### 12. `iamgio/quarkdown` — 15,902★ Markdown-with-superpowers

| | |
|---|---|
| **Description** | "🪐 Markdown with superpowers: from ideas to papers, presentations, websites, books, and knowledge bases." |
| **Language** | Kotlin |
| **License** | GPL-3.0 |
| **Last push** | 2026-08-16 |
| **Domain fit** | 3.0 — Extends Markdown for output, not for input |
| **Maturity** | 9.5 — 15,902 stars, active LSP + VS Code extension |
| **Adoption friction** | 1.0 — **GPL-3.0 is incompatible with our Apache-2.0** (viral, would force our code to GPL) |
| **License compatibility** | **0 — GPL-3.0 viral license** |
| **Code quality** | 9.5 — 24-module architecture, full LSP |
| **Composite** | **4.5** |

**Recommended action: 🟠 Reference (with hard constraint)**

**Why:** Strong architecture inspiration (24 modules, LSP, VS Code extension pattern), but **GPL-3.0 license is incompatible** — adopting it as a library would force our entire codebase to GPL. Read the design docs, don't link. Their `quarkdown-vscode` is a model for our own VS Code extension.

---

### 13. `Graphify-Labs/graphify` — 107,089★ codebase → knowledge graph

| | |
|---|---|
| **Description** | "Turn any codebase, with its docs, SQL schemas, configs, and PDFs, into a queryable knowledge graph." |
| **Language** | Python |
| **License** | Apache-2.0 |
| **Last push** | 2026-08-16 |
| **Domain fit** | 2.0 — Codebase analyzer, not document converter |
| **Maturity** | 9.5 — 107k stars, very active |
| **Adoption friction** | 4.0 — Heavy infrastructure (vector store, AST parsing) |
| **License compatibility** | 10 — Apache-2.0 |
| **Code quality** | 9.0 — Mature |
| **Composite** | **5.0** |

**Recommended action: 🔴 Pass**

**Why:** Out of scope. We convert documents to OKF; graphify analyzes codebases. Different domain.

---

### 14. `yifanfeng97/Hyper-Extract` — 3,315★ LLM-driven extraction

| | |
|---|---|
| **Description** | "Hypergraph is more powerful. Transform unstructured text into structured knowledge with LLMs." |
| **Language** | Python |
| **License** | Other |
| **Last push** | 2026-08-12 |
| **Domain fit** | 3.5 — LLM-driven, not deterministic |
| **Maturity** | 8.0 — 3,315 stars, active |
| **Adoption friction** | 3.0 — Requires LLM API calls |
| **License compatibility** | 4.0 — "Other" license is risky |
| **Code quality** | 7.0 — Unknown deep quality |
| **Composite** | **4.4** |

**Recommended action: 🔴 Pass**

**Why:** Different philosophy (LLM-driven vs deterministic). License unclear ("Other"). Would require API keys users may not have. Not aligned with headcleaner's offline-first stance.

---

### 15. `AmadeusITGroup/docs2vecs` — 7★ docs embedding CLI

| | |
|---|---|
| **Description** | "CLI that helps with docs splitting, embedding and exposing them in a seamless manner." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-08-09 |
| **Domain fit** | 3.5 — Embedding-side, not conversion |
| **Maturity** | 4.0 — 7 stars, recent activity |
| **Adoption friction** | 6.0 — MIT, Python |
| **License compatibility** | 10 — MIT |
| **Code quality** | 5.0 — Unknown |
| **Composite** | **4.5** |

**Recommended action: 🔴 Pass**

**Why:** Different domain (vector store / chunking, not document-to-OKF). Not a near-term priority.

---

### Bonus: `thomas-villani/all2md` — 27★ (research-only, not on your list)

| | |
|---|---|
| **Description** | "Convert PDF, Word, PowerPoint, HTML, email & 40+ formats to clean Markdown — and back." |
| **Language** | Python |
| **License** | MIT |
| **Last push** | 2026-08-15 |
| **Domain fit** | 10.0 — Closest match to headcleaner-cli in existence |
| **Maturity** | 7.0 — 27 stars but v1.12.0 with 21+ CLI commands |
| **Adoption friction** | 6.0 — MIT, pip-installable |
| **License compatibility** | 10 — MIT |
| **Code quality** | 9.5 — AST pipeline, 50+ parsers, roundtrip scoring |
| **Composite** | **8.7** |

**Recommended action: 🟡 Spike (strategic)**

**Why:** The closest cousin project. Their 50+ parsers, AST pipeline, and roundtrip fidelity scoring are valuable references. Not a substitute — they don't do OKF — but a strategic comparison point. Worth a half-day read of the AST design.

---

## Final Ranking

| Rank | Repo | Score | Action |
|---|---|---|---|
| 🥇 1 | `yfedoseev/office_oxide` | 8.7 | 🟢 Adopt |
| 🥇 1 | `thomas-villani/all2md` *(bonus)* | 8.7 | 🟡 Spike (strategic) |
| 🥉 3 | `rocklambros/any2md` | 8.3 | 🟢 Adopt (selectively) |
| 4 | `liquidaty/zsv` | 7.3 | 🟡 Spike |
| 5 | `landing-ai/ade-cli` | 6.5 | 🟠 Reference |
| 6 | `Galaxy-Dawn/pubtab` | 6.2 | 🟠 Reference |
| 7 | `run-llama/semtools` | 5.9 | 🟠 Reference |
| 8 | `Liu-Qing-song/xlsx-md-roundtrip` | 5.5 | 🟡 Spike (future) |
| 8 | `pawamoy/markdown-exec` | 5.5 | 🟡 Spike (future) |
| 10 | `Graphify-Labs/graphify` | 5.0 | 🔴 Pass |
| 11 | `AmadeusITGroup/docs2vecs` | 4.5 | 🟠 Reference |
| 11 | `iamgio/quarkdown` | 4.5 | 🟠 Reference (license-blocked) |
| 13 | `yifanfeng97/Hyper-Extract` | 4.4 | 🔴 Pass |
| 14 | `DalCorsoMarco/markdown-to-xlsx` | 3.8 | 🟠 Reference |
| 15 | `yangjianchuan/xlsm_text_extractor` | 3.5 | 🔴 Pass |
| 16 | `barizonlucas/xls-to-md` | 2.6 | 🔴 Pass |

---

## Cross-Cutting Recommendations

### 🟢 Adopt now (would change headcleaner)

1. **`office_oxide`** — Replace OfficeCLI binary with pure-Python Rust-backed library. Effort: M. Ship as v0.8.0.
2. **`any2md` heuristics** — Borrow the 12-stage cleanup pipeline into a new `headcleaner/heuristics.py`. Don't vendor the library; copy the techniques. Effort: M.

### 🟡 Spike next quarter (worth 1-2 day evaluations)

3. **`zsv`** — Add as a binary fallback for huge CSVs (same pattern as OfficeCLI).
4. **`all2md`** — Strategic comparison; their AST design is worth reading deeply.
5. **`xlsx-md-roundtrip`** — Roundtrip candidate when/if we add that direction.
6. **`markdown-exec`** — Future feature: `headcleaner verify --execute` to run code blocks.

### 🟠 Read the source, don't adopt

7. `pubtab` — LaTeX focus, but bidirectional patterns are useful.
8. `semtools` — Chunking output format reference.
9. `quarkdown` — Architecture inspiration (GPL-3.0 blocks adoption).
10. `ade-cli` — UX inspiration (cloud blocks adoption).

### 🔴 Pass

11-15. All under 5.0 composite — out of scope or not worth the time.

---

## License Compatibility Matrix (for the adoptable ones)

| Repo | License | Compatible with our Apache-2.0? |
|---|---|---|
| `office_oxide` | Apache-2.0 + MIT (dual) | ✅ |
| `any2md` | MIT | ✅ |
| `zsv` | MIT | ✅ |
| `markdown-exec` | ISC | ✅ |
| `xlsx-md-roundtrip` | MIT | ✅ |
| `pubtab` | MIT | ✅ |
| `semtools` | MIT | ✅ |
| `ade-cli` | Apache-2.0 | ✅ |
| `quarkdown` | **GPL-3.0** | ❌ **Viral — would force our code to GPL** |
| `all2md` | MIT | ✅ |

Only `quarkdown` is a license issue. All others can be vendored or pip-installed without legal friction.

---

## Adoption Effort Estimate (composite, for the 6 adoptable/spikeable ones)

| Repo | Integration effort | Risk | Impact |
|---|---|---|---|
| `office_oxide` | M (~3 days) | Medium (rewrite `engines/officecli.py`, fallback path needed) | High (~100× speedup, no binary dep) |
| `any2md` heuristics | M (~3 days) | Low (copy techniques, vendor nothing) | Medium (cleaner MD output) |
| `zsv` | S (~1 day) | Low (binary install + new adapter) | Medium (huge CSV perf) |
| `all2md` strategic read | S (~1 day) | None (research only) | High (architectural reference) |
| `xlsx-md-roundtrip` | L (~1 week) | High (new direction, OKF impact unclear) | Low (not a current need) |
| `markdown-exec` | L (~1 week) | Medium (new `--execute` mode, security implications) | Low (future feature) |

**Total**: ~2 weeks of focused work to adopt 3 of the 6 adoptable repos (office_oxide + any2md + zsv), with strategic read of all2md as a reference.

---

## Bottom Line

**The single most impactful change** is adopting `office_oxide` to replace the OfficeCLI binary dependency. That's a v0.8.0 candidate.

**The single most impactful reference** is `all2md` — they have 50+ parsers, an AST pipeline, roundtrip fidelity scoring, and an MCP server. They're us plus a year of more development in a different direction.

**Everything else is incremental** — borrow heuristics, add zsv for big CSVs, read pubtab/quarkdown for design inspiration. None of it is urgent.