#!/usr/bin/env python
"""Enforce the repository documentation audit contract.

The active documentation surface is the root README plus Markdown under docs/, with
historical docs/_archive excluded. A phase passes only when every active document has
a recorded, evidenced decision and every local path/fragment reference resolves.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ARCHIVE_DIRECTORY = "_archive"
AUDIT_DIRECTORY = Path("docs/development/phase-audits")
ACTIVE_PHASE_PATH = Path("docs/development/ACTIVE_PHASE.md")
ALLOWED_DISPOSITIONS = {"updated", "reviewed", "not-applicable"}
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:")
MARKDOWN_LINK = re.compile(r"!?\[[^]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"(?<!!)\[([^]]+)\]\[([^]]+)\]")
REFERENCE_DEFINITION = re.compile(r"^\s*\[([^]]+)\]:\s*(\S+)", re.MULTILINE)
HTML_LINK = re.compile(r"<(?:a|img)\b[^>]+?(?:href|src)=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
HTML_ANCHOR = re.compile(r"<(?:a|h[1-6])\b[^>]+?\bid=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)


def active_documents(root: Path) -> list[Path]:
    """Return the tracked active documentation surface in deterministic order."""
    documents: list[Path] = []
    readme = root / "README.md"
    if readme.exists():
        documents.append(readme)
    docs_root = root / "docs"
    if docs_root.exists():
        documents.extend(
            path
            for path in docs_root.rglob("*.md")
            if ARCHIVE_DIRECTORY not in path.relative_to(docs_root).parts
        )
    return sorted(documents, key=lambda path: path.relative_to(root).as_posix())


def github_slug(value: str) -> str:
    """Approximate GitHub's heading fragment slugging for local validation."""
    value = unquote(value).strip().lower()
    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"[^\w\- ]", "", value)
    return re.sub(r"[ -]+", "-", value).strip("-")


def document_anchors(path: Path) -> set[str]:
    """Collect ATX headings and explicit HTML ids, including duplicate heading suffixes."""
    counts: Counter[str] = Counter()
    anchors: set[str] = set()
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match is None:
            continue
        base = github_slug(match.group(1))
        counts[base] += 1
        anchors.add(base if counts[base] == 1 else f"{base}-{counts[base] - 1}")
    anchors.update(unquote(anchor) for anchor in HTML_ANCHOR.findall(text))
    return anchors


def markdown_targets(text: str) -> list[str]:
    """Extract inline, reference-style, and simple HTML link targets."""
    targets = list(MARKDOWN_LINK.findall(text))
    references = {
        label.strip().lower(): target.strip()
        for label, target in REFERENCE_DEFINITION.findall(text)
    }
    for label, reference in REFERENCE_LINK.findall(text):
        target = references.get((reference or label).strip().lower())
        if target is not None:
            targets.append(target)
    targets.extend(HTML_LINK.findall(text))
    return targets


def normalize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def resolve_target(root: Path, source: Path, path_part: str) -> Path:
    if path_part.startswith("/"):
        return (root / path_part.lstrip("/")).resolve()
    if path_part.startswith("docs/"):
        return (root / path_part).resolve()
    return (source.parent / path_part).resolve()


def validate_links(root: Path, documents: list[Path]) -> list[str]:
    """Return every missing local target or Markdown fragment in active docs."""
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in documents:
        text = source.read_text(encoding="utf-8")
        for raw_target in markdown_targets(text):
            target = normalize_target(raw_target)
            if not target or target.startswith(EXTERNAL_PREFIXES):
                continue
            path_part, marker, fragment = target.partition("#")
            destination = (
                source.resolve() if not path_part else resolve_target(root, source, path_part)
            )
            source_label = source.relative_to(root).as_posix()
            if not destination.exists():
                errors.append(f"{source_label} -> {target}: missing target")
                continue
            if marker and destination.suffix.lower() == ".md":
                anchors = anchor_cache.setdefault(destination, document_anchors(destination))
                if github_slug(fragment) not in anchors and unquote(fragment) not in anchors:
                    errors.append(f"{source_label} -> {target}: missing anchor")
    return errors


def audit_path(root: Path, phase: str) -> Path:
    return root / AUDIT_DIRECTORY / f"{phase}.json"


