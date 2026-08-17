"""Normalize adapter output into a CanonicalDoc.

`CanonicalDoc` is the single intermediate representation the emitters consume.
It is independent of which engine produced the source.
"""

from __future__ import annotations

import hashlib
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .walk import SourceFile


@dataclass
class CanonicalDoc:
    """The single intermediate form shared between all adapters and emitters."""

    title: str
    body_md: str
    source_path: Path
    source_relpath: Path
    source_uri: str  # file:// absolute URI (OKF §4.1 `resource`)
    source_sha256: str
    source_size_bytes: int
    source_format: str  # e.g. ".docx", ".pdf"
    engine: str  # adapter name that produced this
    metadata: dict[str, Any] = field(default_factory=dict)
    attachments: list[dict] = field(default_factory=list)

    # OKF v0.2 trust family defaults (honest — see docs/OKF_NOTES.md)
    okf_type: str = "Document"
    okf_status: str = "unverified"
    okf_generated: str = ""
    okf_verified: str = "human:pending"
    okf_stale_after: str = ""

    def __post_init__(self) -> None:
        if not self.okf_generated:
            self.okf_generated = default_generated()
        if not self.okf_stale_after:
            self.okf_stale_after = default_stale_after()

    def to_okf_frontmatter(self, *, obsidian_compat: bool = False) -> dict[str, Any]:
        """Build the OKF frontmatter dict for this doc.

        When `obsidian_compat` is True, additional flat fields are added
        (`source`, `sha256`, `generated_by`, `verified_by`, `stale_on`)
        for cleaner Obsidian property rendering. The original OKF fields
        remain intact.
        """
        fm = {
            "type": self.okf_type,
            "title": self.title,
            "description": self._description(),
            "resource": self.source_uri,
            "tags": self._tags(),
            "status": self.okf_status,
            "stale_after": self.okf_stale_after,
            "sources": [
                {
                    "uri": self.source_uri,
                    "kind": "file",
                    "sha256": self.source_sha256,
                }
            ],
            "generated": self.okf_generated,
            "verified": self.okf_verified,
        }
        if obsidian_compat:
            sources = fm["sources"]
            if sources and isinstance(sources[0], dict):
                if sources[0].get("uri"):
                    fm["source"] = sources[0]["uri"]
                if sources[0].get("sha256"):
                    fm["sha256"] = sources[0]["sha256"]
            if fm.get("generated"):
                fm["generated_by"] = fm["generated"].replace(":", "_")
            if fm.get("verified"):
                fm["verified_by"] = fm["verified"].replace(":", "_")
            if fm.get("stale_after"):
                fm["stale_on"] = fm["stale_after"]
        return fm

    def to_md_frontmatter(self) -> dict[str, Any]:
        """Build the plain-Markdown frontmatter dict for this doc."""
        return {
            "title": self.title,
            "source": self.source_uri,
            "format": self.source_format,
            "engine": self.engine,
            "sha256": self.source_sha256,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def _description(self) -> str:
        """One-sentence summary: 'Document derived from <relpath> by <engine>'."""
        return f"Document derived from {self.source_relpath} via {self.engine}."

    def _tags(self) -> list[str]:
        """Tags: every path segment of relpath plus the file extension (no dot)."""
        parts = [p for p in self.source_relpath.parts if p not in (".", "..")]
        # Drop the filename, keep directories, plus the format tag
        tags = [p.lower() for p in parts[:-1]]
        if self.source_format:
            tags.append(self.source_format.lstrip(".").lower())
        return tags or ["document"]


def default_generated() -> str:
    """Build a producer tag in OKF §7 convention: human:<user> or process:<id>."""
    user = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    try:
        hostname = socket.gethostname().split(".")[0]
    except OSError:
        hostname = "localhost"
    return f"human:{user}@{hostname}"


def default_stale_after() -> str:
    """180 days from now, ISO date (OKF §5.2 freshness)."""
    return (datetime.now(timezone.utc) + timedelta(days=180)).strftime("%Y-%m-%d")


def normalize(source: SourceFile, adapter_dict: dict, engine: str) -> CanonicalDoc:
    """Adapter output dict → CanonicalDoc."""
    body_md = adapter_dict.get("body_md") or ""
    title = adapter_dict.get("title") or source.path.stem
    metadata = adapter_dict.get("metadata") or {}
    attachments = adapter_dict.get("attachments") or []

    sha = _sha256(source.path)

    abs_path = source.path.resolve()
    source_uri = abs_path.as_uri()  # file:///C:/.../foo.docx on Windows

    return CanonicalDoc(
        title=title,
        body_md=body_md,
        source_path=abs_path,
        source_relpath=source.relpath,
        source_uri=source_uri,
        source_sha256=sha,
        source_size_bytes=source.size_bytes,
        source_format=source.path.suffix.lower(),
        engine=engine,
        metadata=metadata,
        attachments=attachments,
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
