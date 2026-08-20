# Citations and trust

This page explains the citation block at the top of every converted file, what the trust family fields mean, and why auto-conversion is not the same as human review. The page is short on purpose: the concepts here are foundational and once you understand them, the rest of headcleaner's safety model falls into place.

## What is in the citation block

Every file headcleaner emits — whether it lives in `_md/` or in `okf/` — opens with a YAML frontmatter block. The most important fields in that block are:

- `type`, which describes what kind of artifact the file is. Headcleaner sets this to `Document` for every auto-converted file. The OKF format uses additional type values for non-document artifacts, but headcleaner currently emits only documents.
- `status`, which describes the current state of the file. Auto-converted files start with `status: unverified`. The status changes only when a downstream reviewer or policy makes an explicit decision about the file.
- `generated`, which records who or what produced the file and when. Headcleaner sets this to `human:<user>@<host>` using the values of `$USER` (on macOS and Linux) or `$USERNAME` (on Windows). If you want this to read something other than your system username, set the environment variable before running headcleaner.
- `verified`, which records the most recent human review action. Headcleaner always sets this to `human:pending` on auto-converted files. Changing it requires an explicit human action; headcleaner will never silently promote a file.
- `stale_after`, which records the date after which the file should be considered stale. Headcleaner defaults to 180 days from the conversion date. The [Claims and policy developer guide](../developer/claims-and-policy.md) explains how stale findings are derived from this field.
- `sources`, which is a list of source references for the file. Every auto-converted file has exactly one source entry, containing the source URI and the source SHA-256 hash. The URI is the location of the source file at conversion time; the hash is the unique fingerprint of the source bytes.

Together, these six fields form the **trust family** that OKF v0.2 requires. They are the structured answer to "what is this, where did it come from, has a human checked it, and is it still fresh?"

## Why citations matter

Citations exist so that you, a reviewer, or a downstream tool can always answer "where did this content come from?" without guessing. Without citations, a Markdown file is just text; you have to trust whoever produced it. With citations, every piece of generated content is traceable to a specific source file at a specific version.

The SHA-256 hash in the citation is the load-bearing piece. It is a cryptographic fingerprint of the source bytes; if even one byte of the source changes, the hash changes. This means that if you ever need to prove "this Markdown came from that exact source," you can re-hash the source and compare it to the citation. If the hashes match, the provenance is certain.

Headcleaner uses the same hash to detect changes between runs. When you re-run a conversion, headcleaner compares the current source hash to the recorded source hash. If they differ, the source has been modified and the conversion needs to be redone; if they match, headcleaner knows the cached output is still valid and skips re-processing the file. This is how headcleaner stays fast on large folders without ever producing stale output.

## Why auto-conversion is not review

Auto-conversion is the process of running headcleaner on a folder and producing a clean output. The output is correct in the sense that it faithfully represents the source bytes, but it is **not** verified in the sense that a human has read it and decided it is accurate, complete, and appropriate for whatever you intend to do with it.

This distinction matters because most downstream systems that consume documents make assumptions about whether a human has reviewed them. A regulatory archive assumes reviewed; a publication pipeline assumes reviewed; a legal-hold system assumes reviewed. If headcleaner silently produced output that looked reviewed, those systems would treat auto-converted content as if it had passed a human checkpoint. That would be unsafe.

Headcleaner refuses to make that mistake. Every auto-converted file starts with `verified: human:pending`, and that field cannot change without an explicit human action. The action that changes it is a deliberate review step — you open the file, you check it, you record your decision. The mechanism for recording that decision is part of the [Review workflow](#the-review-workflow) below.

If you feed headcleaner output to a downstream system that requires human-reviewed status, you must run the explicit review step on every file you intend to publish. There is no shortcut around this; the constraint is part of the safety guarantee.

## The review workflow

When you are ready to mark a file as reviewed, the workflow is:

1. Open the converted file in your editor of choice.
2. Read the file end to end, comparing it against the source as needed.
3. If the conversion looks correct, mark the file as reviewed by changing `verified: human:pending` to `verified: human:reviewed` and adding your reviewer identifier and the review date.

Headcleaner does not provide a dedicated CLI command for this transition yet; it is intentionally a manual step that lives in your editor. The reason is that no CLI can know whether you actually read the file. The human reviewer who marks the file is the one asserting "I read this and it is correct."

If you need a structured audit trail of who reviewed what and when, the convention headcleaner follows is to record the reviewer identity and review timestamp in additional frontmatter fields. The OKF v0.2 trust family defines a `reviewers` field for this purpose; you can extend your frontmatter with it.

## Stale content

Every converted file carries a `stale_after` date. By default, headcleaner sets this to 180 days from the conversion. After that date passes, the [Claims module](../developer/claims-and-policy.md) emits a stale finding against the file when you run `headcleaner claims`. The finding is a warning, not an error; it is a signal that the conversion is old enough that you should consider re-checking the source and re-running the conversion.

If you want to change the staleness window, you can configure it in your policy file. The default of 180 days is conservative; you can shorten it (say, to 30 days for a regulatory use case) or lengthen it (to a year for archival content that does not change often). The [configuration reference](../reference/configuration-reference.md) documents the field.

## What to read next

If you want a complete field reference for the frontmatter block, the OKF vocabulary is documented in the archived [`docs/_archive/legacy-docs/OKF_NOTES.md`](../_archive/legacy-docs/OKF_NOTES.md). If you want to understand the search and indexing side of citations — how chunks carry citation data, how the graph uses citation evidence — read [Search and context](search-and-context.md). If you want to add explicit policy rules that govern which sources can be converted and what status they must have, read the [configuration reference](../reference/configuration-reference.md).