def write_audit_template(root: Path, documents: list[Path], phase: str) -> Path:
    """Create an incomplete, exhaustive audit record for a new phase."""
    path = audit_path(root, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "phase": phase,
                "status": "in_progress",
                "entries": [
                    {
                        "path": document.relative_to(root).as_posix(),
                        "disposition": "pending",
                        "evidence": "",
                    }
                    for document in documents
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def validate_audit(root: Path, documents: list[Path], phase: str) -> list[str]:
    """Ensure a completed phase audit covers every active document exactly once."""
    path = audit_path(root, phase)
    if not path.exists():
        return [f"missing phase audit: {path.relative_to(root).as_posix()}"]
    try:
        audit = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid phase audit JSON: {exc.msg}"]
    errors: list[str] = []
    if audit.get("phase") != phase:
        errors.append(f"audit phase mismatch: expected {phase}")
    if audit.get("status") != "complete":
        errors.append("documentation audit status is not complete")
    entries = audit.get("entries")
    if not isinstance(entries, list):
        return [*errors, "audit entries must be a list"]
    expected = {document.relative_to(root).as_posix() for document in documents}
    seen: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append("audit entry lacks a path")
            continue
        entry_path = entry["path"]
        if entry_path in seen:
            errors.append(f"audit duplicates: {entry_path}")
        seen[entry_path] = entry
    for missing in sorted(expected - set(seen)):
        errors.append(f"audit coverage missing: {missing}")
    for unexpected in sorted(set(seen) - expected):
        errors.append(f"audit coverage stale: {unexpected}")
    for entry_path, entry in sorted(seen.items()):
        if entry.get("disposition") not in ALLOWED_DISPOSITIONS:
            errors.append(f"audit disposition invalid: {entry_path}")
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append(f"audit evidence missing: {entry_path}")
    return errors


def active_phase(root: Path) -> str | None:
    path = root / ACTIVE_PHASE_PATH
    if not path.exists():
        return None
    phase = path.read_text(encoding="utf-8").strip()
    return phase or None


def staged_paths(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "could not read staged paths")
    return {path.replace("\\", "/") for path in result.stdout.splitlines() if path}


def validate_staged_commit(root: Path, phase: str) -> list[str]:
    """Require phase audit and development history updates in every staged commit."""
    try:
        staged = staged_paths(root)
    except RuntimeError as exc:
        return [str(exc)]
    if not staged:
        return ["no staged files to validate"]
    required = {
        "DEVELOPMENT_HISTORY.md",
        audit_path(root, phase).relative_to(root).as_posix(),
    }
    return [
        f"staged commit is missing required documentation update: {path}"
        for path in sorted(required - staged)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate active-doc links and phase documentation audits."
    )
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Repository root (default: cwd)."
    )
    parser.add_argument(
        "--phase", help="Phase name whose complete documentation audit is required."
    )
    parser.add_argument(
        "--staged", action="store_true", help="Also validate the staged commit documentation gate."
    )
    parser.add_argument(
        "--write-audit-template",
        metavar="PHASE",
        help="Write an exhaustive, incomplete audit template for PHASE.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    documents = active_documents(root)
    if args.write_audit_template is not None:
        if args.phase is not None or args.staged:
            parser.error("--write-audit-template cannot be combined with --phase or --staged")
        path = write_audit_template(root, documents, args.write_audit_template)
        print(f"WROTE_AUDIT_TEMPLATE={path.relative_to(root).as_posix()}")
        print(f"ACTIVE_DOCS={len(documents)}")
        return 0
    errors = validate_links(root, documents)
    phase = args.phase
    if args.staged and phase is None:
        phase = active_phase(root)
        if phase is None:
            errors.append(f"missing active phase: {ACTIVE_PHASE_PATH.as_posix()}")
    if phase is not None:
        errors.extend(validate_audit(root, documents, phase))
    if args.staged and phase is not None:
        errors.extend(validate_staged_commit(root, phase))

    print(f"ACTIVE_DOCS={len(documents)}")
    if phase is not None and not any("audit" in error for error in errors):
        print("DOCUMENTATION_AUDIT=complete")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
