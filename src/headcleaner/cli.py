"""headcleaner CLI entrypoint.

Subcommands (all shipped as of v0.14.0):
  convert    Convert a folder to Markdown / OKF / both
  templates  List supported formats and engines
  agents     List detected engines and their install status
  config     Show / set per-user defaults
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import click

from . import __version__
from .i18n import SUPPORTED_LOCALES, set_locale, tr
from .policy import AttachmentLimits
from .run import RunOptions, run_pipeline
from .tui import run_with_tui


def _select_language(_ctx: click.Context, _param: click.Parameter, value: str | None) -> str | None:
    """Activate locale before Click renders help or invokes any subcommand."""
    set_locale(value)
    return value


@click.group()
@click.option(
    "--lang",
    type=click.Choice(("en", "es", "zh-CN"), case_sensitive=False),
    default=None,
    callback=_select_language,
    is_eager=True,
    expose_value=False,
    help=f"Interface language (default: $HEADCLEANER_LANG or {SUPPORTED_LOCALES[0]}).",
)
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
    "--ocr-profile",
    type=click.Choice(["fast", "balanced", "archival", "handwriting_experimental"]),
    default="balanced",
    show_default=True,
    help="OCR preprocessing and Tesseract segmentation profile.",
)
@click.option("--ocr-lang", default=None, help="Comma-separated Tesseract language codes.")
@click.option(
    "--attachment-max-depth",
    type=click.IntRange(min=1),
    default=AttachmentLimits().max_depth,
    show_default=True,
    help="Maximum recursive attachment depth.",
)
@click.option(
    "--attachment-max-members",
    type=click.IntRange(min=1),
    default=AttachmentLimits().max_members,
    show_default=True,
    help="Maximum attachment members per run.",
)
@click.option(
    "--attachment-max-member-bytes",
    type=click.IntRange(min=1),
    default=AttachmentLimits().max_member_bytes,
    show_default=True,
    help="Maximum decompressed bytes for one attachment.",
)
@click.option(
    "--attachment-max-total-bytes",
    type=click.IntRange(min=1),
    default=AttachmentLimits().max_total_bytes,
    show_default=True,
    help="Maximum total decompressed attachment bytes per run.",
)
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
@click.option(
    "--no-continue-on-error", is_flag=True, default=False, help="Stop on the first failure."
)
@click.option(
    "--tui/--no-tui",
    default=None,
    help="Force / disable the animated TUI. Default: auto-detect TTY.",
)
@click.option(
    "--no-okf-index", is_flag=True, default=False, help="Skip writing OKF directory index.md files."
)
@click.option(
    "--clean",
    "clean_md",
    is_flag=True,
    default=False,
    help="Apply the 12-stage heuristic cleanup pipeline (any2md-inspired) to each extracted body before emission.",
)
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
    "--dedupe-threshold",
    default=0.8,
    type=click.FloatRange(0, 1),
    show_default=True,
    help="Contract 2.5: retain near-duplicate candidates only above this score.",
)
@click.option(
    "--git-commit",
    "git_commit_flag",
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
    "--engine", "requested_engine", default=None, help="Use a specific extraction engine."
)
@click.option(
    "--no-fallback", is_flag=True, default=False, help="Do not attempt alternate engines."
)
@click.option(
    "--allow-fallback",
    is_flag=True,
    default=False,
    help="Permit declared fallback engines after typed extraction failures.",
)
@click.option(
    "--allow-network",
    is_flag=True,
    default=False,
    help="Permit engines that explicitly require network access.",
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
    ocr_profile: str,
    ocr_lang: str | None,
    attachment_max_depth: int,
    attachment_max_members: int,
    attachment_max_member_bytes: int,
    attachment_max_total_bytes: int,
    officecli_timeout: int,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    jobs: int,
    no_cache: bool,
    no_continue_on_error: bool,
    tui: bool | None,
    no_okf_index: bool,
    obsidian_compat: bool,
    clean_md: bool,
    enriched_index: bool,
    write_log: bool,
    write_bundle_manifest: bool,
    dry_run: bool,
    json_output: bool,
    requested_engine: str | None,
    no_fallback: bool,
    allow_fallback: bool,
    allow_network: bool,
    theme: str,
    crossref: bool,
    policy: Path | None,
    dedupe_threshold: float,
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
    if no_fallback and allow_fallback:
        raise click.UsageError("--no-fallback and --allow-fallback cannot be used together")
    requested_ocr_languages = tuple(
        code.strip() for code in (ocr_lang or "").split(",") if code.strip()
    )
    try:
        attachment_limits = AttachmentLimits(
            max_depth=attachment_max_depth,
            max_members=attachment_max_members,
            max_member_bytes=attachment_max_member_bytes,
            max_total_bytes=attachment_max_total_bytes,
        )
    except ValueError as error:
        raise click.UsageError(f"invalid attachment limits: {error}") from error
    if ocr:
        from .ocr import get_profile, installed_languages, validate_requested_languages

        profile = get_profile(ocr_profile)
        executable = shutil.which("tesseract")
        if executable is None:
            raise click.UsageError(
                "OCR_TESSERACT_UNAVAILABLE: install Tesseract or run without --ocr"
            )
        try:
            available_languages = installed_languages(executable)
        except (OSError, subprocess.SubprocessError) as error:
            raise click.UsageError(
                f"OCR_TESSERACT_UNAVAILABLE: could not query installed languages ({type(error).__name__})"
            ) from error
        requested_ocr_languages = validate_requested_languages(
            requested_ocr_languages or profile.requested_languages,
            available_languages,
        )

    # Rebuild the OfficeCLI adapter with the requested timeout.
    # Other adapters are constructed once in router._ADAPTERS but their
    # timeout is irrelevant (they don't subprocess).
    for a in get_adapters():
        if isinstance(a, OfficeCLIAdapter):
            a.timeout = officecli_timeout

    claim_policy = None
    if policy is not None:
        from .policy import Policy

        claim_policy = Policy.load(policy)

    opts = RunOptions(
        input_root=input_dir,
        output_root=output,
        fmt=fmt.lower(),
        ocr=ocr,
        ocr_profile=ocr_profile,
        ocr_languages=requested_ocr_languages,
        attachment_limits=attachment_limits,
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
        dedupe_threshold=dedupe_threshold,
        claim_suppressions=claim_policy.claim_suppressions if claim_policy else {},
        claim_scope=claim_policy.claim_scope if claim_policy else "bundle",
        requested_engine=requested_engine,
        allow_fallback=allow_fallback,
        allow_network=allow_network,
        clean_md=clean_md,
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

        pol = claim_policy or Policy.load(policy)
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
    err.write(tr("headcleaner {version}").format(version=__version__) + "\n")
    err.write(f"  {tr('input')}:  {input_dir}\n")
    err.write(f"  {tr('output')}: {output}\n")
    err.write(f"  {tr('format')}: {fmt}\n")
    if dry_run:
        err.write("  " + tr("mode: DRY RUN (no files will be written)") + "\n")
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
    err.write(f"\n✓ {tr('done')}  ok={ok}  skipped={skipped}  failed={failed}\n")
    if dry_run:
        err.write(f"({tr('dry run — no files written')})\n")
    else:
        err.write(f"{tr('manifest')}: {output}/manifest.json\n")
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
    no_okf_index: bool,
    debounce_ms: int,
    webhook_url: str | None,
) -> None:
    """Watch INPUT_DIR for changes and re-convert automatically.

    Like `convert`, but runs forever until Ctrl+C. Each detected change
    triggers a re-conversion of the whole folder (incremental per-file
    conversion is tracked for a future enhancement; not yet implemented).

    Optional webhook: --webhook-url <URL> POSTs the manifest.json after
    each run completes (useful for Slack/Discord notifications).
    """
    from .engines.officecli import OfficeCLIAdapter
    from .router import adapters as get_adapters
    from .watch import watch_directory
    from .webhook import post_webhook

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
@click.option(
    "--private-key",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="PEM ed25519 key for signing the Merkle root.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path for attestation.json (default: <bundle>/attestation.json).",
)
def attest(directory: Path, private_key: Path | None, output: Path | None) -> None:
    """Eng #36: compute an Attested Computations payload for a bundle (Merkle root + optional ed25519 signature)."""  # noqa: E501
    from .attest import write_attestation

    out = write_attestation(directory, output=output, private_key_path=private_key)
    payload = json.loads(out.read_text(encoding="utf-8"))
    click.echo(f"Attestation written: {out}")
    click.echo(f"  concepts: {payload['concept_count']}")
    click.echo(f"  merkle_root: {payload['merkle_root']}")
    if payload.get("signature"):
        click.echo(f"  signature: {payload['signature'][:32]}...")
        click.echo(f"  public_key: {payload['public_key']}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--public-key",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="PEM ed25519 public key for verifying the signature.",
)
@click.option(
    "--attestation",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to attestation.json (default: <bundle>/attestation.json).",
)
def verify(directory: Path, public_key: Path | None, attestation: Path | None) -> None:
    """Eng #36: verify an attestation against the bundle contents."""
    from .verify import verify_attestation

    attest_path = attestation or (directory / "attestation.json")
    result = verify_attestation(directory, attest_path, public_key_path=public_key)
    sig = result.get("signature_valid")
    if result.get("valid") and sig is not False:
        click.echo(
            f"OK: bundle matches attestation (merkle_valid={result['merkle_valid']}, signature_valid={sig})"
        )
    else:
        click.echo(f"FAIL: {result.get('errors')}")
        raise SystemExit(1)


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
    """Eng #44: launch the interactive glob REPL."""
    from .glob_repl import launch_repl

    launch_repl(directory)


