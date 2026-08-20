# Set up email and attachment conversion

This tutorial walks through converting a folder of email archives (`.eml`, `.msg`, `.pst`) into a clean OKF bundle. Email is a special case because each message may contain attachments that themselves contain documents, and headcleaner recursively converts those attachments while preserving the parent-child provenance.

## Outcome

You will have converted a folder of email archives into a bundle where each message is a concept, each attachment is a child concept linked to its parent, and every attachment's output cites the parent message as well as the original attachment bytes.

## Prerequisites

- headcleaner installed per the [installation guide](../getting-started/installation.md).
- For `.pst` archives, the `readpst` binary installed per the [installation guide](../getting-started/installation.md#optional-tools-that-make-headcleaner-more-useful). On Windows, `readpst` ships with the MSYS2 environment; on macOS, install via Homebrew; on Linux, install via your distribution's package manager.
- A folder containing at least one `.eml` file or one `.msg` file. A `.pst` archive from an Outlook export also works.

## Step 1 — Understand the email data model

Each email message becomes one concept in the OKF bundle. Each attachment becomes a child concept. The child concept's frontmatter records:

- `parent_source_sha256`: the SHA-256 hash of the parent message.
- `parent_attachment_id`: an identifier for the attachment within the parent.
- `child_ordinal`: the position of this attachment among its siblings.
- `sources[]`: the original attachment bytes, with their URI and SHA-256 hash.

This is the provenance chain that lets you trace any extracted attachment back to the message that contained it and ultimately to the source archive.

## Step 2 — Convert the email folder

The conversion command handles email the same way it handles any other format:

```bash
uv run --no-sync --python 3.13 headcleaner convert ./email-archive ./email-archive.clean --format both
```

Headcleaner reads each message, extracts the body and the attachment list, and processes each attachment through the same adapter pipeline that processes standalone files. The body of each message is rendered as Markdown with the standard frontmatter; the attachments are rendered into their own concepts in a sub-namespace.

For `.pst` archives, headcleaner invokes `readpst` to extract individual messages, then processes each message as if it were a standalone `.eml` file. If `readpst` is not installed, the `.pst` archive will be skipped with a message naming the missing tool.

## Step 3 — Look at the bundle structure

Open `./email-archive.clean/okf/` in your file browser. You will see something like:

```text
./email-archive.clean/okf/
├── index.md
├── 2024-03-15-project-update.eml.md
├── 2024-03-15-project-update.eml.attachments/
│   ├── 00-q1-spreadsheet.xlsx.md
│   ├── 01-proposal.pdf.md
│   └── 02-photo.jpg.md
├── 2024-04-02-status.eml.md
└── 2024-04-02-status.eml.attachments/
    └── 00-budget.xlsx.md
```

Each message has a sibling `.attachments/` directory containing one concept per attachment. The numeric prefix on each attachment filename is the `child_ordinal` — the order of the attachment within its parent message. The parent message's frontmatter records the same ordinal for each attachment, making the link between parent and child unambiguous.

## Step 4 — Read the parent-child citations

Open `2024-03-15-project-update.eml.md`. The frontmatter includes the standard source citation plus an `attachments` field that lists each child:

```yaml
type: Document
status: unverified
generated: human:you@example
verified: human:pending
stale_after: 2027-02-16
sources:
- uri: file:///path/to/email-archive/2024-03-15-project-update.eml
  sha256: ccc...
attachments:
- id: 00-q1-spreadsheet.xlsx
  sha256: ddd...
  media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- id: 01-proposal.pdf
  sha256: eee...
  media_type: application/pdf
- id: 02-photo.jpg
  sha256: fff...
  media_type: image/jpeg
```

Open one of the attachment files. Its frontmatter records both the original attachment bytes (the `sources[]` entry) and the parent provenance (the `parent_source_sha256` and `parent_attachment_id` fields):

```yaml
type: Document
status: unverified
sources:
- uri: file:///path/to/email-archive/2024-03-15-project-update.eml
  sha256: ccc...
parent_source_sha256: ccc...
parent_attachment_id: 00-q1-spreadsheet.xlsx
child_ordinal: 0
```

The dual citation is what makes attachment provenance auditable. You can answer "where did this attachment come from?" with the parent message URI, and "what was the parent message's hash?" with the `parent_source_sha256`.

## Step 5 — Understand the safety limits

Headcleaner does not recursively process attachments without limits. The limits protect you from archive bombs, encrypted members, and other hostile content. The default limits are:

- Maximum recursion depth: 2 (a message may contain a ZIP that may contain documents, but not further nesting).
- Maximum number of members per archive: 100.
- Maximum member size: 25 MB.
- Maximum total extracted bytes: 100 MB.

If an attachment exceeds a limit, it is quarantined. The parent message is still converted; the offending attachment is reported in the run report with a `QUARANTINED` status and a reason. Sibling attachments continue processing; one bad attachment does not stop the rest.

You can adjust these limits in your policy file. The [configuration reference](../reference/configuration-reference.md) documents the available knobs. Adjusting limits down makes your runs safer; adjusting them up trades safety for completeness.

## Step 6 — Handle encrypted or hostile members

Email messages and attachments may be encrypted with a password. Headcleaner does not ask for passwords; encrypted members are quarantined with a clear `ENCRYPTED_MEMBER` diagnostic. If you need to extract an encrypted archive, do so manually before running headcleaner and pass the extracted contents through the conversion as a separate input folder.

Members with symlinks, directory traversal attempts, or other suspicious characteristics are quarantined before extraction. The [troubleshooting guide](../user-guide/troubleshooting.md) covers the symptom-driven diagnosis if you see unexpected quarantines.

## Step 7 — Build the search index

Once the conversion is complete, build the search index over the entire bundle, including the attachments:

```bash
uv run --no-sync --python 3.13 headcleaner index rebuild ./email-archive.clean/okf
```

The rebuild includes both parent messages and child attachments as searchable chunks. A search across the email archive will surface results from both the message bodies and the attachment contents, with citations that distinguish them.

## What you have learned

You know how to convert email archives, how the parent-child provenance is recorded, where the attachment outputs live, and what the safety limits are. You also know how to handle encrypted or hostile members without compromising the rest of the run.

## Where to go next

- [PDF and OCR tutorial](pdf-and-ocr.md) — when attachments include scanned PDFs.
- [Local search tutorial](local-search.md) — going deeper on the search index, including how citations work for parent-child relationships.
- [Configuration reference](../reference/configuration-reference.md) — adjusting the attachment safety limits.