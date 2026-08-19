"""Tests for the new format adapters (md, csv, json)."""

from __future__ import annotations

import json

import pytest

from headcleaner.engines.csv_json import CsvAdapter, JsonAdapter
from headcleaner.engines.md import MdAdapter


def test_md_adapter_extracts_h1_title(tmp_path) -> None:
    f = tmp_path / "note.md"
    f.write_text("# Hello World\n\nThis is the body.\n", encoding="utf-8")
    out = MdAdapter().extract(f)
    assert out["title"] == "Hello World"
    assert "Hello World" in out["body_md"]
    assert "This is the body" in out["body_md"]
    assert out["metadata"]["engine"] == "md"


def test_md_adapter_preserves_existing_frontmatter(tmp_path) -> None:
    f = tmp_path / "note.md"
    f.write_text(
        "---\nauthor: alice\n---\n\n# Body\n\nParagraph.\n",
        encoding="utf-8",
    )
    out = MdAdapter().extract(f)
    # Body should NOT include the frontmatter (normalize will re-emit it)
    assert not out["body_md"].startswith("---")
    assert "Body" in out["body_md"]


def test_md_adapter_falls_back_to_filename(tmp_path) -> None:
    f = tmp_path / "README.md"
    f.write_text("Just a paragraph, no heading.\n", encoding="utf-8")
    out = MdAdapter().extract(f)
    assert out["title"] == "README"


def test_csv_adapter_basic(tmp_path) -> None:
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,92\nBob,87\n", encoding="utf-8")
    out = CsvAdapter().extract(f)
    assert out["title"] == "data"
    body = out["body_md"]
    assert "| name | score |" in body
    assert "| --- | --- |" in body
    assert "| Alice | 92 |" in body
    assert "| Bob | 87 |" in body
    assert "2 rows × 2 columns" in body
    assert out["tabular_assets"] == [
        {
            "kind": "csv",
            "ordinal": 0,
            "columns": ["name", "score"],
            "rows": [["Alice", "92"], ["Bob", "87"]],
            "provenance": {"engine": "csv", "delimiter": ","},
        }
    ]


def test_csv_adapter_handles_pipe_in_value(tmp_path) -> None:
    f = tmp_path / "data.csv"
    f.write_text("name,note\nalice,hello|world\n", encoding="utf-8")
    out = CsvAdapter().extract(f)
    assert "hello\\|world" in out["body_md"]


def test_csv_adapter_empty(tmp_path) -> None:
    f = tmp_path / "empty.csv"
    f.write_text("", encoding="utf-8")
    out = CsvAdapter().extract(f)
    assert "empty" in out["body_md"].lower()


def test_json_adapter_basic(tmp_path) -> None:
    f = tmp_path / "config.json"
    f.write_text('{"name": "test", "version": 1}', encoding="utf-8")
    out = JsonAdapter().extract(f)
    assert out["title"] == "test"
    assert "```json" in out["body_md"]
    parsed = json.loads(out["body_md"].split("```json\n")[1].split("\n```")[0])
    assert parsed["name"] == "test"


def test_json_adapter_flat_object_renders_summary(tmp_path) -> None:
    f = tmp_path / "config.json"
    f.write_text('{"name": "svc", "version": "1.2.3", "enabled": true}', encoding="utf-8")
    out = JsonAdapter().extract(f)
    assert "**name**" in out["body_md"]
    assert "**version**" in out["body_md"]
    assert "1.2.3" in out["body_md"]


def test_json_adapter_invalid_json_raises(tmp_path) -> None:
    from headcleaner.engines.base import AdapterError

    f = tmp_path / "bad.json"
    f.write_text("{not: valid, json}", encoding="utf-8")
    with pytest.raises(AdapterError):
        JsonAdapter().extract(f)


def test_json_adapter_title_picks_first_known_key(tmp_path) -> None:
    f = tmp_path / "pkg.json"
    f.write_text('{"id": "my-package", "version": "0.1.0"}', encoding="utf-8")
    out = JsonAdapter().extract(f)
    assert out["title"] == "my-package"