@cli.command()
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory to verify as writable (defaults to a temp dir probe).",
)
def doctor(output_dir: Path | None) -> None:
    """Run diagnostic checks: Python, OfficeCLI, OCR, output perms, registry."""
    from .doctor import exit_code as doctor_exit
    from .doctor import render_text, run_all

    results = run_all(output_dir=output_dir)
    click.echo(render_text(results))
    sys.exit(doctor_exit(results))


@cli.command()
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8765, show_default=True, type=int, help="Bind port.")
def serve(bundle: Path, host: str, port: int) -> None:
    """Eng #22: serve an OKF bundle over HTTP for browsing + search."""
    from .serve import run_serve

    run_serve(bundle, host=host, port=port)


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
@click.option(
    "--fix", "do_fix", is_flag=True, default=False, help="Auto-repair safe issues to <DIR>.fixed/."
)
@click.option(
    "--fix-out",
    type=click.Path(path_type=Path),
    default=None,
    help="Override --fix output directory.",
)
def lint_cmd(
    directory: Path, strict: bool, no_color: bool, do_fix: bool, fix_out: Path | None
) -> None:
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


@cli.command(name="chunks")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--rebuild", is_flag=True, default=False)
@click.option("--json", "json_output", is_flag=True, default=False)
def chunks_cmd(bundle: Path, rebuild: bool, json_output: bool) -> None:
    """Write or inspect deterministic cited chunks for BUNDLE."""
    from .chunking import read_chunks, rebuild_chunks

    chunks = rebuild_chunks(bundle) if rebuild else read_chunks(bundle)
    payload = [chunk.to_dict() for chunk in chunks]
    click.echo(
        json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if json_output
        else f"{len(payload)} chunks"
    )


