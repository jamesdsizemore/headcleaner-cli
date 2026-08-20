# Frequently asked questions

## General

### What is headcleaner for?

Converting folders of mixed-format documents (DOCX, PDF, HTML, TXT, …) into
either:
- **Plain Markdown** with a lightweight YAML frontmatter, or
- **OKF v0.2 bundles** — directory hierarchies of `.md` files with the
  full OKF trust family pre-filled, plus auto-generated `index.md` files
  for progressive disclosure.

It's a folder walker → engine dispatcher → Markdown / OKF emitter. No
LLM calls, no network, no database.

### Why "headcleaner"?

The lightning-bolt jar. Think of it as a "brain-cleaning" tool: you point
it at a messy folder of mixed-format documents, and it walks out with a
clean, normalized, searchable bundle.

### What does it NOT do?

- It does not call any LLM. No summarization, no rewriting.
- It does not store anything in a database. All output is plain files.
- It does not run a server or a daemon (yet — see `docs/ENHANCEMENTS.md`
  for the planned `headcleaner watch` and `serve` modes).

## OKF

### What is OKF?

OKF = Open Knowledge Format, v0.2. Markdown + YAML frontmatter in a
directory hierarchy. Required frontmatter: `type`. Recommended:
`title`, `description`, `resource`, `tags`. v0.2 adds: `sources`,
`verified`, `status`, `stale_after`. See
`docs/OKF_NOTES.md` for the full contract this CLI emits.

### Why use OKF instead of just Markdown?

OKF *is* Markdown + frontmatter. The benefit is:
- Frontmatter is required, not optional
- Trust fields are first-class (`status`, `verified`, `sources`)
- Directory layout implies concept hierarchy
- Auto-generated `index.md` files at every level enable progressive
  disclosure (a reader can browse the bundle without loading everything)

### How do I view an OKF bundle?

Any tool that consumes markdown + YAML frontmatter works:
- **Obsidian** — drop the `okf/` directory in your vault
- **Notion** — import via "Markdown & CSV"
- **MkDocs / Hugo / Jekyll** — `okf/` becomes your `docs/` source tree
- **VS Code** — open `okf/` as a workspace; the markdown preview handles frontmatter
- **Plain `cat`** — every concept is a valid Markdown file

### Why does `verified` always say `human:pending`?

Auto-conversion is not review. Setting `verified: human:reviewed` after
running an automated tool would be dishonest — a human never actually
looked at the file. We never auto-claim review. To mark a concept as
human-reviewed, edit the file and set `verified: human:<your-id>`.

You can grep `human:pending` to find concepts that need review:

```bash
grep -l "verified: human:pending" okf/**/*.md
```

## Engines

### Why does `headcleaner agents` say `officecli` is missing?

OfficeCLI is a separate npm package (`@officecli/officecli`). We shell
out to it for DOCX/XLSX/PPTX. Install once:

```bash
npm install -g @officecli/officecli
```

After install, `officecli --version` should print `1.0.x` or newer.

### Can I use headcleaner without OfficeCLI?

Yes. Without OfficeCLI installed, headcleaner silently skips DOCX/XLSX/PPTX
files (with a note in the manifest). All other formats still work.

### Why pdfplumber and not Tesseract by default?

OCR is slow (~1 sec/page) and error-prone. Most PDFs have a text layer
that pdfplumber can extract in milliseconds. Use `--ocr` only for
scanned PDFs.

### What about `.doc` / `.xls` / `.ppt` (legacy binary formats)?

Not supported in v0.1. The Office binary formats (pre-2007) are
distinct from the OOXML formats and require a different parser.
See `docs/ENHANCEMENTS.md` #18 for the plan to support them via
`libreoffice --convert-to docx` as a preprocessing step.

## Installation

### Should I use uv, pipx, or pip?

We recommend `uv tool install`. It's the fastest, it manages venvs for
you, and `uv tool upgrade headcleaner` is a one-liner.

`pipx` is a fine alternative if you're already comfortable with it.

`pip install --user` works but you have to manage the venv yourself.

### How do I upgrade?

```bash
uv tool upgrade headcleaner
```

### How do I uninstall?

```bash
uv tool uninstall headcleaner
```

## Output

### Can I customize the frontmatter?

Not via CLI flags in v0.1. Edit the resulting `.md` files directly, or
fork `src/headcleaner/normalize.py` and adjust `to_okf_frontmatter()`
and `to_md_frontmatter()`.

### Can I get just Markdown or just OKF?

Yes — `--format md` or `--format okf`. Default is `--format both`.

### The OKF index.md wasn't generated. Why?

Auto-generated only when the directory contains ≥1 concept. Use
`--no-okf-index` to opt out entirely.

### Can I run headcleaner on a network share or cloud-synced folder?

Yes. The walker is filesystem-agnostic. Just point `--input` at the
mounted path. Note that `source_sha256` will change if the source
file is modified between runs.

## CI

### Does headcleaner work in CI?

Yes. `headcleaner convert --no-tui` exits 0 on full success and 1 on
any failure. `headcleaner lint <DIR>` exits 1 on any linter error.

```yaml
# .github/workflows/example.yml
- run: headcleaner convert ./inbox --format both --output ./out --no-tui
- run: headcleaner lint ./out --strict
```

### Why is the TUI off by default in CI?

CI runners don't have a TTY, so headcleaner auto-detects and uses plain
mode. You can force TUI on a runner with `script -c "headcleaner ..."
typescript.log` if you want a recorded session.

## Performance

### How fast is it?

Roughly:
- DOCX: ~200 ms each (OfficeCLI subprocess overhead dominates)
- PDF: ~50 ms per page for text-layer
- HTML/TXT: ~10 ms each

A 100-file mixed folder takes ~10-20 seconds on commodity hardware.

### Can I parallelize?

Not in v0.1. The pipeline is single-threaded. OCR is CPU-bound and
would benefit from a worker pool; that's ENHANCEMENTS.md #11.

## Project

### Where is the source code?

`~/developer/headcleaner-cli/` (this repo).

### Is there a public mirror?

Not yet. See `docs/ENHANCEMENTS.md` #24 for the GitHub publish plan.

### What's the license?

Apache-2.0.
