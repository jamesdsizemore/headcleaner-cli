#!/usr/bin/env python3
"""Portable documentation-governance verifier. Standard library only."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT_RECORDS = (
    "BACKLOG.md",
    "ISSUES.md",
    "MEMORY.md",
    "DEVELOPMENT_HISTORY.md",
    "DEPENDENCIES.md",
    "PINS.md",
    "AGENTS.md",
    "CLAUDE.md",
)
DEFAULT_AUDIT_DIRECTORY = Path("docs/development/phase-audits")
DEFAULT_EXCLUDES = (Path("docs/_archive"),)
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\[([^\]]+)\]")
REFERENCE_DEF = re.compile(r"^\s*\[([^\]]+)\]:\s*(\S+)", re.MULTILINE)
HTML_TARGET = re.compile(r"<(?:a|img)\b[^>]*(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", re.I)
HTML_ANCHOR = re.compile(r"<(?:a|span|div|h[1-6])\b[^>]*(?:id|name)\s*=\s*[\"']([^\"']+)[\"']", re.I)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def normalize_anchor(text: str) -> str:
    """Approximate GitHub heading slugs, including duplicate suffixes elsewhere."""
    text = re.sub(r"`([^`]*)`", r"\1", unquote(text)).strip().lower()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    result = set(HTML_ANCHOR.findall(text))
    seen: Counter[str] = Counter()
    for match in HEADING.finditer(text):
        base = normalize_anchor(match.group(1))
        if not base:
            continue
        suffix = seen[base]
        result.add(base if suffix == 0 else f"{base}-{suffix}")
        seen[base] += 1
    return result


def active_documents(root: Path, docs_dir: Path) -> list[Path]:
    documents: list[Path] = []
    readme = root / "README.md"
    if readme.is_file():
        documents.append(readme)
    if docs_dir.is_dir():
        for candidate in sorted(docs_dir.rglob("*.md")):
            relative = candidate.relative_to(root)
            if any(relative.is_relative_to(excluded) for excluded in DEFAULT_EXCLUDES):
                continue
            documents.append(candidate)
    return documents


def _target_value(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split(maxsplit=1)[0] if raw else raw


def links(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    values = [_target_value(match.group(1)) for match in INLINE_LINK.finditer(text)]
    values.extend(match.group(1) for match in HTML_TARGET.finditer(text))
    definitions = {key.strip().casefold(): value for key, value in REFERENCE_DEF.findall(text)}
    for label, reference in REFERENCE_LINK.findall(text):
        key = (reference or label).strip().casefold()
        if key in definitions:
            values.append(_target_value(definitions[key]))
    return values


def is_external(target: str) -> bool:
    return bool(re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", target, re.I))


def resolve_target(root: Path, source: Path, value: str) -> tuple[Path, str]:
    target, separator, fragment = value.partition("#")
    target = unquote(target.split("?", 1)[0])
    fragment = unquote(fragment)
    if not target:
        return source, fragment
    if target.startswith("/"):
        return root / target.lstrip("/"), fragment
    return (source.parent / target).resolve(), fragment


def validate_links(root: Path, documents: list[Path]) -> list[str]:
    errors: list[str] = []
    for source in documents:
        try:
            source_links = links(source)
        except UnicodeDecodeError:
            errors.append(f"{source.relative_to(root)}: not valid UTF-8")
            continue
        for value in source_links:
            if not value or is_external(value):
                continue
            target, fragment = resolve_target(root, source, value)
            relative_source = source.relative_to(root)
            if not target.is_file():
                errors.append(f"{relative_source}: missing target {value}")
                continue
            if fragment and target.suffix.lower() == ".md" and fragment not in anchors(target):
                errors.append(f"{relative_source}: missing anchor #{fragment} in {target.relative_to(root)}")
    return errors


def audit_path(root: Path, phase: str, audit_directory: Path) -> Path:
    return root / audit_directory / f"{phase}.json"


def write_audit_template(root: Path, phase: str, documents: list[Path], audit_directory: Path) -> Path:
    destination = audit_path(root, phase, audit_directory)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite existing audit: {destination}")
    payload = {
        "schema_version": 1,
        "phase": phase,
        "status": "in_progress",
        "documents": [
            {
                "path": document.relative_to(root).as_posix(),
                "disposition": "pending",
                "evidence": "",
            }
            for document in documents
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination


def validate_records(root: Path) -> list[str]:
    return [f"missing required development record: {name}" for name in ROOT_RECORDS if not (root / name).is_file()]


def validate_audit(root: Path, phase: str, documents: list[Path], audit_directory: Path) -> list[str]:
    destination = audit_path(root, phase, audit_directory)
    if not destination.is_file():
        return [f"missing phase audit: {destination.relative_to(root)}"]
    try:
        audit = json.loads(destination.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid phase audit JSON: {exc}"]

    errors: list[str] = []
    if audit.get("schema_version") != 1:
        errors.append("phase audit schema_version must be 1")
    if audit.get("phase") != phase:
        errors.append(f"phase audit names {audit.get('phase')!r}, expected {phase!r}")
    if audit.get("status") != "complete":
        errors.append("phase audit status must be 'complete'")
    entries = audit.get("documents")
    if not isinstance(entries, list):
        return errors + ["phase audit documents must be a list"]

    expected = {document.relative_to(root).as_posix() for document in documents}
    actual: list[str] = []
    allowed = {"updated", "reviewed", "not-applicable"}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"audit document entry {index} must be an object")
            continue
        path = entry.get("path")
        actual.append(path if isinstance(path, str) else "")
        if entry.get("disposition") not in allowed:
            errors.append(f"audit entry {path!r} has invalid disposition")
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"audit entry {path!r} lacks concrete evidence")
    duplicates = sorted(path for path, count in Counter(actual).items() if path and count > 1)
    if duplicates:
        errors.append("audit has duplicate paths: " + ", ".join(duplicates))
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    if missing:
        errors.append("audit missing active documents: " + ", ".join(missing))
    if unexpected:
        errors.append("audit references non-active documents: " + ", ".join(unexpected))
    return errors


def active_phase(root: Path, active_phase_file: Path) -> str:
    path = root / active_phase_file
    if not path.is_file():
        raise ValueError(f"missing active phase file: {active_phase_file}")
    value = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", value):
        raise ValueError("active phase must contain only lowercase letters, digits, '.', '_' or '-'")
    return value


def staged_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError("cannot inspect staged files; run inside a Git repository")
    return {line.replace("\\", "/") for line in result.stdout.splitlines() if line}


def validate_staged(root: Path, phase: str, audit_directory: Path) -> list[str]:
    staged = staged_paths(root)
    required = {"DEVELOPMENT_HISTORY.md", audit_path(root, phase, audit_directory).relative_to(root).as_posix()}
    missing = sorted(required - staged)
    return ["staged commit lacks required documentation evidence: " + ", ".join(missing)] if missing else []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIRECTORY)
    parser.add_argument("--active-phase-file", type=Path, default=Path("docs/development/ACTIVE_PHASE"))
    parser.add_argument("--phase")
    parser.add_argument("--write-audit-template", metavar="PHASE")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    documents = active_documents(root, root / args.docs_dir)
    errors = validate_links(root, documents)

    if args.write_audit_template:
        if args.phase or args.staged:
            parser.error("--write-audit-template cannot be combined with --phase or --staged")
        try:
            destination = write_audit_template(root, args.write_audit_template, documents, args.audit_dir)
        except FileExistsError as exc:
            errors.append(str(exc))
        else:
            print(f"WROTE_AUDIT_TEMPLATE={destination.relative_to(root).as_posix()}")

    phase = args.phase
    if args.staged:
        try:
            phase = active_phase(root, args.active_phase_file)
        except ValueError as exc:
            errors.append(str(exc))
    if phase:
        errors.extend(validate_records(root))
        errors.extend(validate_audit(root, phase, documents, args.audit_dir))
        if args.staged and not errors:
            errors.extend(validate_staged(root, phase, args.audit_dir))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"ACTIVE_DOCS={len(documents)}")
    if phase:
        print(f"PHASE_AUDIT={phase}: complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
