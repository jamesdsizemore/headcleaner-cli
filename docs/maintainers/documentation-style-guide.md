# Documentation style guide

This page defines the writing conventions for headcleaner's documentation. It is the maintainer's reference for what good docs look like, and the contributor's reference for what to write when adding a new doc.

## Two audiences

Headcleaner's documentation serves two audiences with rigorously separated needs:

- **Users** — developers who may never have heard of headcleaner or OKF and want simple, practical help.
- **Contributors** — maintainers who need implementation, architecture, testing, and extension guidance.

Never lead user documentation with internal terms such as adapter, routing layer, schema, subprocess boundary, canonical, derivative, or pipeline vocabulary. Explain those only in developer documentation.

The two styles must not be mixed on the same page. A user-guide page that drifts into implementation detail breaks the user's reading flow; a developer-guide page that drifts into marketing voice breaks the developer's trust.

## User page voice

Write in a warm, clear, confident, product-oriented voice. Assume the reader is intelligent but new to headcleaner. Explain unfamiliar terms immediately. Favor plain statements:

- "headcleaner converts your folder of mixed documents into clean Markdown you can read, search, and trust."
- "If an optional tool is not installed, headcleaner tells you what is missing."
- "Run one small set of checks before opening a pull request."

Every page must answer some combination of: what is this, why does it matter, when should I use it, what do I need, what exact steps do I take, what result should I expect, and what should I do next?

## Developer page voice

Write in a contract-shaped, comprehensive, reference-oriented voice. Lead with the data shapes, the public APIs, and the invariants. Code blocks and tables are first-class citizens; narrative is connective tissue.

Every page should document:

- The data shapes (dataclass fields, JSON shapes, query parameters).
- The public functions or commands (signatures, parameters, return values).
- The invariants the implementation enforces.
- The tests that prove the invariants.
- The links to related pages.

## Voice discipline

- Use present tense for descriptions ("headcleaner converts..." not "headcleaner will convert...").
- Use second person for the reader ("you can run..." not "one can run...").
- Use active voice ("headcleaner writes..." not "the file is written by headcleaner...").
- Avoid filler ("simply", "just", "easy", "obviously") that condescends or patronizes.
- Use American English spelling (recognize, color, behavior) consistently.
- Use sentence case for headings. Capitalize the first word and proper nouns only.

## Lists and tables

Lists and tables are information-dense and useful. The discipline is that every list lives inside prose that says what the list means. A bullet-only doc has no narrative flow and is hard to read.

The pattern is:

> The five statuses are: ok, warn, fail, error, skipped. Each one tells you something specific.

> | Status | Meaning |
> |---|---|
> | ok | The file was converted successfully. |
> | warn | The file was converted with a recoverable condition. |
> | failed | The file could not be converted. |

The table follows the prose that introduces it. The reader knows why the table is there before they read the table.

## Code blocks

Code blocks are copy-pasteable. The convention:

- Show the exact command to run, including flags.
- Use real commands from the actual CLI, not invented examples.
- Indicate expected output where useful.
- Use fenced code blocks with a language hint for syntax highlighting.

When a code block is part of a longer procedure, the prose between code blocks explains what just happened and what to do next.

## Cross-linking

Every page links to the next logical step. The pattern:

- The user-guide pages link to the relevant tutorial pages.
- The tutorial pages link to the relevant reference pages.
- The reference pages link to the relevant developer-guide pages.
- The developer-guide pages link back to the architecture and source-tree pages.

The links are bidirectional where possible. If a user-guide page links to a tutorial, the tutorial links back to the user-guide page.

## Diagrams

User pages use dark-themed SVG diagrams in the cyan/pink/purple palette. Developer pages use ASCII diagrams that render correctly in any terminal or text viewer. The two mediums are deliberately different because the audiences have different needs: users want a polished visual, developers want a copy-pasteable sketch.

When adding a new diagram:

- User pages: produce a dark-themed SVG with semantic CSS classes (no inline colors), include it as an `<img>` tag with descriptive alt text, and reference the source file.
- Developer pages: produce ASCII art with consistent box-drawing characters, and ensure it renders correctly in a fixed-width font.

## Documentation that must change for a new feature

When you add a new feature to headcleaner, the following documentation must change:

- The CLI reference, if you added a new command or flag.
- The configuration reference, if you added a new policy field.
- The engine directory, if you added a new adapter.
- The MCP tool reference, if you added a new MCP tool.
- The serve API reference, if you added a new HTTP endpoint.
- The relevant tutorial, if the feature has a tutorial-shaped use case.
- The relevant developer guide page, if the feature has a public API or data shape.
- The `CHANGELOG.md` (preserved in the archive), if the feature is user-visible.

The discipline is: a feature is not complete until its docs are updated. The [DOCS_REWRITE_TRACKER](../DOCS_REWRITE_TRACKER.md) is the authoritative map of what docs exist; check it before adding a feature.

## Mandatory phase and commit audit

Every implementation phase must review the complete active documentation surface: root `README.md` and all Markdown under `docs/`, excluding historical `docs/_archive/`. The current phase audit records one concrete, evidenced disposition per page: `updated`, `reviewed`, or `not-applicable`. A phase cannot be declared complete until `scripts/verify_docs.py --phase <phase>` validates both that complete audit and all local targets/heading fragments.

Every commit must also stage an updated current audit and `DEVELOPMENT_HISTORY.md`. The versioned pre-commit hook enforces this after `sh scripts/install-git-hooks.sh`. The full contract, audit schema, and recovery path are in [documentation governance](../development/DOCUMENTATION_GOVERNANCE.md).

## What to read next

The [DOCS_REWRITE_TRACKER](../DOCS_REWRITE_TRACKER.md) is the master plan for the documentation tree. The [support runbook](support-runbook.md) covers user-reported documentation issues. The [coding standards](../developer/coding-standards.md) covers the conventions for code-adjacent documentation like docstrings.