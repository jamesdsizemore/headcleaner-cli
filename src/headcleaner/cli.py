"""headcleaner CLI entrypoint.

Subcommands:
  convert    Convert a folder to Markdown / OKF / both
  templates  List supported formats and engines (planned)
  agents     List detected engines and their install status (planned)
  config     Show / set per-user defaults (planned)

For v0.1 we ship `convert` only; the others are stubs that print a TODO.
"""
from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .run import RunOptions, run_pipeline
from .tui import run_with_tui


@click.group()
@click.version_option(__version__, prog_name="headcleaner")
def cli() -> None:
    """headcleaner — walk a folder, emit Markdown and/or OKF v0.2."""


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "okf", "both"], case_sensitive=False),
    default="both",
    show_default=True,
    help="Output format(s).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("./out"),
    show_default=True,
    help="Output directory (created if missing).",
)
@click.option("--ocr", is_flag=True, default=False, help="Enable Tesseract OCR for scanned PDFs.")
@click.option(
    "--officecli-timeout",
    type=int,
    default=60,
    show_default=True,
    help="Timeout in seconds for each OfficeCLI subprocess call.",
)
@click.option("--include", "-i", multiple=True, help="Include glob (may be repeated).")
@click.option("--exclude", "-e", multiple=True, help="Exclude glob (may be repeated).")
@click.option(
    "--jobs",
    "-j",
    type=int,
    default=1,
    show_default=True,
    help="Number of worker processes (1 = sequential).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable the SHA-256 skip-cache; re-convert every file.",
)
@click.option("--no-continue-on-error", is_flag=True, default=False, help="Stop on the first failure.")
@click.option("--tui/--no-tui", default=None, help="Force / disable the animated TUI. Default: auto-detect TTY.")
@click.option("--no-okf-index", is_flag=True, default=False, help="Skip writing OKF directory index.md files.")
@click.option(
    "--obsidian-compat",
    is_flag=True,
    default=False,
    help="Add Obsidian-friendly flat fields to OKF frontmatter (source, sha256, generated_by, verified_by, stale_on).",
)
@click.option(
    "--enriched-index",
    is_flag=True,
    default=False,
    help="Eng #38: show description + word count in OKF index.md.",
)
@click.option(
    "--write-log",
    is_flag=True,
    default=False,
    help="Eng #37: append a dated entry to <bundle>/log.md (OKF §9).",
)
@click.option(
    "--write-bundle-manifest",
    is_flag=True,
    default=False,
    help="Eng #39: aggregate across runs into bundle.manifest.json.",
)
@click.option(
    "--crossref",
    is_flag=True,
    default=False,
    help="Eng #34: rewrite cross-concept mentions as markdown links (second pass).",
)
@click.option(
    "--policy",
    type=click.Path(path_type=Path),
    default=None,
    help="Eng #35: load a trust policy TOML and fail the run if any concept violates it.",
)
@click.option(
    "--git-commit",
    is_flag=True,
    default=False,
    help="Eng #32: after a successful run, `git add` the output dir and `git commit` it.",
)
@click.option(
    "--git-commit-message",
    default="headcleaner: convert run",
    show_default=True,
    help="Commit message used by --git-commit.",
)
@click.option(
    "--git-commit-verify",
    is_flag=True,
    default=False,
    help="Run pre-commit hooks on the auto-commit (default: skip hooks for speed).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Eng #42: print what would be converted without writing any files.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Eng #43: emit one JSON line per event on stdout (for piping to jq).",
)
@click.option(
    "--tui / --no-tui",
    default=None,
    help="Force / disable the animated TUI (default: auto-detect TTY).",
)
@click.option(
    "--theme",
    type=click.Choice(["neon", "light", "dark", "mono"], case_sensitive=False),
    default="neon",
    show_default=True,
    help="Eng #40: color palette for the TUI and plain-mode progress lines.",
)
def convert(
    input_dir: Path,
    fmt: str,
    output: Path,
    ocr: bool,
    officecli_timeout: int,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    jobs: int,
    no_cache: bool,
    no_continue_on_error: bool,
    tui: bool | None,
    no_okf_index: bool,
    obsidian_compat: bool,
    enriched_index: bool,
    write_log: bool,
    write_bundle_manifest: bool,
    dry_run: bool,
    json_output: bool,
    theme: str,
    crossref: bool,
    policy: Path | None,
    git_commit_flag: bool,
    git_commit_message: str,
    git_commit_verify: bool,
) -> None:
    """Convert every supported document under INPUT_DIR."""
    from . import theme as _theme
    from .engines.officecli import OfficeCLIAdapter
    from .router import adapters as get_adapters

    # Apply the requested theme before anything renders (TUI + plain lines)
    _theme.set_theme(theme)

    # Rebuild the OfficeCLI adapter with the requested timeout.
    # Other adapters are constructed once in router._ADAPTERS but their
    # timeout is irrelevant (they don't subprocess).
    for a in get_adapters():
        if isinstance(a, OfficeCLIAdapter):
            a.timeout = officecli_timeout

    opts = RunOptions(
        input_root=input_dir,
        output_root=output,
        fmt=fmt.lower(),
        ocr=ocr,
        include_glob=list(include) if include else None,
        exclude_glob=list(exclude) if exclude else None,
        continue_on_error=not no_continue_on_error,
        write_okf_index=not no_okf_index,
        jobs=jobs,
        use_cache=not no_cache,
        obsidian_compat=obsidian_compat,
        enriched_index=enriched_index,
        write_log=write_log,
        write_bundle_manifest=write_bundle_manifest,
        dry_run=dry_run,
        json_output=json_output,
    )

    # Eng #34: cross-concept link inference (second pass)
    if crossref and not dry_run and opts.fmt in {"okf", "both"}:
        from .crossref import linkify_bundle
        n = linkify_bundle(opts.output_root / "okf")
        if n:
            print(f"  crossref: rewrote {n} file(s)", file=sys.stderr)

    # Eng #35: policy gate
    if policy is not None and not dry_run and opts.fmt in {"okf", "both"}:
        from .policy import Policy, evaluate
        pol = Policy.load(policy)
        findings = evaluate(pol, opts.output_root / "okf")
        if findings:
            for f in findings:
                print(
                    f"  policy violation: {f.file.name}: [{f.rule}] {f.message}",
                    file=sys.stderr,
                )
            print(
                f"  ✗ policy gate failed: {len(findings)} violation(s)",
                file=sys.stderr,
            )
            sys.exit(2)

    # Eng #32: git-backed bundle
    if git_commit_flag and not dry_run:
        from .git_commit import git_commit as do_git_commit
        rc, msg = do_git_commit(
            opts.output_root,
            message=git_commit_message,
            verify=git_commit_verify,
        )
        if rc != 0:
            print(f"  git-commit: {msg}", file=sys.stderr)
        else:
            print(f"  git-commit: {msg}", file=sys.stderr)

    use_tui = tui if tui is not None else sys.stderr.isatty() and sys.stdout.isatty()
    if use_tui:
        sys.exit(run_with_tui(opts))

    # Plain mode: print progress to stderr, line-buffered
    import sys as _sys
    err = _sys.stderr
    err.write(f"headcleaner {__version__}\n")
    err.write(f"  input:  {input_dir}\n")
    err.write(f"  output: {output}\n")
    err.write(f"  format: {fmt}\n")
    if dry_run:
        err.write("  mode:   DRY RUN (no files will be written)\n")
    err.write("\n")
    err.flush()

    def hook(i: int, total: int, result) -> None:
        sym = {"ok": "✓", "skipped": "↷", "failed": "✗"}.get(result.status, "?")
        err.write(f"  [{i}/{total}] {sym} {result.engine or '-':>10}  {result.relpath}\n")
        err.flush()

    opts.on_progress = hook
    record = run_pipeline(opts)
    ok = sum(1 for r in record.results if r.status == "ok")
    skipped = sum(1 for r in record.results if r.status == "skipped")
    failed = sum(1 for r in record.results if r.status == "failed")
    err.write(f"\n✓ done  ok={ok}  skipped={skipped}  failed={failed}\n")
    if dry_run:
        err.write("(dry run — no files written)\n")
    else:
        err.write(f"manifest: {output}/manifest.json\n")
    sys.exit(0 if failed == 0 else 1)


