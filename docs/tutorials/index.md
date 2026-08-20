# Tutorials

This page is the table of contents for the headcleaner tutorial collection. Each tutorial is a guided lesson, not a command list: every tutorial tells you what you will learn, what you need before you start, walks you through the exact steps, shows you the expected result, explains what just happened, and points you at the next lesson.

Read the tutorials in any order. If you are brand-new to headcleaner, start with [Your first ten minutes](first-10-minutes.md) and then pick the path that matches the kind of work you do.

## The lessons

[Your first ten minutes](first-10-minutes.md) is the on-ramp tutorial. It assumes you have just installed headcleaner and want to confirm it works on a real folder of your own documents. You will run a single conversion, read the output, and decide where to go next.

[Set up a Python-friendly document conversion](python-project.md) walks through converting a folder of mixed Office documents and PDFs into a searchable archive. It assumes you have OfficeCLI and either LibreOffice or Tesseract installed, and teaches you the shape of a healthy run on a realistic corpus.

[Set up a PDF and OCR conversion](pdf-and-ocr.md) is the lesson for scanned PDFs, image-only documents, and any corpus where text extraction needs help from Tesseract. It explains when to enable OCR, when to leave it off, and how to read the OCR-related diagnostics.

[Set up email and attachment conversion](email-and-attachments.md) walks through converting `.eml`, `.msg`, and `.pst` archives. Attachments are processed recursively with safety limits; this tutorial explains the limits and the way parent-child provenance is recorded in the output.

[Set up local search over your output](local-search.md) takes you from a converted bundle to a searchable SQLite index and walks through the CLI search, the FastAPI server, and the MCP server. You will learn how to use filters and how the deterministic tie-break works.

[Connect headcleaner to an AI coding assistant](ai-coding-assistant.md) is the practical setup lesson for the MCP integration. You will configure a generic stdio client, confirm the assistant can see the search index, and try a few example prompts.

[Add headcleaner to CI without installing every optional tool](ci-integration.md) is the lesson for teams that want headcleaner to run on every pull request without each CI runner needing every optional tool. The lesson shows how to install only what you need, how to fail the build on policy violations, and how to upload the manifest as an artifact for debugging.

## What to read next

When you finish the tutorials, the [user guide](../user-guide/index.md) is the next stop. The [CLI reference](../reference/cli-reference.md) is the lookup for any specific command. The [developer guide](../developer/contributor-onboarding.md) is where you go when you want to extend headcleaner with a new adapter, engine, or configuration field.