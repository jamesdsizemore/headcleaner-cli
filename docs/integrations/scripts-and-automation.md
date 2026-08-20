# Scripts and automation

Headcleaner is a CLI tool with no long-running state of its own beyond the files it writes. That makes it straightforward to drive from scripts, schedulers, and automation tools. This page covers the conventions and pitfalls of running headcleaner from automation.

## The exit code contract

Headcleaner uses a stable set of exit codes:

- `0` — success. No error-level findings or failures occurred.
- `1` — recoverable failure. A file was in `failed` status, a policy rule matched an error finding, a search query had no results, or a command-specific failure occurred. The output is still usable.
- `2` — fatal error. An argument was malformed, the lockfile is out of date, the environment is missing a required tool, or an internal error occurred.

Automation should treat `1` as "fix the underlying issue, the run produced usable output" and `2` as "fix the automation, the run did not produce useful output." The distinction matters because a `2` is usually a configuration or environment problem that will recur on every run, while a `1` is usually a content problem that needs human attention.

## The `--json` flag

When headcleaner runs from a script, pass `--json` to get structured events on stdout instead of human-readable lines. The event stream format is stable across versions and is documented in the [result reference](../reference/result-reference.md).

A typical shell loop:

```bash
headcleaner convert ./in ./out --json > events.jsonl 2> errors.log
```

The exit code tells you the run succeeded or failed; the event stream tells you what happened per file; the errors log captures any non-fatal warnings or human-readable messages that headcleaner emitted to stderr.

## Scheduling headcleaner

The most common scheduling pattern is `cron` on Linux and macOS, or Task Scheduler on Windows. The convention:

- Run headcleaner on a schedule that matches how often your documents change. Daily is a reasonable default; weekly is enough for slowly-changing corpora.
- Capture the manifest and report for each run. Diff them against the previous run to detect regressions.
- Fail silently on recoverable failures (`exit 1`); alert on fatal errors (`exit 2`).

A typical cron entry:

```cron
0 2 * * * cd /path/to/repo && uv run --no-sync --python 3.13 headcleaner convert ./in ./out --quiet
```

The `--quiet` flag suppresses per-file progress lines, which is what you want when the output is going to a log file rather than an interactive terminal.

## Watching a directory

For directories that change frequently, headcleaner's `watch` command (combined with `sync`) gives you an event-driven workflow. The watcher invokes the sync planner in dry-run mode and applies changes only when you explicitly tell it to.

The watcher is documented in detail in the [sync and watch developer guide](../developer/sync-and-watch.md). The short version is: start the watcher pointing at your input folder and your output folder, and let it report what it would do. When you are ready to apply, run `headcleaner sync` with `--apply`.

## Driving headcleaner from Python

Because headcleaner is a CLI, you can drive it from Python using `subprocess.run`:

```python
import subprocess
result = subprocess.run(
    ["uv", "run", "--no-sync", "--python", "3.13", "headcleaner", "convert", "./in", "./out", "--json"],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    for line in result.stdout.splitlines():
        event = json.loads(line)
        # process the event
else:
    print(f"headcleaner failed: {result.stderr}")
```

If you want a tighter integration, headcleaner's modules are importable as a Python library. The library API is not formally stable across versions; the CLI is the supported interface. Use the library at your own risk, and pin your headcleaner version.

## Driving headcleaner from CI

The CI integration shape is documented in the [CI overview](ci-overview.md) and the [tutorial on CI integration](../tutorials/ci-integration.md). The short version is: install the smallest set of optional tools that lets your corpus convert correctly, run the conversion with `--json`, capture the manifest and report as artifacts, and fail the build on policy violations or conversion failures.

## Common pitfalls

The most common automation pitfalls are:

- **Not pinning the headcleaner version.** Pin it explicitly so your automation is reproducible.
- **Not using `--no-sync`.** Without it, every command checks the lockfile. With it, the command uses the resolved environment directly.
- **Not capturing both stdout and stderr.** `--json` writes to stdout; warnings and human-readable messages go to stderr. Capture both.
- **Treating warnings as errors.** Warnings are signals. Use `--strict` if you want them to fail the build.
- **Not diffing against the previous run.** Without diffing, regressions accumulate silently.

## Where to read next

The [result reference](../reference/result-reference.md) explains every field of the manifest and every event in the JSON stream. The [CLI reference](../reference/cli-reference.md) is the complete command reference. The [tutorial on CI integration](../tutorials/ci-integration.md) is the GitHub Actions walkthrough.