@cli.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "okf", "both"], case_sensitive=False),
    default="both",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=Path("./out"),
    show_default=True,
)
@click.option("--ocr", is_flag=True, default=False)
@click.option(
    "--officecli-timeout",
    type=int,
    default=60,
    show_default=True,
)
@click.option("--include", "-i", multiple=True)
@click.option("--exclude", "-e", multiple=True)
@click.option("--jobs", "-j", type=int, default=1, show_default=True)
@click.option("--no-cache", is_flag=True, default=False)
@click.option("--no-continue-on-error", is_flag=True, default=False)
@click.option("--no-okf-index", is_flag=True, default=False)
@click.option(
    "--debounce-ms",
    type=int,
    default=500,
    show_default=True,
    help="Minimum interval (ms) between re-conversions when many files change at once.",
)
@click.option(
    "--webhook-url",
    default=None,
    help="POST the run manifest to this URL after each re-conversion.",
)
@click.option(
    "--theme",
    type=click.Choice(["neon", "light", "dark", "mono"], case_sensitive=False),
    default="neon",
    show_default=True,
    help="Eng #40: color palette for the TUI and plain-mode progress lines.",
)
def watch(
    ocr: bool,
    officecli_timeout: int,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    jobs: int,
    no_cache: bool,
    no_continue_on_error: bool,
    no_okf_index: bool,
    debounce_ms: int,
    webhook_url: str | None,
) -> None:
    """Watch INPUT_DIR for changes and re-convert automatically.

    Like `convert`, but runs forever until Ctrl+C. Each detected change
    triggers a re-conversion of the whole folder (incremental per-file
    conversion is a future enhancement; tracked as Batch 4).

    Optional webhook: --webhook-url <URL> POSTs the manifest.json after
    each run completes (useful for Slack/Discord notifications).
    """
    from .engines.officecli import OfficeCLIAdapter
    from .router import adapters as get_adapters
    from .webhook import post_webhook
    from .watch import watch_directory

    for a in get_adapters():
        if isinstance(a, OfficeCLIAdapter):
            a.timeout = officecli_timeout

    def on_run_complete(record) -> None:
        if webhook_url is not None:
            try:
                post_webhook(webhook_url, record)
            except Exception as e:
                print(f"  ⚠ webhook POST failed: {e}", file=sys.stderr)

    opts = RunOptions(
        input_root=input_dir,
        output_root=output,
        fmt=fmt.lower(),
        ocr=ocr,
        include_glob=list(include) if include else None,
        exclude_glob=list(exclude) if exclude else None,
        continue_on_error=not no_continue_on_error,
        write_okf_index=not no_okf_index,
        jobs=jobs,
        use_cache=not no_cache,
    )

    try:
        watch_directory(opts, debounce_ms=debounce_ms, on_run_complete=on_run_complete)
    except KeyboardInterrupt:
        pass


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
def attest(directory: Path) -> None:
    """Eng #36: compute an Attested Computations payload for a bundle."""
    from .attest import write_attestation
    out = write_attestation(directory)
    click.echo(f"Attestation written: {out}")


