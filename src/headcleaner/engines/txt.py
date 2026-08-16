"""Plain text adapter — .txt files.

Strategy:
  1. detect encoding with chardet
  2. read with errors='replace'
  3. emit as a fenced code block so formatting (leading spaces, alignment) survives
"""
from __future__ import annotations

from pathlib import Path

import chardet

from .base import Adapter


class TxtAdapter(Adapter):
    name = "txt"
    extensions = {".txt"}

    def __init__(self, sample_bytes: int = 64 * 1024) -> None:
        self.sample_bytes = sample_bytes

    def extract(self, source: Path, *, progress=None) -> dict:
        raw = source.read_bytes()
        detected = chardet.detect(raw[: self.sample_bytes]) or {}
        encoding = detected.get("encoding") or "utf-8"
        # chardet can return "ascii" — that's a strict subset of utf-8
        if encoding.lower() in {"ascii", "utf-8", "utf8"}:
            text = raw.decode("utf-8", errors="replace")
        else:
            try:
                text = raw.decode(encoding, errors="replace")
            except (LookupError, UnicodeDecodeError):
                text = raw.decode("utf-8", errors="replace")

        body_md = f"```text\n{text.rstrip()}\n```\n"

        return {
            "title": source.stem,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": ".txt",
                "encoding": encoding,
                "byte_size": len(raw),
            },
            "attachments": [],
        }
