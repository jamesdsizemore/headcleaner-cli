# Set up a PDF and OCR conversion

This tutorial is for corpora that include scanned PDFs and image-only documents. It explains when to enable OCR, when to leave it off, and how to read the OCR-related diagnostics so you can tell whether your conversion is healthy.

## Outcome

You will have converted a folder of mixed text-native and scanned PDFs into a clean, searchable bundle, with OCR applied only where it is needed.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- Tesseract installed per the [installation guide](../getting-started/installation.md#tesseract-for-scanned-pdfs-and-image-only-documents). Confirm with `tesseract --version`.
- A folder containing at least one text-native PDF (one created from a Word document, for example) and at least one scanned PDF (one created by scanning a paper document). If you do not have a scanned PDF handy, most operating systems ship a PDF printer that can produce one for testing.

## Step 1 — Understand what headcleaner does with a PDF

For a PDF, headcleaner first tries to extract text directly. PDFs created from digital documents contain real text; headcleaner reads it without any external tool. PDFs created by scanning paper documents contain only images of pages; headcleaner detects that there is no extractable text and, if OCR is enabled, runs Tesseract on the page images to recover the text.

OCR is a separate, opt-in capability. By default, `headcleaner convert` does not run OCR. The reason is that OCR is slow and produces lower-fidelity output than direct text extraction; you almost always want it on for scanned PDFs and off for text-native PDFs. Headcleaner's `--ocr` flag is the explicit switch.

## Step 2 — First conversion without OCR

Start by converting your folder without OCR enabled. This is the default and lets you see which files headcleaner can read directly.

```bash
uv run --no-sync --python 3.13 headcleaner convert ./pdf-corpus ./pdf-corpus.clean
```

Open `./pdf-corpus.clean/REPORT.md` and look at the per-file lines. The text-native PDF should be in `ok` status. The scanned PDF should be in `skipped` status with a message like "no OCR engine installed" or "OCR not enabled for this run." That is expected and correct; you have not asked headcleaner to run OCR yet.

## Step 3 — Re-run with OCR enabled

Now enable OCR and re-run the conversion. The `--ocr` flag tells headcleaner to invoke Tesseract on any PDF that lacks extractable text.

```bash
uv run --no-sync --python 3.13 headcleaner convert ./pdf-corpus ./pdf-corpus.clean --ocr
```

The same scanned PDF that was `skipped` before should now be in `ok` (or possibly `warn`) status. The elapsed time per scanned page will be noticeably longer than for a text-native PDF — that is the cost of OCR and it is unavoidable.

If the scanned PDF is still in `skipped` status after this command, Tesseract is not installed or not on your `PATH`. Run `headcleaner doctor` to see what headcleaner can see. If Tesseract is installed but headcleaner cannot find it, the doctor command will tell you which path it expected; adjust your `PATH` or set the explicit Tesseract path in your policy file.

## Step 4 — Specify OCR languages

If your scanned PDFs are not in English, tell headcleaner which Tesseract language packs to load. The `--ocr-lang` flag takes a comma-separated list of language codes:

```bash
uv run --no-sync --python 3.13 headcleaner convert ./pdf-corpus ./pdf-corpus.clean --ocr --ocr-lang deu,eng
```

The codes are Tesseract's three-letter ISO 639-2 codes. Headcleaner checks that the requested languages are installed; if not, the run fails before any document processing begins with a clear doctor code pointing at the missing language pack. The [installation guide](../getting-started/installation.md#tesseract-for-scanned-pdfs-and-image-only-documents) lists how to install additional Tesseract language packs.

## Step 5 — Choose an OCR profile

For most users, the default OCR profile (`balanced`) is the right choice. It runs preprocessing (deskew, denoise) before passing pages to Tesseract and is the best trade-off between speed and accuracy.

If you have a corpus of high-quality scans and you want every page to receive the full archival preprocessing pipeline, use `--ocr-profile archival`. If you have a large corpus and you are willing to trade some accuracy for speed, use `--ocr-profile fast`. The full description of each profile lives in the [engine directory](../reference/engine-directory.md).

```bash
uv run --no-sync --python 3.13 headcleaner convert ./pdf-corpus ./pdf-corpus.clean --ocr --ocr-profile archival
```

## Step 6 — Read the OCR diagnostics

Open `./pdf-corpus.clean/REPORT.md` again. Look at the per-file warnings. Common OCR-related warnings include:

- `low_confidence` — Tesseract returned text but with a low confidence score. This usually means the scan is degraded or rotated. The body content is preserved; the warning tells you to spot-check.
- `page_skipped` — Tesseract failed to process a specific page. The page is left out of the output. The [troubleshooting guide](../user-guide/troubleshooting.md) covers the common causes.
- `language_mismatch` — Tesseract detected text that does not match the requested language pack. Either the language pack is wrong or the document has mixed-language content.

Warnings are not failures. The conversion produced output; the warning tells you to look more carefully at that file. Compare the OCR'd Markdown against the original PDF for any file with an OCR warning.

## Step 7 — Rebuild the search index and try a search

OCR'd content is now part of the bundle; rebuild the search index so you can query it:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./pdf-corpus.clean/okf
uv run --no-sync --python 3.13 headcleaner search "phrase from a scanned page" --bundle ./pdf-corpus.clean
```

If the OCR ran successfully, the search should return a result whose citation points to the scanned PDF. Open the scanned PDF and confirm the phrase appears on the page the citation points to.

## What you have learned

You know how to detect text-native versus scanned PDFs, enable OCR for the scanned ones, choose an OCR profile and language pack, and read the OCR diagnostics. You also know that OCR is opt-in and that headcleaner tells you when a file would benefit from OCR rather than silently invoking it.

## Where to go next

- [Engine directory](../reference/engine-directory.md) — the full description of every engine, including the OCR profiles and their preprocessing steps.
- [Email and attachments tutorial](email-and-attachments.md) — when your corpus includes email with PDF attachments.
- [Local search tutorial](local-search.md) — going deeper on searching across mixed text-native and OCR'd content.