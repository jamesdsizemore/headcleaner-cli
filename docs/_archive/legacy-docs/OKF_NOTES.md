# OKF_NOTES

> What `headcleaner` emits for OKF v0.2. Reference: https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf

## OKF in one paragraph

A **knowledge bundle** is a directory of `.md` files, each with a YAML
frontmatter block delimited by `---` on its own line at the top of the
file and a closing `---` on its own line. Only one frontmatter key is
strictly required: `type`. Everything else (title, description, resource,
tags, trust fields, body) is producer freedom.

## What we emit (v0.1)

For every supported source file we write **one OKF concept** at:

```
<output>/okf/<mirrored-source-relpath-without-ext>.md
```

The frontmatter always contains:

```yaml
---
type: Document              # required by OKF §4.1
title: <derived>            # OKF §4.1 recommended
description: <one line>     # OKF §4.1 recommended
resource: file:///abs/path  # OKF §4.1 recommended
tags: [<from path>]         # OKF §4.1 recommended

# OKF v0.2 trust family (§5)
status: unverified          # §5.2 — lifecycle
stale_after: 2027-02-15     # §5.2 — freshness (+180d)

# OKF v0.2 provenance (§5.1)
sources:
  - uri: file:///abs/path
    kind: file
    sha256: 8c2f...         # SHA-256 of source bytes

# OKF v0.2 actor convention (§7)
generated: human:james@host # <producer>/<version>; for us: $USER + this CLI version
verified: human:pending     # never auto-verify; this is an honest default
---

# <title>

<Markdown body derived from source>
```

## Field-by-field

### `type` (required, OKF §4.1)

Every concept carries `type: Document`. This is the only field OKF
mandates. Other values are allowed (`Playbook`, `Metric`, `Reference`,
`Attested Computation`, etc.) — we picked `Document` because it's the
most generic for auto-conversion.

Future versions may infer a more specific type based on the source file
(DOCX → `Reference`, XLSX → `Metric`, etc.). See ENHANCEMENTS.md #7.

### `title` (recommended)

Best-effort, in priority order:
1. The first `<h1>` in the source (DOCX/HTML)
2. The PDF document metadata title (`pdfplumber.metadata.title`)
3. The source filename without extension

### `description` (recommended)

We auto-generate: `Document derived from <relpath> via <engine>.`
This is intentionally bland. Users can edit the description after the
fact to add real meaning.

### `resource` (recommended)

A `file://` URI to the source file's absolute path. On Windows:
`file:///C:/Users/james/inbox/q3.pdf`. On Unix: `file:///home/james/inbox/q3.pdf`.

### `tags` (recommended)

We auto-derive from the source path:
- Every directory segment of the relpath (lowercased)
- The source extension (lowercased, no dot)

Example: `inbox/finance/q3.pdf` → `tags: [finance, pdf]`.

### `status` (OKF v0.2 §5.2)

Always `unverified` for auto-conversion. Downstream consumers can
override this once they've manually reviewed the file.

### `stale_after` (OKF v0.2 §5.2)

`today + 180 days` in `YYYY-MM-DD` format. After this date, downstream
consumers should re-verify the concept (e.g., re-extract and diff).

### `sources[]` (OKF v0.2 §5.1)

A list of one entry (per-file conversion):

```yaml
sources:
  - uri: file:///abs/path
    kind: file            # always "file" for v0.1; future: "url", "api", etc.
    sha256: <64-char hex> # SHA-256 of the source bytes
```

The `sha256` lets consumers detect when a source file has changed and
needs re-conversion.

### `generated` (OKF v0.2 §7)

Convention: `<producer>/<version>`. We emit:

```
human:<user>@<hostname>
```

- `<user>` = `$USER` env var (Unix) or `$USERNAME` (Windows); falls
  back to `"unknown"` if neither is set.
- `<hostname>` = `socket.gethostname()`, stripped of domain.

Example: `generated: human:james@ThreeKings-Main`.

### `verified` (OKF v0.2 §5.3)

Always `human:pending` for auto-conversion. NEVER `human:reviewed` or
`machine-confirmed` — those require actual review, which auto-conversion
is not.

## Directory indices (OKF §8)

At every directory level under the OKF bundle that contains ≥1 concept,
we auto-generate an `index.md`:

```markdown
# inbox

## Concepts

- [Q3 Financial Summary](q3.pdf.md) — `Document` — unverified
- [Meeting Notes](notes.md) — `Document` — unverified
```

Indices let consumers browse the bundle hierarchically without loading
every file. They are regenerated on every `headcleaner convert` run.

## Update history (OKF §9)

Optionally, we can append a `log.md` at the bundle root with one
entry per run. v0.1 doesn't generate this automatically — tracked in
ENHANCEMENTS.md #19.

## What we deliberately do NOT do

- We never set `verified: human:reviewed` or `verified: machine-confirmed`.
  Auto-conversion is not review.
- We never invent `sources` entries pointing to systems we did not
  actually query. All sources are file paths we read.
- We never strip the `human:pending` placeholder — the human can grep
  it later to find unverified concepts.

## OKF validity check

We ship `headcleaner lint` to validate every emitted concept. The
linter applies these rules (see `src/headcleaner/lint.py`):

| Rule | Severity | What it checks |
|---|---|---|
| `okf/frontmatter` | error | YAML frontmatter parses cleanly |
| `okf/type-required` | error | `type` is present and non-empty |
| `okf/type-length` | warning | `type` is shorter than 60 chars |
| `okf/resource-uri` | warning | `resource` starts with `file://` |
| `okf/sources-empty` | error | `sources` is a non-empty list |
| `okf/sources-shape` | error | every `sources[i]` is a dict |
| `okf/sources-uri` | warning | every `sources[i]` has a `uri` |
| `okf/sources-sha256` | error | every `sources[i].sha256` is a 64-char hex string |
| `okf/status-missing` | warning | `status` is set |
| `okf/verified-missing` | warning | `verified` is set |
| `okf/body-empty` | error | concept body is non-empty |

Run: `headcleaner lint <output-dir>` (see `docs/USAGE.md` §7).

## Future OKF work

- v0.2 `Attested Computation` type (§10) — when an OKF concept can
  be re-derived by running a deterministic computation. We don't emit
  these in v0.1 because plain document extraction isn't a
  computation. Out of scope.
- Cross-concept links — OKF encourages markdown links between
  concepts. v0.1 emits standalone concepts; v1.0 will infer links
  (see ENHANCEMENTS.md #8).
- Producer-policy overrides — let orgs require `verified: human:reviewed`
  before allowing a concept into a published bundle. ENHANCEMENTS.md #9.
- `log.md` (OKF §9) — per-run update history. ENHANCEMENTS.md #19.
