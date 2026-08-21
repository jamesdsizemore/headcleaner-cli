from pathlib import Path

root = Path(r"C:/Users/james/developer/headcleaner-cli")

run_path = root / "src/headcleaner/run.py"
run_text = run_path.read_text(encoding="utf-8")
run_old = '    fmt: str = "both"  # "md" | "okf" | "both"\n    ocr: bool = False\n    include_glob: list[str] | None = None\n'
run_new = '    fmt: str = "both"  # "md" | "okf" | "both"\n    ocr: bool = False\n    ocr_profile: str = "balanced"\n    ocr_languages: tuple[str, ...] = ()\n    include_glob: list[str] | None = None\n'
assert run_text.count(run_old) == 1
run_path.write_text(run_text.replace(run_old, run_new), encoding="utf-8")

cli_path = root / "src/headcleaner/cli.py"
cli_text = cli_path.read_text(encoding="utf-8")
decorator_old = '@click.option("--ocr", is_flag=True, default=False, help="Enable Tesseract OCR for scanned PDFs.")\n@click.option(\n    "--officecli-timeout",\n'
decorator_new = '@click.option("--ocr", is_flag=True, default=False, help="Enable Tesseract OCR for scanned PDFs.")\n@click.option(\n    "--ocr-profile",\n    type=click.Choice(["fast", "balanced", "archival", "handwriting_experimental"]),\n    default="balanced",\n    show_default=True,\n    help="OCR preprocessing and Tesseract segmentation profile.",\n)\n@click.option("--ocr-lang", default=None, help="Comma-separated Tesseract language codes.")\n@click.option(\n    "--officecli-timeout",\n'
assert cli_text.count(decorator_old) == 1
cli_text = cli_text.replace(decorator_old, decorator_new)
signature_old = '    output: Path,\n    ocr: bool,\n    officecli_timeout: int,\n'
signature_new = '    output: Path,\n    ocr: bool,\n    ocr_profile: str,\n    ocr_lang: str | None,\n    officecli_timeout: int,\n'
assert cli_text.count(signature_old) == 1
cli_text = cli_text.replace(signature_old, signature_new)
options_old = '        fmt=fmt.lower(),\n        ocr=ocr,\n        include_glob=list(include) if include else None,\n'
options_new = '        fmt=fmt.lower(),\n        ocr=ocr,\n        ocr_profile=ocr_profile,\n        ocr_languages=tuple(code.strip() for code in (ocr_lang or "").split(",") if code.strip()),\n        include_glob=list(include) if include else None,\n'
assert cli_text.count(options_old) == 1
cli_path.write_text(cli_text.replace(options_old, options_new), encoding="utf-8")
