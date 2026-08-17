"""Tests for the markdown and OKF emitters."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from headcleaner.emit import manifest as manifest_emit
from headcleaner.emit import markdown as md_emit
from headcleaner.emit import okf as okf_emit
from headcleaner.emit import okf_index
from headcleaner.normalize import normalize
from headcleaner.walk import SourceFile


def _make_doc(tmp_path: Path, name: str, body: str = "Hello world\n", engine: str = "txt"):
    """Create a CanonicalDoc whose source lives at tmp_path/name."""
    f = tmp_path / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    sf = SourceFile(path=f, relpath=Path(name), size_bytes=f.stat().st_size)
    return normalize(sf, {"title": name, "body_md": body}, engine=engine)


def _make_doc_with_relpath(tmp_path: Path, relpath: str, body: str = "x"):
    """Create a CanonicalDoc with an explicit relpath (used for subdirectory tests)."""
    f = tmp_path / relpath
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    sf = SourceFile(path=f, relpath=Path(relpath), size_bytes=f.stat().st_size)
    return normalize(sf, {"title": Path(relpath).name, "body_md": body}, engine="txt")


def test_markdown_emitter_writes_file(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path, "x.txt")
    out = md_emit.write(doc, tmp_path)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    assert m, "markdown file missing frontmatter"
    fm = yaml.safe_load(m.group(1))
    assert "title" in fm
    assert "engine" in fm
    assert "sha256" in fm


def test_okf_emitter_has_required_type(tmp_path: Path) -> None:
    doc = _make_doc(tmp_path, "x.txt")
    out = okf_emit.write(doc, tmp_path)
    text = out.read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    fm = yaml.safe_load(m.group(1))
    assert "type" in fm and fm["type"]
    assert fm["status"] == "unverified"
    assert fm["verified"] == "human:pending"


def test_okf_index_generates_index_md(tmp_path: Path) -> None:
    doc_a = _make_doc_with_relpath(tmp_path, "sub/a.txt", "a")
    doc_b = _make_doc_with_relpath(tmp_path, "sub/b.txt", "b")
    doc_c = _make_doc(tmp_path, "c.txt")
    okf_emit.write(doc_a, tmp_path)
    okf_emit.write(doc_b, tmp_path)
    okf_emit.write(doc_c, tmp_path)
    n = okf_index.generate(tmp_path)
    assert n >= 2  # root + sub
    assert (tmp_path / "index.md").exists()
    assert (tmp_path / "sub" / "index.md").exists()
    root_text = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "c" in root_text.lower()
    sub_text = (tmp_path / "sub" / "index.md").read_text(encoding="utf-8")
    assert "a" in sub_text.lower()
    assert "b" in sub_text.lower()


def test_okf_index_heading_is_clean(tmp_path: Path) -> None:
    doc_a = _make_doc_with_relpath(tmp_path, "sub/a.txt", "a")
    okf_emit.write(doc_a, tmp_path)
    okf_index.generate(tmp_path)
    text = (tmp_path / "sub" / "index.md").read_text(encoding="utf-8")
    # Heading must NOT be the broken literal "# ." we shipped earlier
    assert not text.startswith("# .")
    assert text.startswith("# ")


def test_manifest_writer_creates_valid_json(tmp_path: Path) -> None:
    import json

    record = manifest_emit.RunRecord(
        input_root=str(tmp_path),
        output_root=str(tmp_path),
        format="both",
        options={"ocr": False},
    )
    record.results = [
        manifest_emit.FileResult(
            source_path="/x.txt",
            relpath="x.txt",
            engine="txt",
            sha256="0" * 64,
            md_path="/x.md",
            okf_path="/x.okf.md",
            status="ok",
        )
    ]
    record.finish()
    p = manifest_emit.write(record, tmp_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["tool"] == "headcleaner"
    assert data["format"] == "both"
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "ok"
