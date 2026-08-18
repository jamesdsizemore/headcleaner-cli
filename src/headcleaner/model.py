"""Typed document elements shared by adapters, normalization, and emitters."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

ELEMENT_KINDS = frozenset(
    {
        "heading",
        "paragraph",
        "list",
        "table",
        "image",
        "code",
        "quote",
        "attachment_ref",
        "page_break",
    }
)
_LOCATION_KEYS = frozenset({"page", "start", "end"})


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _json_safe(value: object) -> bool:
    try:
        json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return False
    return True


@dataclass(frozen=True)
class Element:
    id: str
    kind: str
    ordinal: int
    text: str
    source_location: dict[str, int | None] | None = None
    attributes: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.kind not in ELEMENT_KINDS:
            raise ValueError(f"invalid element kind: {self.kind}")
        if self.ordinal < 0:
            raise ValueError("element ordinal must be non-negative")
        if self.source_location is not None:
            if set(self.source_location) - _LOCATION_KEYS or any(
                value is not None and not isinstance(value, int)
                for value in self.source_location.values()
            ):
                raise ValueError("invalid source_location")
        if self.attributes is not None and not _json_safe(self.attributes):
            raise ValueError("element attributes must be JSON-safe")

    @classmethod
    def create(
        cls,
        source_sha: str,
        kind: str,
        ordinal: int,
        text: str,
        *,
        source_location: dict[str, int | None] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Element:
        normalized = _normalized(text)
        digest = hashlib.sha256(
            f"{source_sha}\0{kind}\0{ordinal}\0{normalized}".encode()
        ).hexdigest()
        return cls(digest, kind, ordinal, text, source_location, attributes)
