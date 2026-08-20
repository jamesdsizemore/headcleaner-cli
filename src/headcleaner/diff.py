"""Typed-element semantic diffs; never use raw Markdown lines as source of truth."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import yaml

from .model import Element

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class ElementChange:
    kind: str
    status: str
    left_element_id: str | None
    right_element_id: str | None
    before: str | None
    after: str | None
    citation: dict[str, Any] | None


@dataclass(frozen=True)
class DiffResult:
    left_ref: str
    right_ref: str
    summary: dict[str, int]
    changes: tuple[ElementChange, ...]
    algorithm_version: str = "1"


def diff_elements(
    left: Iterable[Element],
    right: Iterable[Element],
    *,
    left_ref: str,
    right_ref: str,
    include_unchanged: bool = False,
) -> DiffResult:
    remaining = {item.id: item for item in right}
    changes: list[ElementChange] = []
    for item in left:
        other = remaining.pop(item.id, None)
        if other is None:
            candidates = [
                candidate for candidate in remaining.values() if candidate.kind == item.kind
            ]
            other = max(
                candidates,
                key=lambda candidate: SequenceMatcher(None, item.text, candidate.text).ratio(),
                default=None,
            )
            if other is not None:
                remaining.pop(other.id)
        if other is None:
            changes.append(
                ElementChange(
                    item.kind, "removed", item.id, None, item.text, None, item.source_location
                )
            )
        elif item.text != other.text:
            changes.append(
                ElementChange(
                    item.kind,
                    "modified",
                    item.id,
                    other.id,
                    item.text,
                    other.text,
                    other.source_location,
                )
            )
        elif item.ordinal != other.ordinal:
            changes.append(
                ElementChange(
                    item.kind,
                    "moved",
                    item.id,
                    other.id,
                    item.text,
                    other.text,
                    other.source_location,
                )
            )
        elif include_unchanged:
            changes.append(
                ElementChange(
                    item.kind,
                    "unchanged",
                    item.id,
                    other.id,
                    item.text,
                    other.text,
                    other.source_location,
                )
            )
    for item in remaining.values():
        changes.append(
            ElementChange(item.kind, "added", None, item.id, None, item.text, item.source_location)
        )
    changes.sort(
        key=lambda change: (change.status, change.left_element_id or change.right_element_id or "")
    )
    summary = {
        status: sum(change.status == status for change in changes)
        for status in ("added", "removed", "modified", "moved", "unchanged")
    }
    return DiffResult(left_ref, right_ref, summary, tuple(changes))


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return None, text
    try:
        value = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        value = {"_invalid_frontmatter": match.group(1)}
    return json.dumps(value, ensure_ascii=False, sort_keys=True), text[match.end() :]


def _typed_markdown_elements(text: str, source_ref: str) -> list[Element]:
    elements: list[Element] = []
    for ordinal, block in enumerate(part.strip() for part in text.split("\n\n") if part.strip()):
        if re.match(r"^#{1,6}\s+", block):
            kind = "heading"
        elif block.lstrip().startswith("|"):
            kind = "table"
        elif block.startswith("```"):
            kind = "code"
        elif re.match(r"^(?:[-*+]\s|\d+\.\s)", block):
            kind = "list"
        elif re.match(r"^!?\[[^\]]*\]\([^)]+\)$", block):
            kind = "attachment_ref"
        else:
            kind = "paragraph"
        elements.append(Element.create(source_ref, kind, ordinal, block))
    return elements


def _table_cells(text: str) -> dict[tuple[int, int], str]:
    """Parse Markdown table cells by coordinate, excluding the alignment row."""
    cells: dict[tuple[int, int], str] = {}
    row = 0
    for line in text.splitlines():
        values = [value.strip() for value in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", value) for value in values):
            continue
        for column, value in enumerate(values):
            cells[(row, column)] = value
        row += 1
    return cells


def _expand_table_change(change: ElementChange) -> list[ElementChange]:
    if change.kind != "table" or change.status != "modified":
        return [change]
    left_cells = _table_cells(change.before or "")
    right_cells = _table_cells(change.after or "")
    cell_changes: list[ElementChange] = []
    for row, column in sorted(set(left_cells) | set(right_cells)):
        before = left_cells.get((row, column))
        after = right_cells.get((row, column))
        if before == after:
            continue
        status = (
            "modified"
            if before is not None and after is not None
            else ("added" if before is None else "removed")
        )
        suffix = f":r{row}c{column}"
        cell_changes.append(
            ElementChange(
                "table_cell",
                status,
                f"{change.left_element_id}{suffix}" if before is not None else None,
                f"{change.right_element_id}{suffix}" if after is not None else None,
                before,
                after,
                change.citation,
            )
        )
    return cell_changes or [change]


def diff_markdown(
    left_text: str,
    right_text: str,
    *,
    left_ref: str,
    right_ref: str,
    include_unchanged: bool = False,
) -> DiffResult:
    """Compare Markdown as typed blocks plus canonicalized frontmatter/trust metadata."""
    left_frontmatter, left_body = _split_frontmatter(left_text)
    right_frontmatter, right_body = _split_frontmatter(right_text)
    result = diff_elements(
        _typed_markdown_elements(left_body, left_ref),
        _typed_markdown_elements(right_body, right_ref),
        left_ref=left_ref,
        right_ref=right_ref,
        include_unchanged=include_unchanged,
    )
    changes = [
        cell_change for change in result.changes for cell_change in _expand_table_change(change)
    ]
    if left_frontmatter != right_frontmatter:
        changes.append(
            ElementChange(
                "frontmatter", "modified", None, None, left_frontmatter, right_frontmatter, None
            )
        )
    elif left_frontmatter is not None and include_unchanged:
        changes.append(
            ElementChange(
                "frontmatter", "unchanged", None, None, left_frontmatter, right_frontmatter, None
            )
        )
    changes.sort(key=lambda change: (change.status, change.kind, change.left_element_id or ""))
    summary = {
        status: sum(change.status == status for change in changes)
        for status in ("added", "removed", "modified", "moved", "unchanged")
    }
    return DiffResult(left_ref, right_ref, summary, tuple(changes))


def render_markdown_report(result: DiffResult) -> str:
    """Render a compact diff report that preserves both input source references."""
    lines = [
        "# headcleaner semantic diff",
        "",
        f"- Left source: `{result.left_ref}`",
        f"- Right source: `{result.right_ref}`",
        f"- Algorithm: `{result.algorithm_version}`",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {status} | {count} |" for status, count in result.summary.items())
    lines.extend(["", "| Kind | Status | Left | Right |", "|---|---|---|---|"])
    for change in result.changes:
        before = (change.before or "").replace("|", "\\|").replace("\n", "<br>")
        after = (change.after or "").replace("|", "\\|").replace("\n", "<br>")
        lines.append(f"| {change.kind} | {change.status} | {before} | {after} |")
    return "\n".join(lines) + "\n"
