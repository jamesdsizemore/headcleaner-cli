# Add headcleaner to CI without installing every optional tool

This tutorial walks through adding headcleaner to a continuous integration pipeline. The challenge is that headcleaner's optional tools (OfficeCLI, LibreOffice, Tesseract, readpst) take time to install and may not all be relevant to a given repository. The lesson shows how to install only what you need, how to fail the build on policy violations, and how to upload the manifest as an artifact for debugging.

## Outcome

You will have a GitHub Actions workflow that runs `headcleaner convert` on every pull request, builds the search index, fails the build on policy violations, and uploads the run artifacts for review.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- A GitHub repository with a folder of documents you want headcleaner to convert. The folder should contain a representative sample of the formats you care about; a single PDF for a PDF-focused repo, or a mixed folder for a general one.
- Permission to add or modify a workflow file under `.github/workflows/`.

## Step 1 — Decide what you actually need

The first decision is which optional tools your CI runner needs. The answer depends on which formats your documents use, not on what headcleaner can do in principle.

For a docs-only repository that ships Markdown files, you do not need any optional tools. For a repository with PDFs, you need at least `pdfplumber`, which headcleaner bundles, and you may need Tesseract if the PDFs are scanned. For a repository with Office documents, you need OfficeCLI. For a repository with legacy Office documents, you also need LibreOffice.

The principle is: install the smallest set that lets the run produce the output your reviewers need to see. Installing tools you do not need wastes time and surface area.

## Step 2 — A minimal workflow

The smallest workflow that runs headcleaner in CI is:

```yaml
name: headcleaner

on:
  pull_request:
    paths:
      - 'documents/**'

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - name: Install headcleaner
        run: pip install .
      - name: Convert documents
        run: headcleaner convert ./documents ./out
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: headcleaner-output
          path: |
            out/REPORT.md
            out/manifest.json
```

This workflow checks out the repository, installs headcleaner via `pip`, runs the conversion, and uploads the report and manifest as artifacts. The `pull_request` trigger with a `paths` filter means the workflow only runs when files under `documents/` change, which keeps CI time and cost down.

## Step 3 — Add the search index step

If you want the workflow to also build the search index, add a step after the conversion:

```yaml
      - name: Rebuild search index
        run: headcleaner index rebuild ./out/okf
```

The index is a derivative; building it in CI is optional. The reason to do it is to catch chunking or indexing regressions before they land. The reason to skip it is that the index is large and is not consumed in CI itself; the artifacts you actually want are the report and manifest.

## Step 4 — Install optional tools selectively

If your documents need OfficeCLI, Tesseract, or LibreOffice, install only what your documents actually use. For a PDF-only repository with text-native PDFs, you do not need Tesseract or LibreOffice at all. For a mixed repository, install OfficeCLI and skip LibreOffice unless you have legacy Office files.

Add the installation step before the conversion:

```yaml
      - name: Install OfficeCLI
        run: npm install -g @officecli/officecli
      - name: Install Tesseract
        run: sudo apt-get install -y tesseract-ocr
```

Each step adds time to the workflow. Add only the ones that close a real gap in your conversion.

## Step 5 — Fail on policy violations

The most useful CI behavior is to fail the build when headcleaner's policy rules are violated. Add a policy test step:

```yaml
      - name: Test policy
        run: headcleaner policy test ./out --pack my-pack
```

The policy test command exits with code 0 if no error rules match, 1 if any error rule matched, and 2 if the policy file itself is invalid. This maps cleanly onto CI exit codes; the step will fail the build when policy violations occur.

The policy pack you pass to `--pack` should be a TOML file in your repository that defines the rules you care about. The [configuration reference](../reference/configuration-reference.md) documents the available rule shapes. A typical starting pack might require that every concept has a non-empty `type`, that the `status` field is `unverified` (so reviewers can spot anything that has slipped past the gate), and that the `sources[]` array is non-empty.

## Step 6 — Capture structured events

If you want to feed the run into a downstream dashboard or alerting tool, capture the JSON event stream:

```yaml
      - name: Convert documents with structured events
        run: headcleaner convert ./documents ./out --json > events.jsonl
      - name: Validate event schema
        run: headcleaner events validate events.jsonl
```

The `--json` flag emits one JSON object per event on stdout. The `events validate` command checks the stream against the schema. Capturing this stream lets you build a dashboard of run statistics over time without having to scrape the human-readable report.

## Step 7 — Make the failure visible

When the workflow fails, the most useful artifact for the person debugging it is the report. The workflow above already uploads `out/REPORT.md` and `out/manifest.json` as artifacts, but you can make failures more visible by adding a job summary step:

```yaml
      - name: Summarize
        if: always()
        run: |
          echo "## headcleaner summary" >> $GITHUB_STEP_SUMMARY
          cat out/REPORT.md >> $GITHUB_STEP_SUMMARY
```

The `$GITHUB_STEP_SUMMARY` file is rendered as a Markdown section in the GitHub Actions UI. Anyone looking at the failed workflow sees the report inline, without having to download the artifact.

## Step 8 — Decide when to skip

If your pull request does not touch any document files, the workflow above will not run because of the `paths` filter. If you want the workflow to run anyway (to confirm nothing else changed in a way that affects headcleaner), drop the `paths` filter. If you want it to skip gracefully when the documents folder does not exist, add a guard:

```yaml
      - name: Check documents folder
        id: check
        run: |
          if [ -d "./documents" ]; then
            echo "exists=true" >> $GITHUB_OUTPUT
          else
            echo "exists=false" >> $GITHUB_OUTPUT
      - name: Convert documents
        if: steps.check.outputs.exists == 'true'
        run: headcleaner convert ./documents ./out
```

## What you have learned

You know how to add headcleaner to a GitHub Actions workflow with selective optional-tool installation, policy-based failure detection, structured event capture, and inline failure summaries. You also know how to keep the workflow small by using path filters and conditional steps.

## Where to go next

- [CI overview](../integrations/ci-overview.md) — the conceptual background for CI integration.
- [Configuration reference](../reference/configuration-reference.md) — the policy pack format and the available rule shapes.
- [Reference/cli-reference.md](../reference/cli-reference.md) — every command flag and exit code.