@cli.group(name="index")
def index_cmd() -> None:
    """Build the rebuildable local search index."""


@index_cmd.command(name="rebuild")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
def index_rebuild_cmd(bundle: Path) -> None:
    from .index import rebuild_index

    click.echo(rebuild_index(bundle))


@index_cmd.command(name="update")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
def index_update_cmd(bundle: Path) -> None:
    """Atomically refresh the cited local index from current bundle derivatives."""
    from .index import update_index

    click.echo(update_index(bundle))


@index_cmd.command(name="embed")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--provider",
    type=str,
    required=True,
)
@click.option("--model", required=True)
@click.option("--endpoint")
@click.option("--qdrant-endpoint")
@click.option("--qdrant-collection", default="headcleaner")
@click.option("--recreate-qdrant-collection", is_flag=True, default=False)
@click.option("--allow-network", is_flag=True, default=False)
@click.option("--timeout", default=30.0, type=float)
def index_embed_cmd(
    bundle: Path,
    provider: str,
    model: str,
    endpoint: str | None,
    qdrant_endpoint: str | None,
    qdrant_collection: str,
    recreate_qdrant_collection: bool,
    allow_network: bool,
    timeout: float,
) -> None:
    """Explicitly cache vectors for chunk text; no provider is selected implicitly."""
    from .chunking import read_chunks
    from .embeddings import (
        HttpEmbeddingProvider,
        LocalSentenceTransformerProvider,
        QdrantVectorStore,
        VectorCache,
    )

    if provider == "openai_compatible_http":
        embedding_provider = HttpEmbeddingProvider(endpoint or "", model, timeout=timeout)
    elif provider == "local_sentence_transformer":
        embedding_provider = LocalSentenceTransformerProvider(Path(model), model)
    else:
        from .plugins import load_embedding_providers

        embedding_provider = load_embedding_providers()[0].get(provider)
        if embedding_provider is None:
            raise click.BadParameter(
                f"unknown embedding provider: {provider}", param_hint="--provider"
            )

    if qdrant_endpoint and not allow_network:
        raise click.UsageError("Qdrant requires --allow-network")

    chunks = read_chunks(bundle)
    vectors = embedding_provider.embed(
        [chunk.text for chunk in chunks], allow_network=allow_network
    )
    cache = VectorCache(bundle)
    qdrant = None
    if qdrant_endpoint:
        qdrant = QdrantVectorStore(qdrant_endpoint, qdrant_collection)
        if vectors:
            qdrant.ensure_compatible(
                dimension=len(vectors[0]),
                model_id=embedding_provider.model_id,
                recreate=recreate_qdrant_collection,
            )
    for chunk, vector in zip(chunks, vectors, strict=True):
        cache.put(
            chunk.text,
            chunk_id=chunk.id,
            provider=embedding_provider.name,
            model_id=embedding_provider.model_id,
            dimension=len(vector),
            version=embedding_provider.version,
            vector=vector,
        )
        if qdrant:
            qdrant.upsert(
                chunk_id=chunk.id,
                vector=vector,
                metadata={
                    "concept_id": chunk.concept_id,
                    "source_sha256": chunk.source_sha256,
                    "citation": chunk.citation,
                },
                model_id=embedding_provider.model_id,
            )
    pruned = cache.prune_orphans({chunk.id for chunk in chunks})
    qdrant_pruned = qdrant.prune_orphans({chunk.id for chunk in chunks}) if qdrant else 0
    click.echo(
        f"cached {len(vectors)} vectors; pruned {pruned} local and {qdrant_pruned} Qdrant orphans"
    )


