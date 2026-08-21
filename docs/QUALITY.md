# Quality dashboard (Contract 3.8)

HeadCleaner renders a public, self-contained benchmark dashboard for each
quality run. The dashboard is built only from public, attributed fixtures and
documents every metric delta against the declared baseline.

## Inputs

The dashboard renderer (`headcleaner benchmark-dashboard`) requires:

1. **`tests/quality/baseline.json`** — the pinned baseline of per-fixture
   metrics. Must declare `schema_version`, `tool_version`, `fixtures[]`
   (each with `fixture_id` and `metrics`), and a `summary` block.
2. **A current benchmark result JSON** — supplied as the positional
   `CURRENT` argument; contains a `results[]` list with per-fixture
   `metrics`.
3. **`tests/quality/fixtures/ATTRIBUTION.md`** — must mention `author`,
   `license`, and `source` so the dashboard always carries attribution.
4. **`tests/quality/fixtures/`** — the public fixtures root. The renderer
   refuses to render if a fixture is marked `non_public: true`.

## Outputs

- **`--format json`** — deterministic JSON payload with per-metric signed
  deltas, baseline schema, tool version, summary, attribution excerpt, and
  declared `known_limitations`.
- **`--format html`** — single-file, self-contained HTML dashboard with no
  external scripts, stylesheets, or analytics calls. Every fixture label
  is HTML-escaped.

## Invariants

- **Deterministic.** No timestamps or random ordering; two consecutive
  renders of the same inputs are byte-identical.
- **Self-contained.** No network calls; no remote fonts; no analytics.
- **Public-only.** Renderer rejects any fixture marked `non_public`.
- **No baseline mutation.** The renderer never writes to
  `baseline.json`; the existing `headcleaner benchmark --update-baseline`
  workflow is the only path that may update it.
- **No original fixture upload.** The dashboard surfaces only metric
  numbers; the original fixture bytes never leave the test workspace.

## Limitations

- Per-metric delta gates (CI pass/fail thresholds) are not part of this
  contract; the dashboard surfaces numbers, the workflow enforces.
- The dashboard is rendered on demand; the publishing decision remains
  out-of-band and explicit.
