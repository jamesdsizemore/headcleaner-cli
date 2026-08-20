# Support runbook

This page is the maintainer's reference for handling user reports. It covers the most common categories of issues, the diagnostic steps for each, and the right way to escalate when an issue requires a code change.

## Bug reports

When a user files a bug report, the first step is to gather the minimal reproduction:

1. The headcleaner version (`headcleaner --version`).
2. The platform (Windows/macOS/Linux) and Python version.
3. The exact command that produced the bug, including all flags.
4. The relevant portion of the manifest or report.
5. A small reproduction case if possible (a single source file and a single command).

The maintainer's first response should be to confirm the reproduction. If the bug reproduces with the latest main, the issue is real. If the bug reproduces only on a specific platform or Python version, that is information to capture early.

## Missing optional tools

The most common "bug" is actually a missing optional tool. The user reports that headcleaner skipped their files or returned an error; the actual cause is that OfficeCLI, LibreOffice, Tesseract, or `readpst` is not installed.

The diagnostic is `headcleaner doctor`. The doctor command reports which tools are present and which are missing. The user installs the missing tool per the [installation guide](../getting-started/installation.md#optional-tools-that-make-headcleaner-more-useful) and re-runs.

## Wrong exit code

If a user reports that headcleaner returned an unexpected exit code, the diagnostic is to capture the exit code and the error message. The exit code contract is documented in the [result reference](../reference/result-reference.md#exit-codes):

- `0` — success
- `1` — recoverable failure (a file was in `failed` status, a policy rule matched)
- `2` — fatal error (malformed argument, missing required tool, internal error)

If the exit code is `1`, the failure is recoverable and the output is still usable. If the exit code is `2`, the failure is fatal and the output may not be usable. The fix for each category is different.

## Missing source file

If a user reports that headcleaner did not process a file, the diagnostic is to check the manifest. The manifest records every file headcleaner saw and what it did with each. If a file is in the manifest with `status: skipped`, the message in the `error` field explains why.

The most common reasons:

- The file extension is not in any adapter's `extensions`. The fix is to add an adapter or rename the file.
- The required tool is not installed. The fix is to install the tool.
- The file is excluded by `--exclude` glob. The fix is to remove the exclusion.

## Wrong conversion output

If a user reports that the conversion output is incorrect, the diagnostic is to compare the output against the source. The manifest records the source SHA-256 for every file; the conversion output carries the citation block with the same hash.

If the citation matches but the body is wrong, the bug is in the adapter. Open an issue with the source file, the expected output, and the actual output. If the citation does not match, the bug is upstream — the source file changed between runs.

## Performance issues

If a user reports that headcleaner is slow, the diagnostic is to identify which stage is slow. Use `--json` to capture per-file `duration_seconds`. A small number of files will dominate the wall clock; focusing on them usually reveals the cause.

Common slow stages:

- OCR (Tesseract). Each page takes seconds; a large scanned PDF can take hours.
- Embedding. The HTTP provider is network-bound; the local provider is CPU-bound.
- The first run on a large bundle. Subsequent runs use the cache and are much faster.

## When to escalate

Escalate to a code change when:

- The bug reproduces on the latest main.
- The bug is in a code path, not a configuration issue.
- The bug affects a safety invariant (source immutability, network permission, trust state).

Do not escalate when:

- The bug is actually a missing optional tool.
- The bug is a misuse of the CLI (wrong flags, wrong arguments).
- The bug is a third-party adapter issue (the fix lives in the adapter's upstream).

## Communication with users

When responding to a user, lead with the diagnosis, not the question. "I see from your manifest that the file was skipped because LibreOffice is not installed" is more useful than "Can you run `headcleaner doctor` and tell me what it says?"

Be specific. "Your output is wrong" is not actionable; "your output for `notes.docx` is missing the first heading because OfficeCLI is not installed" is.

Be patient. The user is reporting a problem they care about; taking time to understand their reproduction is part of the support.

## What to read next

The [incident and security runbook](incident-and-security.md) covers the cases where a bug report is actually a security issue. The [versioning and compatibility reference](versioning-and-compatibility.md) covers version semantics. The [user troubleshooting guide](../user-guide/troubleshooting.md) is the symptom-first page you can point users at.