@cli.command(name="search")
@click.argument("query")
@click.option(
    "--bundle", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--tag")
@click.option("--type", "concept_type")
@click.option("--status")
@click.option("--path", "path_prefix")
@click.option("--source-sha")
@click.option("--limit", default=20, type=int)
@click.option("--json", "json_output", is_flag=True, default=False)
def search_cmd(
    query: str,
    bundle: Path,
    tag: str | None,
    concept_type: str | None,
    status: str | None,
    path_prefix: str | None,
    source_sha: str | None,
    limit: int,
    json_output: bool,
) -> None:
    """Search local chunks with deterministic FTS5 ranking and filters."""
    from .search import SearchQueryError, search

    try:
        hits = search(
            bundle,
            query,
            tag=tag,
            type=concept_type,
            status=status,
            path=path_prefix,
            source_sha=source_sha,
            limit=limit,
        )
    except (SearchQueryError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    rows = [hit.__dict__ for hit in hits]
    click.echo(
        json.dumps(rows, ensure_ascii=False, sort_keys=True)
        if json_output
        else "\n".join(f"{row['concept_path']}: {row['excerpt']}" for row in rows)
    )


@cli.command(name="graph")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--node")
@click.option("--depth", default=1, type=int)
@click.option(
    "--kind",
    type=click.Choice(
        [
            "contains",
            "cites",
            "mentions",
            "related_to",
            "duplicate_candidate",
            "conflicts_candidate",
        ]
    ),
    default=None,
)
@click.option("--policy", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "json_output", is_flag=True, default=False)
def graph_cmd(
    bundle: Path,
    node: str | None,
    depth: int,
    kind: str | None,
    policy: Path | None,
    json_output: bool,
) -> None:
    """Build and query evidence-linked graph data for BUNDLE."""
    from .graph import build_graph, filter_graph, query_graph, write_graph
    from .policy import Policy

    graph = build_graph(bundle)
    if policy:
        graph = filter_graph(graph, Policy.load(policy).graph_excluded_edge_kinds)
    write_graph(bundle, graph)
    if node:
        payload = query_graph(graph, node, depth=depth, kind=kind)
    else:
        payload = {
            "nodes": [item.__dict__ for item in graph.nodes],
            "edges": [item.__dict__ for item in graph.edges],
        }
    click.echo(
        json.dumps(payload, default=list, sort_keys=True)
        if json_output
        else f"{len(payload['nodes'])} nodes, {len(payload['edges'])} edges"
    )


@cli.command(name="claims")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--policy", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--json", "json_output", is_flag=True, default=False)
def claims_cmd(bundle: Path, policy: Path | None, json_output: bool) -> None:
    """List deterministic stale and potential-conflict candidates for BUNDLE."""
    from .chunking import read_chunks
    from .claims import analyze_claims
    from .policy import Policy

    claim_policy = Policy.load(policy) if policy else Policy()
    claims, findings = analyze_claims(
        [chunk.to_dict() for chunk in read_chunks(bundle)],
        suppressions=claim_policy.claim_suppressions,
        scope=claim_policy.claim_scope,
    )
    payload = {
        "claims": [claim.__dict__ for claim in claims],
        "findings": [finding.__dict__ for finding in findings],
    }
    click.echo(
        json.dumps(payload, default=list, sort_keys=True)
        if json_output
        else f"{len(findings)} findings"
    )


@cli.command(name="dedupe")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--threshold", default=0.8, type=float)
@click.option("--json", "json_output", is_flag=True, default=False)
def dedupe_cmd(bundle: Path, threshold: float, json_output: bool) -> None:
    """List exact and near-duplicate candidate families without mutating sources."""
    from .chunking import read_chunks
    from .dedupe import analyze_documents

    chunks = read_chunks(bundle)
    by_concept: dict[str, list] = {}
    for chunk in chunks:
        by_concept.setdefault(chunk.concept_id, []).append(chunk)
    families = analyze_documents(
        (
            {
                "id": path,
                "sha256": rows[0].source_sha256,
                "title": path,
                "text": "\n".join(row.text for row in rows),
                "path": path,
            }
            for path, rows in sorted(by_concept.items())
        ),
        threshold=threshold,
    )
    payload = [family.__dict__ for family in families]
    click.echo(
        json.dumps(payload, default=list, sort_keys=True)
        if json_output
        else f"{len(payload)} families"
    )


@cli.command(name="diff")
@click.argument("left", type=click.Path(exists=True, path_type=Path))
@click.argument("right", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format", "output_format", type=click.Choice(["text", "json", "md"]), default="text"
)
@click.option("--include-unchanged", is_flag=True, default=False)
def diff_cmd(left: Path, right: Path, output_format: str, include_unchanged: bool) -> None:
    """Compare Markdown by typed blocks and canonical frontmatter/trust metadata."""
    from .diff import diff_markdown, render_markdown_report

    result = diff_markdown(
        left.read_text(encoding="utf-8"),
        right.read_text(encoding="utf-8"),
        left_ref=str(left),
        right_ref=str(right),
        include_unchanged=include_unchanged,
    )
    payload = {
        "left_ref": result.left_ref,
        "right_ref": result.right_ref,
        "summary": result.summary,
        "changes": [change.__dict__ for change in result.changes],
        "algorithm_version": result.algorithm_version,
    }
    if output_format == "json":
        click.echo(json.dumps(payload, default=list, sort_keys=True))
    elif output_format == "md":
        click.echo(render_markdown_report(result), nl=False)
    else:
        click.echo(json.dumps(payload["summary"], sort_keys=True))


@cli.command(name="sync")
@click.argument("input_root", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("output", type=click.Path(file_okay=False, path_type=Path))
@click.option("--dry-run", is_flag=True, default=True)
@click.option("--apply", "apply_changes", is_flag=True, default=False)
@click.option("--prune-generated", is_flag=True, default=False)
@click.option("--json", "json_output", is_flag=True, default=False)
def sync_cmd(
    input_root: Path,
    output: Path,
    dry_run: bool,
    apply_changes: bool,
    prune_generated: bool,
    json_output: bool,
) -> None:
    """Preview rename/deletion-safe bundle synchronization; apply is explicit."""
    from .sync import load_state, plan_sync, reconcile
    from .walk import sha256_of, walk

    sources = {
        source.relpath.as_posix(): source.sha256 or sha256_of(source.path)
        for source in walk(input_root)
    }
    try:
        if dry_run and not apply_changes and not prune_generated:
            plan = plan_sync(input_root, output)
        else:
            plan = reconcile(
                load_state(output),
                sources,
                output,
                dry_run=dry_run,
                apply=apply_changes,
                prune_generated=prune_generated,
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        json.dumps(plan, sort_keys=True)
        if json_output
        else "\n".join(f"{row['status']}: {row.get('path', row.get('from', ''))}" for row in plan)
    )


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


@cli.command(name="view")
@click.argument("bundle", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "-o",
    "--out",
    type=click.Path(path_type=Path),
    default=None,
    help="Output HTML path (default: <bundle>/viz.html).",
)
@click.option(
    "-t",
    "--title",
    default=None,
    help="Graph title shown in the header (default: parent/bundle dir name).",
)
@click.option(
    "-l",
    "--link",
    default=None,
    help="Optional source URL shown in the header (e.g. GitHub repo link).",
)
@click.option(
    "--layout",
    default=None,
    type=click.Choice(["cose", "concentric", "breadthfirst", "circle", "grid"]),
    help="Initial graph layout. Default: cose for small bundles, concentric for large.",
)
@click.option(
    "--max-nodes",
    type=int,
    default=None,
    help="Refuse to render bundles with more concepts than this (useful in CI).",
)
@click.option("--og-image", default=None, help="Absolute URL for the og:image social preview.")
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    default=False,
    help="Open the rendered viz.html in the default browser after writing.",
)
@click.option(
    "--serve",
    "serve_local",
    is_flag=True,
    default=False,
    help="Serve the rendered file on a local HTTP server after writing.",
)
@click.option("--host", default="127.0.0.1", help="--serve host (default: 127.0.0.1).")
@click.option("--port", type=int, default=8765, help="--serve port (default: 8765).")
@click.option(
    "--tui",
    "tui_mode",
    is_flag=True,
    default=False,
    help="Browse the bundle interactively in the terminal (whole-frame TUI).",
)
def view_cmd(
    bundle: Path,
    out: Path | None,
    title: str | None,
    link: str | None,
    layout: str | None,
    max_nodes: int | None,
    og_image: str | None,
    open_browser: bool,
    serve_local: bool,
    host: str,
    port: int,
    tui_mode: bool,
) -> None:
    """Render an OKF bundle as a self-contained interactive HTML graph.

    The output is one HTML file: concepts as graph nodes (colored by type,
    sized by body length), markdown links and `sources` as edges, and a
    wiki-style detail panel with rendered markdown, OKF v0.2 trust
    signals, "Links to" / "Cited by" backlinks, layout switcher, and
    per-type filter.

    No backend is required to view it — open the file in any browser.

    Adopts scaccogatto/okf-skills (MIT) as the rendering engine.
    """
    if tui_mode:
        from .okf_tui import run_tui

        raise SystemExit(run_tui(bundle))

    from .viewer import render

    out_path = out or (bundle / "viz.html")
    if out_path.is_dir():
        out_path = out_path / "viz.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n, e = render(
        bundle,
        out_path,
        title=title,
        link=link,
        layout=layout,
        og_image=og_image,
        max_nodes=max_nodes,
    )
    click.echo(f"rendered {n} concepts, {e} links -> {out_path}")

    if serve_local:
        import http.server
        import socketserver
        import threading
        import webbrowser

        def handler(*a, **kw):
            return http.server.SimpleHTTPRequestHandler(*a, directory=str(out_path.parent), **kw)

        with socketserver.TCPServer((host, port), handler) as httpd:
            url = f"http://{host}:{port}/{out_path.name}"
            click.echo(f"serving {url}  (Ctrl+C to stop)")
            if open_browser:
                threading.Timer(0.5, lambda: webbrowser.open(url)).start()
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                click.echo("stopped")
    elif open_browser:
        import webbrowser

        webbrowser.open(out_path.as_uri())


