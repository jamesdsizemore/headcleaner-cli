"""CSV adapter — comma/tab/semicolon separated values.

Detects the dialect (delimiter, quoting) using stdlib `csv.Sniffer`,
then renders the file as a GitHub-flavored Markdown table. The first
non-empty row is the header.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .base import Adapter, AdapterError


class CsvAdapter(Adapter):
    name = "csv"
    extensions = {".csv", ".tsv"}

    def __init__(self, sample_bytes: int = 64 * 1024) -> None:
        self.sample_bytes = sample_bytes

    def extract(self, source: Path) -> dict:
        raw = source.read_bytes()[: self.sample_bytes].decode("utf-8", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(raw, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel  # safe default: comma

        rows: list[list[str]] = []
        try:
            with source.open("r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.reader(f, dialect=dialect)
                for row in reader:
                    rows.append(row)
        except (OSError, UnicodeDecodeError) as e:
            raise AdapterError(f"csv read failed on {source}: {e}") from e

        if not rows:
            return {
                "title": source.stem,
                "body_md": "(empty CSV)\n",
                "metadata": {"engine": self.name, "source_format": source.suffix.lower()},
                "attachments": [],
            }

        header = rows[0]
        body = rows[1:]

        # Trim trailing empty rows
        while body and all(not c.strip() for c in body[-1]):
            body.pop()

        md_table = self._to_markdown(header, body)
        title = source.stem

        return {
            "title": title,
            "body_md": md_table + "\n",
            "metadata": {
                "engine": self.name,
                "source_format": source.suffix.lower(),
                "delimiter": dialect.delimiter,
                "rows": len(body),
                "cols": len(header),
            },
            "attachments": [],
        }

    @staticmethod
    def _to_markdown(header: list[str], body: list[list[str]]) -> str:
        """Render rows as a GFM table; escape pipes inside cell values."""
        def cell(value: str) -> str:
            if value is None:
                return ""
            return str(value).replace("|", "\\|").replace("\n", " ").strip()

        if not header or all(not h for h in header):
            return "_CSV with no header row detected._\n"

        cols = len(header)
        lines = [
            "| " + " | ".join(cell(h) for h in header) + " |",
            "| " + " | ".join("---" for _ in range(cols)) + " |",
        ]
        for row in body:
            # Pad/truncate row to header length
            cells = (row + [""] * cols)[:cols]
            lines.append("| " + " | ".join(cell(c) for c in cells) + " |")

        # Stats footer
        return "\n".join(lines) + f"\n\n_{len(body)} rows × {cols} columns_\n"


class JsonAdapter(Adapter):
    """JSON adapter — pretty-prints the parsed JSON in a fenced block."""

    name = "json"
    extensions = {".json"}

    def __init__(self, indent: int = 2, max_bytes: int = 50 * 1024 * 1024) -> None:
        self.indent = indent
        self.max_bytes = max_bytes

    def extract(self, source: Path) -> dict:
        size = source.stat().st_size
        if size > self.max_bytes:
            raise AdapterError(
                f"JSON file too large ({size} bytes > {self.max_bytes}); "
                f"increase --max-json-bytes or pre-process"
            )

        raw = source.read_bytes().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise AdapterError(f"invalid JSON in {source}: {e}") from e

        # Pretty-print
        pretty = json.dumps(data, indent=self.indent, ensure_ascii=False, sort_keys=True)

        # Title: prefer first string key, fall back to file stem
        title = self._title_from_json(data) or source.stem

        # If the JSON is a small flat object, surface top-level fields
        # in the body above the fenced block for quick scanning
        if isinstance(data, dict) and data and all(isinstance(v, (str, int, float, bool, type(None))) for v in data.values()):
            summary = "\n".join(f"- **{k}**: `{json.dumps(v, ensure_ascii=False)}`" for k, v in data.items())
            body_md = f"{summary}\n\n```json\n{pretty}\n```\n"
        else:
            body_md = f"```json\n{pretty}\n```\n"

        return {
            "title": title,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": ".json",
                "byte_size": size,
                "top_level_type": type(data).__name__,
            },
            "attachments": [],
        }

    @staticmethod
    def _title_from_json(data) -> str | None:
        if isinstance(data, dict):
            for key in ("title", "name", "label", "id"):
                v = data.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        return None
