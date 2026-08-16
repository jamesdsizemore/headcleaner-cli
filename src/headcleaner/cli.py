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
) -> None:
    """Convert every supported document under INPUT_DIR."""
    from .engines.officecli import OfficeCLIAdapter
    from .router import adapters as get_adapters

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
    )

    use_tui = tui if tui is not None else sys.stderr.isatty() and sys.stdout.isatty()
    if use_tui:
        sys.exit(run_with_tui(opts))

    # Plain mode: print progress to stderr, line-buffered
    import sys as _sys
    err = _sys.stderr
    err.write(f"headcleaner {__version__}\n")
    err.write(f"  input:  {input_dir}\n")
    err.write(f"  output: {output}\n")
    err.write(f"  format: {fmt}\n\n")
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
    err.write(f"manifest: {output}/manifest.json\n")
    sys.exit(0 if failed == 0 else 1)


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