@cli.command()
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
def review(bundle: Path) -> None:
    """Eng #3: interactively review every `verified: human:pending` concept."""
    from .review import run_review_tui
    summary = run_review_tui(bundle)
    click.echo(
        f"reviewed: approved={summary['approved']} "
        f"rejected={summary['rejected']} "
        f"skipped={summary['skipped']} "
        f"quit={summary['quit']}"
    )


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
def glob(directory: Path) -> None:
    """Eng #44: launch the interactive glob REPL (stub: prints hint)."""
    from .glob_repl import launch_repl
    launch_repl(directory)


@cli.command()
def templates() -> None:
    """List supported formats and their engines."""
    from .router import registered_extensions

    click.echo("Supported formats (v0.1.0):")
    for ext in sorted(registered_extensions()):
        click.echo(f"  {ext}")
    click.echo("\nSee docs/FORMAT_MATRIX.md for the full engine × library table.")


@cli.command()
def agents() -> None:
    """List detected engines and their install status."""
    import shutil

    checks = [
        ("officecli", "Office (DOCX/XLSX/PPTX) — npm i -g @officecli/officecli"),
        ("tesseract", "OCR — choco install tesseract / brew install tesseract"),
        ("readpst", "PST (optional) — install libpst"),
    ]
    for name, desc in checks:
        status = "✓ installed" if shutil.which(name) else "✗ missing"
        click.echo(f"  {status:>13}  {name:<10}  {desc}")


@cli.command(name="lint")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--strict", is_flag=True, default=False, help="Treat warnings as errors.")
@click.option("--no-color", is_flag=True, default=False, help="Disable ANSI color output.")
@click.option("--fix", "do_fix", is_flag=True, default=False, help="Auto-repair safe issues to <DIR>.fixed/.")
@click.option("--fix-out", type=click.Path(path_type=Path), default=None, help="Override --fix output directory.")
def lint_cmd(directory: Path, strict: bool, no_color: bool, do_fix: bool, fix_out: Path | None) -> None:
    """Review converted Markdown / OKF for formatting issues.

    Run after `headcleaner convert` to catch structural problems before
    committing the bundle.
    """
    import sys

    from .lint import main as lint_main

    if no_color or not sys.stdout.isatty():
        # Force the linter to skip ANSI by monkey-patching its color helpers
        from . import lint as _lint_mod
        from . import theme as _theme_mod

        _theme_mod.paint = lambda text, *_a, **_kw: text  # type: ignore[assignment]
        _lint_mod.Finding.format = lambda self: (  # type: ignore[assignment]
            f"  {self.severity.value:<7} "
            f"{self.file.name}:{self.line if self.line else ''}  "
            f"[{self.rule}]  {self.message}"
        )

    argv = [str(directory)]
    if strict:
        argv.append("--strict")
    if no_color:
        argv.append("--no-color")
    if do_fix:
        argv.append("--fix")
    if fix_out is not None:
        argv.extend(["--fix-out", str(fix_out)])
    raise SystemExit(lint_main(argv))


def main(args: list[str] | None = None) -> int:
    """Entry point used by `headcleaner` console script."""
    try:
        cli.main(args=args, standalone_mode=False)
        return 0
    except click.ClickException as e:
        e.show()
        return e.exit_code
    except click.exceptions.Exit as e:
        return e.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