@cli.command(name="benchmark")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--baseline", type=click.Path(path_type=Path), default=None)
@click.option("--json", "json_output", is_flag=True, default=False)
@click.option("--update-baseline", is_flag=True, default=False)
def benchmark(
    input_dir: Path, baseline: Path | None, json_output: bool, update_baseline: bool
) -> None:
    """Measure attributed fixture conversion quality against explicit expectations."""
    from .benchmark import run_benchmark

    try:
        report = run_benchmark(input_dir, baseline=baseline, update_baseline=update_baseline)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if json_output:
        click.echo(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        summary = report["summary"]
        click.echo(f"benchmark: {summary['passed']}/{summary['fixture_count']} fixtures passed")


@cli.command(name="mcp")
@click.argument("bundles", nargs=-1, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--name",
    "named_bundles",
    multiple=True,
    help="Assign names to bundles in positional order (e.g. --name wiki --name notes).",
)
def mcp_cmd(bundles: tuple[Path, ...], named_bundles: tuple[str, ...]) -> None:
    """Run headcleaner as an MCP server (stdio).

    Each BUNDLE argument is an OKF bundle directory. The first one becomes
    the default target for tool calls. Use the ``name=path`` form (or
    positional --name) to give bundles explicit names.

    The required ``mcp`` dependency installs with headcleaner. Restore a missing
    locked environment with::

        uv sync --locked

    Then register with an MCP client (e.g. Claude Code)::

        claude mcp add headcleaner -- headcleaner mcp ./out/okf
    """
    from . import mcp as mcp_mod

    args: list[str] = []
    if named_bundles:
        for name, bundle in zip(named_bundles, bundles, strict=False):
            args.append(f"{name}={bundle}")
        args.extend(str(b) for b in bundles[len(named_bundles) :])
    else:
        args.extend(str(b) for b in bundles)
    sys.exit(mcp_mod.main(args))


@cli.command(name="notion-import")
@click.argument("export", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(file_okay=False, path_type=Path))
def notion_import(export: Path, output: Path) -> None:
    """Eng #31: reverse a Notion workspace export into an OKF bundle."""
    from .notion import detect_export, import_notion_export

    counts = detect_export(export)
    click.echo(
        f"Detected {counts['databases']} databases, {counts['pages']} pages, {counts['files']} files in {export}"
    )
    n = import_notion_export(export, output)
    click.echo(f"Imported {n} concepts to {output}")


@cli.command(name="verify-render")
@click.argument("input", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
@click.option("--json", "json_output", is_flag=True, default=False)
def verify_render_cmd(
    input: Path, output: Path, output_dir: Path | None, json_output: bool
) -> None:
    """Verify rendered fidelity for existing source and output artifacts."""
    from dataclasses import asdict

    from .render_verify import verify_render

    report = verify_render(input, output, output_dir=output_dir)
    if json_output:
        click.echo(json.dumps(asdict(report), sort_keys=True))
    else:
        click.echo(f"{report.status}: {report.renderer or 'no compatible renderer'}")
