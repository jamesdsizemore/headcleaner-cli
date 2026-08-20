# Understanding results

Every headcleaner command that does work emits a result, and every result has one of five possible statuses. This page explains what each status means, what usually causes it, and what you should do next. The page exists because most of the confusion new users have with headcleaner comes from misreading these statuses.

## The five statuses

Headcleaner uses five statuses to describe what happened to each source file in a run. They are: `ok`, `warn`, `fail`, `error`, and `skipped`. Each one tells you something specific.

### ok

`ok` is the healthy state. A file in `ok` status was successfully converted by the appropriate adapter, its citation was recorded, its frontmatter was written, and its body was emitted to both the `_md/` and `okf/` outputs.

What it looks like:

```text
[ok] notes.docx  -> _md/notes.docx.md (officecli, 0.4s)
```

What to do next: nothing. `ok` is the only status that requires no follow-up.

### warn

`warn` means the file was converted successfully, but headcleaner noticed something worth telling you about. Examples include an Office document with images that could not be extracted, a PDF where one page rendered as an image instead of text, or a Markdown file that was already in good shape and needed no body changes.

What it looks like:

```text
[warn] report.pdf  -> _md/report.pdf.md (pdfplumber, 1.2s) — 1 page OCR-skipped
```

What to do next: read the warning message. Most warnings describe a recoverable condition that does not affect the body of the converted file. If a warning bothers you, the [troubleshooting guide](troubleshooting.md) explains the common ones. You can suppress warnings by adjusting the policy in your project settings file; the [configuration reference](../reference/configuration-reference.md) documents the available knobs.

### fail

`fail` means the file could not be converted to a usable output. The file may have been corrupted, the engine may have been unable to parse it, or the file may have a format that headcleaner recognized as supported but the installed engine could not handle.

What it looks like:

```text
[fail] corrupt.docx  -> _md/corrupt.docx.md (officecli, error: file is not a zip archive)
```

What to do next: open the report and read the `error` field on the failed entry. The most common causes are a corrupted source file, a missing required tool for that format, or a permission issue reading the source. The [troubleshooting guide](troubleshooting.md) walks through the symptom-first diagnosis.

A `fail` does not stop the rest of the run. Headcleaner converts every file it can and reports each failure independently. This is intentional: one bad file in a folder of a hundred should not block the other ninety-nine.

### error

`error` is reserved for unexpected internal failures — the kind of condition that suggests a bug in headcleaner rather than a problem with your input. Examples include an adapter that raised an unhandled exception, a filesystem error during write, or a schema validation failure on the canonical output.

What it looks like:

```text
[error] notes.docx  -> _md/notes.docx.md (officecli, TypeError: unexpected element kind 'unknown')
```

What to do next: this is the status that warrants a bug report. Run `headcleaner --version` to record the version, capture the full error message from the report, and open an issue with the smallest possible reproduction. Unlike `fail`, an `error` typically means headcleaner encountered something the maintainers did not anticipate, and a fix may be needed.

### skipped

`skipped` is the status that confuses people the most. A file in `skipped` status was deliberately not converted. There are two reasons a file would be skipped, and they are very different.

The first reason is that headcleaner did not recognize the file as something it can convert. If your folder contains a `.zip`, a `.exe`, or a `.png`, those files will appear as `skipped` because headcleaner is a document converter, not a general file processor. Skipped here means "this is not in scope."

The second reason is that headcleaner recognized the format but the required tool for that format is not installed. If you have a `.pdf` but Tesseract is not installed and the PDF is image-only, headcleaner will skip it with a message saying which tool would be needed. Skipped here means "I know what this is, but I cannot read it without help that is not currently available."

What it looks like:

```text
[skipped] archive.zip  (unsupported format)
[skipped] scan.pdf  (no OCR engine installed; install Tesseract)
```

What to do next:

- If the skipped file is something headcleaner does not support at all, do nothing. It was correctly excluded.
- If the skipped file is something headcleaner supports but the required tool is missing, install the tool and re-run. The [installation guide](../getting-started/installation.md) lists every optional tool and how to install it.
- If you are not sure why a file was skipped, run `headcleaner doctor` to see which optional tools are present on your machine.

The most important thing to internalize about `skipped` is that it is **not** a synonym for "broken." A skipped file is a file headcleaner chose not to convert for a clear, documented reason. Many folders will have a few skipped files; that is normal.

## Status colors in the terminal

Headcleaner's terminal output uses cyan to indicate success, pink to indicate active work or warnings, and purple for information. Failed and error statuses are reported in pink because that is also the active-warning color in the palette; the palette deliberately avoids red and yellow to keep the experience calm. The exact color of any given line is not a substitute for reading the status word itself; always read the word.

## Reading the manifest

If you want to consume results programmatically — for example, to feed headcleaner output into a CI pipeline or a downstream script — read the manifest. The [result reference](../reference/result-reference.md) documents every field of the manifest and shows how to interpret status, engine, sha256, and error together. The manifest is the authoritative source of "what happened in this run"; the terminal output is a friendly projection of the same information.

## A worked example

Imagine you converted a folder of twelve mixed documents. Your terminal output might look like this:

```text
[ok]     notes.docx
[ok]     q3-report.pdf
[warn]   archived-email.eml  — 1 attachment quarantined (encrypted)
[ok]     meeting.html
[skipped] photo.jpg  (unsupported format)
[ok]     budget.xlsx
[fail]   corrupted.docx  (error: file is not a zip archive)
[ok]     press-release.docx
[skipped] scan.pdf  (no OCR engine installed; install Tesseract)
[ok]     changelog.md
[ok]     todo.txt
[ok]     readme.html
```

This run processed nine files successfully (`ok`), one with a recoverable condition (`warn`), one with an unsupported format (`skipped`), one with a missing optional tool (`skipped`), and one that was actually corrupted (`fail`). The healthy actions are: read the `warn` line and decide whether the encrypted attachment matters to you; install Tesseract if you want OCR on the scanned PDF; open the corrupted `.docx` in Word and either fix or remove it. None of these are signs that headcleaner is misbehaving.

## What to read next

If you want a complete reference for every status, every engine, and every field of the result manifest, see the [result reference](../reference/result-reference.md). If a specific status is causing you trouble right now, the [troubleshooting guide](troubleshooting.md) is symptom-driven and will get you to a fix faster than reading the reference end to end.