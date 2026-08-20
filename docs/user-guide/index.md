# headcleaner User Guide

This is the friendly start-here index for headcleaner. Every page linked here is written for someone who has never seen a Python CLI tool before. Internal terms are introduced in their own pages before they are used, and every page ends with a clear next step so you never end a doc wondering where to go.

## Where to start

If you have not installed headcleaner yet, start with the [Installation guide](../getting-started/installation.md) and then the [First run guide](../getting-started/first-run.md). Both assume nothing and explain every word they use.

If you have already installed headcleaner and run a first conversion, the page you want is [Everyday workflow](everyday-workflow.md), which is the practical story of how headcleaner fits into the work you actually do.

## The chapters

The user guide is organized by what you are trying to accomplish, not by which source module does the work. The chapters form a roughly linear path; you can read them in order or jump to whichever one answers your current question.

[The everyday workflow](everyday-workflow.md) walks you through running headcleaner at the moments it pays off the most: before opening a pull request, after an AI coding session, while introducing continuous integration, and while cleaning up a project. This is the page that turns headcleaner from a tool you tried once into a habit.

[Understanding results](understanding-results.md) explains the five status values headcleaner uses — `ok`, `warn`, `fail`, `error`, `skipped` — and what each one means for your project. The page makes a special point of explaining `skipped`, because that word often makes people worry when there is nothing to worry about.

[Checking converted output](checking-converted-output.md) is the page that teaches you how to read the output folder headcleaner produces. It walks through `_md/`, `okf/`, `manifest.json`, and `REPORT.md` and explains what each artifact is for.

[Citations and trust](citations-and-trust.md) explains the citation block at the top of every converted file, what the trust family fields mean, and why auto-conversion is not the same as human review.

[Search and context](search-and-context.md) explains how to make your converted output searchable — building the local index, running searches, and choosing between the CLI search, the FastAPI server, and the MCP server.

[Working with AI assistants](working-with-ai-agents.md) introduces MCP without protocol jargon and walks you through connecting headcleaner to a compatible coding assistant.

[Troubleshooting](troubleshooting.md) is a symptom-first guide: it lists the things that go wrong, the most likely reason, and the exact fix.

[FAQ](faq.md) answers the practical questions that come up most often.

## Conventions used in this user guide

Code blocks you can copy and paste are always shown with the exact command to run. Long inline paths are broken into shorter forms for readability. Every page links to the next logical step at the bottom so you can read sequentially without losing your place.

The user guide never uses red or yellow text. Headcleaner's status colors are cyan for success, pink for active work or warnings, and purple for information. If you see those colors in the terminal output, they mean what their colors say; they are not decoration.

When a feature requires explicit configuration or consent — running an embedding model, talking to a remote vector database, running OCR on a scanned PDF — the user guide explains why the feature is opt-in rather than treating it as a missing default. Safety is part of the design, not an afterthought.