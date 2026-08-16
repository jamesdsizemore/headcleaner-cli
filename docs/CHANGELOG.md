# Changelog

All notable changes to headcleaner are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/).

## [0.6.0] — 2026-08-16 (Batch 5)

Final Batch 1 leftovers + the last planned format-adapter items. All
44 + 5 = 49 enhancements from the master plan are now shipped.

### Added

- **`.epub` adapter** (Enhancement #7) — `src/headcleaner/engines/epub.py`.
  Uses `ebooklib` to enumerate spine items + render each XHTML as MD
  via a small BeautifulSoup helper. Fallback walks the raw zip.
- **`.rtf` adapter** (Enhancement #8) — `src/headcleaner/engines/rtf.py`.
  Uses `striprtf` for the main path; regex fallback strips control
  words if the dep is unavailable.
- **ODF adapter** (Enhancement #9) — `src/headcleaner/engines/odf.py`.
  Handles `.odt` (paragraphs), `.ods` (GFM tables), and `.odp`
  (per-slide text) via `odfpy`. Raw-XML fallback handles corrupt
  files.
- **`.msg` adapter** (Enhancement #10) — `src/headcleaner/engines/msg.py`.
  Uses `extract-msg` to read Outlook headers + body + attachments.
  Clear "extract-msg not installed" fallback if the dep is missing.
- **`headcleaner review` TUI** (Enhancement #3) —
  `src/headcleaner/review.py` + `headcleaner review BUNDLE` subcommand.
  Walks every concept with `verified: human:pending` and lets a human
  approve (→ `human:reviewed`), reject (→ `human:rejected`), or skip.
  Textual TUI with keybindings (`a`/`r`/`s`/`n`/`p`/`q`) + plain REPL
  fallback for headless environments.

### Dependencies added

- `ebooklib>=0.18`
- `striprtf>=0.0.26`
- `odfpy>=1.4.1`

### Tests

113 passing in ~8s (13 new across `tests/test_batch5_adapters.py` +
`tests/test_batch5_review.py`).

### CLI surface at v0.6.0

```
headcleaner convert    IN_DIR [--format md|okf|both] [-o DIR] [-i GLOB]
                       [-e GLOB] [-j N] [--no-cache] [--officecli-timeout N]
                       [--obsidian-compat] [--enriched-index] [--write-log]
                       [--write-bundle-manifest] [--crossref]
                       [--policy FILE] [--git-commit] [--git-commit-message MSG]
                       [--git-commit-verify] [--dry-run] [--json]
                       [--theme neon|light|dark|mono] [--tui|--no-tui]
                       [--no-continue-on-error] [--no-okf-index] [--ocr]
headcleaner watch      IN_DIR [...] [--webhook-url URL] [--debounce-ms N]
headcleaner review     BUNDLE             # NEW: human sign-off TUI
headcleaner attest     BUNDLE_DIR
headcleaner glob       DIR
headcleaner lint       DIR [--fix] [--strict]
headcleaner agents     [stdout]
headcleaner templates
```

---

## [0.5.0] — 2026-08-16 (Batch 4)

Final batch of the [ENHANCEMENTS.md](ENHANCEMENTS.md) plan shipped.
14 of 14 items complete — the standing goal.

### Added

- **`log.md` (OKF §9)** (Enhancement #37) — `okf_index.append_log_entry()`
  appends a dated, per-engine summary after every run. Idempotent.
  CLI: `--write-log`.
- **Enriched `index.md`** (Enhancement #38) — descriptions + word counts
  on every concept bullet. CLI: `--enriched-index`.
- **Bundle-level `manifest.json`** (Enhancement #39) — aggregates engine
  counts and recent runs across invocations into a single
  `<bundle>/bundle.manifest.json`. CLI: `--write-bundle-manifest`.
- **Cross-concept link inference** (Enhancement #34) — second-pass
  rewrites mentions of other concepts' titles as markdown links.
  Idempotent. CLI: `--crossref`.
- **Pluggable trust policy** (Enhancement #35) — load a `policy.toml`
  that gates the run on required trust-family fields. CLI: `--policy FILE`.
- **Git-backed bundle** (Enhancement #32) — `git add` + commit after a
  successful run. CLI: `--git-commit` + `--git-commit-message` +
  `--git-commit-verify`.
- **TUI theme switching** (Enhancement #40) — 4 palettes (neon, light,
  dark, mono) via `theme.set_theme()`. CLI: `--theme`.
- **Per-engine sub-bars** (Enhancement #41) — TUI gets a second
  progress row that updates via `on_engine_progress(engine, cur, total)`.
  Currently used by the PDF OCR path; other engines can opt in.
- **`--dry-run`** (Enhancement #42) — show what would be converted
  without writing any files. Manifest.json is also skipped.
- **`--json` output** (Enhancement #43) — emit one JSON line per event
  on stdout (`start` / `file` / `finish`) for piping into `jq` or log
  aggregators.
- **Notion import stub** (Enhancement #31) — `src/headcleaner/notion.py`
  + planned `headcleaner notion-import` command. Detect-export works;
  full reverse-import ships in v0.6.
- **Attested Computations stub** (Enhancement #36) — `headcleaner attest`
  builds a per-concept SHA-256 manifest. Merkle root + ed25519
  signature land in v0.6 with proper cryptography deps.
- **VS Code extension stub** (Enhancement #33) — `vscode-extension/`
  with `package.json` + `extension.ts` skeleton. Two commands
  (`headcleaner.lintBundle`, `headcleaner.attest`) shell out to the CLI.
- **Glob REPL stub** (Enhancement #44) — `headcleaner glob` is a thin
  wrapper around `glob_repl.launch_repl()`. Full Textual UI ships
  in v0.6.

### Module additions

- `src/headcleaner/crossref.py` — `linkify_bundle()`.
- `src/headcleaner/policy.py` — `Policy.load()` + `evaluate()` + `PolicyFinding`.
- `src/headcleaner/git_commit.py` — `git_commit()` + `find_repo_root()`.
- `src/headcleaner/bundle_manifest.py` — `write_bundle_manifest()`.
- `src/headcleaner/jsonlog.py` — `emit_json_event()`.
- `src/headcleaner/notion.py` — `detect_export()` + `import_notion_export()`.
- `src/headcleaner/attest.py` — `build_attestation()` + `write_attestation()` + `canonical_hash()`.
- `src/headcleaner/glob_repl.py` — `count_matches()` + `launch_repl()`.
- `src/headcleaner/emit/okf_index.py` — added `_enriched_index_md()`,
  `append_log_entry()`, and a `generate(enriched, write_log, record)`
  signature.

### Tests

100 passing in ~8s (20 new across `test_batch4.py` + `test_batch4_skeletons.py`).

### CLI surface at v0.5.0

```
headcleaner convert  IN_DIR [--format md|okf|both] [-o DIR] [-i GLOB]
                    [-e GLOB] [-j N] [--no-cache] [--officecli-timeout N]
                    [--obsidian-compat] [--enriched-index] [--write-log]
                    [--write-bundle-manifest] [--crossref]
                    [--policy FILE] [--git-commit] [--git-commit-message MSG]
                    [--git-commit-verify] [--dry-run] [--json]
                    [--theme neon|light|dark|mono] [--tui|--no-tui]
                    [--no-continue-on-error] [--no-okf-index] [--ocr]
headcleaner watch    IN_DIR [...] [--webhook-url URL] [--debounce-ms N]
headcleaner attest   BUNDLE_DIR
headcleaner glob     DIR
headcleaner lint     DIR [--fix] [--strict]
headcleaner agents   [stdout]
headcleaner templates
```

---

## [0.4.0] — 2026-08-16 (Batch 3)

Third batch of the [ENHANCEMENTS.md](ENHANCEMENTS.md) plan shipped.
Live mode + distribution + ecosystem.

### Added

- **`headcleaner watch`** (Enhancement #21) — file-system watcher.
  Uses `watchfiles` (already a dep of textual). Re-runs the pipeline
  on every change with `--debounce-ms 500` to avoid thrashing on bulk
  copies. Press Ctrl+C to stop. Raises `WatchfilesMissingError` with a
  clear install hint when the Rust extension isn't available.
- **`headcleaner serve`** (Enhancement #22) — **skeleton only**. Module
  `src/headcleaner/serve.py` ships with the planned route map and
  commented-out FastAPI implementation. Full implementation tracked
  for Batch 4 (needs FastAPI as a dep).
- **Webhook integration** (Enhancement #23) — `src/headcleaner/webhook.py`
  POSTs the run manifest as JSON to any URL. Used by
  `headcleaner watch --webhook-url <URL>` to fire notifications on
  every re-run. Supports Slack, Discord, ntfy, custom endpoints.
- **Homebrew formula** (Enhancement #24) — `packaging/homebrew/headcleaner.rb`.
  Ready to drop into a `homebrew-headcleaner` tap repo.
- **PyPI publish pipeline** (Enhancement #25) — `.github/workflows/publish.yml`
  with OIDC trusted publishing (no API tokens). Tests on push/PR,
  publishes to TestPyPI on `-test` tags, to PyPI on stable tags.
  Plus full PyPI metadata in `pyproject.toml` (keywords, classifiers,
  author email).
- **Docker image** (Enhancement #26) — multi-stage `Dockerfile` with
  Python 3.12 + uv builder + tesseract for OCR. `.github/workflows/docker.yml`
  builds and pushes to `ghcr.io/local/headcleaner` on every tag.
- **Winget / Scoop / Chocolatey manifests** (Enhancement #27) —
  `packaging/windows/headcleaner.yaml`, `headcleaner.scoop.json`,
  `headcleaner.nuspec`. Ready to submit to upstream repositories.
- **PyInstaller spec** (Enhancement #28) —
  `packaging/pyinstaller/headcleaner.spec` for building a single-file
  static binary. ~30 MB compressed, no Python required at runtime.
- **Public GitHub release checklist** (Enhancement #29) — `RELEASE.md`
  with the 10-step release workflow including OIDC trusted publisher
  setup, all four package-manager PR submissions, smoke tests.
- **Obsidian vault sync** (Enhancement #30) — `--obsidian-compat` flag
  adds flat fields (`source`, `sha256`, `generated_by`, `verified_by`,
  `stale_on`) to OKF frontmatter. Obsidian renders these as clickable
  properties. Original OKF fields stay intact.

### Engine coverage at v0.4.0

Same as v0.3.0 (10 adapters + 1 error-path shim). Distribution + integration
features are what changed in this batch.

### Pipeline additions

- `src/headcleaner/watch.py` — `watch_directory()` with debounce + on_change
  + on_run_complete callbacks.
- `src/headcleaner/webhook.py` — `build_payload()` + `post_webhook()`.
- `src/headcleaner/obsidian.py` — flat-field helpers; also wired into
  `CanonicalDoc.to_okf_frontmatter(obsidian_compat=True)`.
- `pyproject.toml`: `watchfiles` promoted to a direct dep; full PyPI
  metadata (keywords, classifiers, author email).

### Tests

80 passing in ~8s (7 new in `tests/test_batch3a.py` covering watch,
webhook, Obsidian compat).

### Deferred from this batch

- #3 review TUI — still pending (Batch 4 UX)
- #7 epub — needs `ebooklib` dep (Batch 4)
- #8 rtf — needs `striprtf` dep (Batch 4)
- #9 odf — needs `odfpy` dep (Batch 4)
- #10 msg — `extract-msg` already in deps (Batch 4)
- Full #22 serve implementation — needs FastAPI dep (Batch 4)

---

## [0.3.0] — 2026-08-16 (Batch 2)

Second batch of the [ENHANCEMENTS.md](ENHANCEMENTS.md) plan shipped.
Performance, reliability, and the last of the easy format wins.

### Added

- **`.eml` adapter** (Enhancement #11) — RFC 5322 email files. Headers
  (From, To, Subject, Date, Message-ID) rendered as a bullet list; the
  preferred body is `text/plain` (fenced) or `text/html` (markdownified);
  attachments listed by filename + MIME type + size.
- **`.pst` adapter stub** (Enhancement #12) — best-effort. Reports
  the item count via `libpff-python` (binary wheels: Windows x64 +
  macOS arm64); full message extraction deferred. If the library is
  not installed, emits a clear `AdapterError` with install/convert
  instructions.
- **Legacy Office clear-error path** (Enhancement #13) — `.doc`,
  `.xls`, `.ppt` no longer silently skip with "no adapter". The
  `legacy_office` adapter surfaces a precise message: "convert with
  `libreoffice --convert-to docx` first, then re-run".
- **`--officecli-timeout <seconds>`** (Enhancement #18) — configurable
  per-subprocess timeout, default 60s.
- **Encrypted PDF error** (Enhancement #19) — detects `/Encrypt`
  metadata or `password` exceptions from pdfplumber and surfaces an
  actionable message: "decrypt with `qpdf --decrypt ...` then re-run".
- **Parallel pipeline `--jobs N`** (Enhancement #14) — process files
  in a `ProcessPoolExecutor` with N workers (default 1 = sequential).
  Significant speedup on folders dominated by OfficeCLI subprocess
  overhead. Output ordering preserved via per-file progress hooks.
- **Streaming manifest** (Enhancement #15) — `<output>/manifest.jsonl`
  is appended to after every file, enabling tail -f audit and crash
  recovery. The final `manifest.json` is built at the end of the run.
- **Idempotent SHA-256 cache** (Enhancement #16) — files whose
  source SHA-256 matches a prior run's `manifest.json` are skipped.
  Disable with `--no-cache`. The walker now also skips the output
  directory itself, so the cache can't be invalidated by headcleaner's
  own writes.
- **Streaming PDF docs** (Enhancement #20) — pdfplumber already streams
  per page; documented the memory profile in `docs/FORMAT_MATRIX.md`
  and `docs/USER_GUIDE.md`.

### Engine coverage at v0.3.0

| Format | Engine | Library |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | officecli | @officecli/officecli |
| `.pdf` | pdf | pdfplumber |
| `.html`, `.htm` | html | beautifulsoup4 + markdownify |
| `.txt` | txt | chardet |
| `.md`, `.markdown` | md | stdlib |
| `.csv`, `.tsv` | csv | stdlib `csv` |
| `.json` | json | stdlib `json` |
| `.eml` | eml | stdlib `email` |
| `.pst` (best-effort) | pst | libpff-python |
| `.doc`, `.xls`, `.ppt` | legacy_office | (error path; no adapter) |

10 active adapters + 1 error-path shim. 72 pytest tests passing in ~7s.

### Pipeline architecture changes

- `walk()` gained a `skip_root` parameter (defaults to the output dir).
- `run.run_pipeline()` now branches between `_process_sequential` (default)
  and `_process_parallel` (when `jobs > 1`).
- `RunOptions` gained `jobs: int = 1` and `use_cache: bool = True`.
- `_load_cache()` reads the previous `manifest.json`; `_save_cache_jsonl()`
  appends after every file.

### Deferred from this batch

- #3 review TUI — still pending (Batch 4 UX)
- #7 epub — needs `ebooklib` dep (Batch 4)
- #8 rtf — needs `striprtf` dep (Batch 4)
- #9 odf — needs `odfpy` dep (Batch 4)
- #10 msg — `extract-msg` already in deps (Batch 4)

---

## [0.2.0] — 2026-08-16 (Batch 1)

First batch of the [ENHANCEMENTS.md](ENHANCEMENTS.md) plan shipped.

### Added

- **`headcleaner lint --fix`** (Enhancement #2)
  - Auto-repair safe OKF structural issues
  - Writes repaired files to `<DIR>.fixed/` (never overwrites source)
  - Adds missing `status`, `verified`, `stale_after`, `resource` (derived
    from `sources[0].uri` when present)
  - Refuses to touch `index.md`, files without frontmatter, files
    without a `type` key, or anything in the body
- **`.md` / `.markdown` adapter** (Enhancement #4)
- **`.csv` / `.tsv` adapter** (Enhancement #5) — Sniffer-detected dialect
- **`.json` adapter** (Enhancement #6) — pretty-printed fenced block +
  bulleted summary for flat objects
- New pytest tests for all of the above (15 new tests)

### Engine coverage at v0.2.0

| Format | Engine | Library |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | officecli | @officecli/officecli |
| `.pdf` | pdf | pdfplumber |
| `.html`, `.htm` | html | beautifulsoup4 + markdownify |
| `.txt` | txt | chardet |
| `.md`, `.markdown` | md | stdlib |
| `.csv`, `.tsv` | csv | stdlib `csv` |
| `.json` | json | stdlib `json` |

9 active adapters, 58 pytest tests passing in ~5s.

### Docs

- README updated with new format table + `--fix` line in CLI reference
- docs/FORMAT_MATRIX.md updated with .md/.csv/.json rows in v0.1.0
  shipped section
- docs/ENHANCEMENTS.md marks #1, #2, #4, #5, #6 as ✅ shipped

### Deferred from this batch

- #3 review TUI — needs a separate Textual pass (Batch 4 UX work)
- #7 epub — needs `ebooklib` dep + chapter iteration (Batch 1 partial)
- #8 rtf — `striprtf` dep (Batch 1 partial)
- #9 odf — `odfpy` dep + ODP parsing (Batch 1 partial)
- #10 msg — `extract-msg` already in deps; minor work (Batch 1 partial)
- #11 eml — stdlib email; minor work (Batch 1 partial)

These will be completed in Batch 2 alongside the perf/reliability work.

---

## [0.1.0] — 2026-08-16

First public release. Rebranded from `doc-ingest` to `headcleaner`.

### Added

- **Conversion pipeline** (`headcleaner convert`)
  - Walks a folder recursively, skipping hidden files and VCS internals
  - Dispatches by extension to one of four active adapters:
    - `officecli` — DOCX, XLSX, PPTX (via the OfficeCLI binary)
    - `pdf` — PDF text-layer extraction via pdfplumber (--ocr flag for Tesseract)
    - `html` — HTML/HTM via BeautifulSoup + markdownify
    - `txt` — TXT via chardet (encoding auto-detected)
  - Emits `_md/` (plain Markdown) and/or `okf/` (OKF v0.2 bundle) plus `manifest.json`
  - Auto-generates `okf/index.md` per directory (OKF §8 progressive disclosure)
- **OKF v0.2 trust family** with honest defaults:
  - `status: unverified`
  - `verified: human:pending`  (never auto-claims review)
  - `generated: human:<user>@<host>` (OKF §7 actor convention)
  - `stale_after: <today + 180d>`
  - `sources: [{uri: file://..., sha256: ...}]` (OKF v0.2 §5.1 provenance)
- **TUI** (`headcleaner convert --tui`, default when stdout is a TTY)
  - omp-inspired visual language (rounded box-drawing panels, powerline separators)
  - Neon palette: cyan primary, pink active, purple info
  - Lightning-bolt jar (⚡) brand mark in header + segmented footer
  - Live progress bar, per-file engine attribution, animated spinner
- **Plain mode** (`headcleaner convert --no-tui`)
  - One progress line per file on stderr, exit code 0/1
  - Designed for CI / pipes / scripts
- **Post-conversion linter** (`headcleaner lint <DIR>`)
  - OKF structural rules: required `type`, valid `resource` URI, valid SHA-256, sources[] shape
  - Markdown body rules: orphan code fences, heading hierarchy, line length
  - `--strict` treats warnings as errors; exit code 1 on any error
- **Other subcommands**:
  - `headcleaner templates` — list supported formats
  - `headcleaner agents` — show engine install status
- **Install paths** (documented in `docs/INSTALL.md`):
  - `curl | bash` and `irm | iex` one-liners
  - `uv tool install headcleaner`
  - `pipx install headcleaner`
  - `pip install --user`
  - From source
- **CI** — GitHub Actions matrix on Python 3.12 + 3.13, OfficeCLI installed
  via npm, full pytest on push and PR.

### Engine coverage at v0.1.0

| Format | Engine | Library |
|---|---|---|
| `.docx`, `.xlsx`, `.pptx` | officecli | @officecli/officecli (binary) |
| `.pdf` | pdf | pdfplumber |
| `.html`, `.htm` | html | beautifulsoup4 + markdownify |
| `.txt` | txt | chardet |

### Tests

43 pytest tests covering walker, router, normalize, emitters, full
pipeline, and linter rules. Suite runs in ~5 seconds.

### Known gaps (planned for v1.0)

See `docs/ENHANCEMENTS.md` for the full 25+ item roadmap. Highlights:

- `.md`, `.csv`, `.json`, `.epub`, `.rtf`, `.odt`/`.ods`/`.odp`,
  `.eml`, `.msg`, `.pst`, legacy `.doc`/`.xls`/`.ppt`
- `headcleaner watch` for live folder monitoring
- `headcleaner serve` for live OKF bundle browser
- Pluggable trust policy (so orgs can require `verified: human:reviewed`)
- Cross-concept link inference
- Homebrew formula

### Changed

- Renamed project from `doc-ingest` to `headcleaner`. The Python package
  is now `headcleaner`; the console script is `headcleaner`; the
  linter is `headcleaner-lint` (also reachable as `headcleaner lint`).

### Removed

- The old `doc-ingest` console script. Users upgrading should
  uninstall the old package first:
  ```
  uv tool uninstall doc-ingest
  uv tool install headcleaner
  ```

---

## Pre-history

Versions ≤ 0.0.x lived under the `doc-ingest` name in
`~/developer/doc-ingest`. They are no longer supported. See git history
of that repo (now removed; this project is its successor).
