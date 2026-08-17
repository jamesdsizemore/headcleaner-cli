# Operations: diagnostics and conversion reports

## `headcleaner doctor`

Run a local preflight before a conversion or when an environment behaves
unexpectedly:

```bash
headcleaner doctor
headcleaner doctor --output-dir ./clean-output
```

The command is terminal/CI-safe plain text and returns a non-zero exit code
only when a required check fails.

| Check | Required | Purpose |
|---|---:|---|
| Python version | Yes | Requires Python 3.12+ |
| `PATH` environment | Yes | Ensures command lookup has a non-empty search path |
| OfficeCLI on `PATH` | Yes | Required for Office document formats |
| Output directory | Yes | Verifies the output directory can be created and written |
| Bundle registry | Yes | Validates the `@slug` registry TOML when it exists |
| Tesseract | No | Needed only for `--ocr` |
| `readpst` | No | Needed only for PST extraction |
| Loaded MCP bundles | Informational | Shows MCP state available to the current process |

Warnings do not block conversion. A missing OfficeCLI installation or an
unwritable output directory does.

OfficeCLI is the recommended Windows document engine:

```bash
npm install -g @officecli/officecli
```

## Automatic `REPORT.md`

Every non-dry `headcleaner convert` run writes `<output>/REPORT.md`.
It is intentionally a portable Markdown artifact for review, CI collection,
and organization-level dashboards.

The report contains:

- input bundle and wall-clock timestamps;
- processed, skipped, failed, total, and success-rate counts;
- a per-engine table with total, successful, failed, **error rate**, and
  **average per-file time**;
- up to ten escaped error messages for quick triage.

Timing represents conversion extraction and emission work for each source.
For multi-concept sources, elapsed time is divided across the concepts that
source produced. Cached records can have no timed work and are shown as
`n/a` in the average-time column.

`--dry-run` deliberately does not write a report or other output artifacts.
