"""Tests for the OKF frontmatter JSON Schema (v0.13.x bonus)."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from headcleaner.normalize import CanonicalDoc

SCHEMA_PATH = Path("docs/schemas/okf-frontmatter.schema.json")


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_is_valid_draft7(schema):
    """The schema file itself must parse as a Draft-7 schema."""
    jsonschema.Draft7Validator.check_schema(schema)


def test_real_headcleaner_frontmatter_validates(schema):
    """A frontmatter dict from `CanonicalDoc.to_okf_frontmatter()` validates."""
    doc = CanonicalDoc(
        title="Sample Document",
        source_format="pdf",
        source_uri="file:///tmp/sample.pdf",
        source_sha256="a" * 64,
        body_md="# Hello",
        source_path=Path("/tmp/sample.pdf"),
        source_relpath=Path("sample.pdf"),
        source_size_bytes=1024,
        engine="pdf",
    )
    fm = doc.to_okf_frontmatter()
    jsonschema.validate(fm, schema)


def test_obsidian_compat_validates(schema):
    doc = CanonicalDoc(
        title="x",
        source_format="pdf",
        source_uri="file:///x.pdf",
        source_sha256="b" * 64,
        body_md="x",
        source_path=Path("/x.pdf"),
        source_relpath=Path("x.pdf"),
        source_size_bytes=1,
        engine="pdf",
    )
    fm = doc.to_okf_frontmatter(obsidian_compat=True)
    jsonschema.validate(fm, schema)


def test_missing_type_rejected(schema):
    """`type` is OKF-required — must be present."""
    bad = {"title": "x"}  # no 'type'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_missing_title_rejected(schema):
    bad = {"type": "Document"}  # no 'title'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_invalid_status_rejected(schema):
    bad = {
        "type": "Document",
        "title": "x",
        "status": "some-other-value",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_valid_statuses_accepted(schema):
    for status in ["unverified", "verified", "rejected", "deprecated"]:
        fm = {"type": "Document", "title": "x", "status": status}
        jsonschema.validate(fm, schema)


def test_bad_sha256_format_rejected(schema):
    bad = {
        "type": "Document",
        "title": "x",
        "sources": [{"uri": "file:///x", "kind": "file", "sha256": "not-hex"}],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_sources_array_required_min_1(schema):
    """The OKF spec requires at least one source for provenance."""
    bad = {
        "type": "Document",
        "title": "x",
        "sources": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_schema_documents_obsidian_fields(schema):
    """The 5 Obsidian-compat flat fields are documented in the schema."""
    expected = {"source", "sha256", "generated_by", "verified_by", "stale_on"}
    assert expected.issubset(schema["properties"].keys())
