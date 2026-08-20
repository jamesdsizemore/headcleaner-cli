"""Non-destructive exact and near-duplicate document-family candidates."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


@dataclass(frozen=True)
class DocumentFamily:
    id: str
    exact_members: tuple[str, ...]
    candidate_members: tuple[dict[str, Any], ...]
    signals: dict[str, Any]
    algorithm_version: str = "1"


def _score(left: str, right: str) -> float:
    try:
        from rapidfuzz.fuzz import ratio

        return ratio(left, right) / 100
    except ImportError:
        return SequenceMatcher(None, left, right).ratio()


def analyze_documents(
    documents: Iterable[dict[str, str]], *, threshold: float = 0.8
) -> list[DocumentFamily]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    records = sorted(documents, key=lambda item: item["id"])
    by_hash: dict[str, list[str]] = {}
    for record in records:
        by_hash.setdefault(record["sha256"], []).append(record["id"])
    families: list[DocumentFamily] = []
    for sha, members in sorted(by_hash.items()):
        if len(members) > 1:
            families.append(
                DocumentFamily(
                    hashlib.sha256(("exact\0" + sha).encode()).hexdigest(),
                    tuple(members),
                    (),
                    {"source_sha256": sha},
                )
            )
    candidates: list[dict[str, Any]] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["sha256"] == right["sha256"]:
                continue
            title_score = _score(
                left.get("title", "").casefold(), right.get("title", "").casefold()
            )
            content_score = _score(
                left.get("text", "").casefold(), right.get("text", "").casefold()
            )
            path_score = _score(left.get("path", "").casefold(), right.get("path", "").casefold())
            combined = (title_score + content_score + path_score) / 3
            if combined > threshold:
                candidates.append(
                    {
                        "left_id": left["id"],
                        "right_id": right["id"],
                        "title_score": title_score,
                        "content_score": content_score,
                        "path_score": path_score,
                        "combined_score": combined,
                        "evidence": "normalized title/content/path",
                    }
                )
    if candidates:
        families.append(
            DocumentFamily(
                hashlib.sha256(b"candidates/v1").hexdigest(),
                (),
                tuple(candidates),
                {"threshold": threshold},
            )
        )
    return families
