"""Schema validation tests for HeadCleaner attestation payloads (Contract 3.5)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from headcleaner import __version__
from headcleaner.attest import (
    build_attestation,
    build_in_toto_statement,
)

SCHEMA_PATH = Path("docs/schemas/attestation.schema.json")


def _make_bundle(tmp_path: Path) -> Path:
    """Build a minimal bundle with OKF sources provenance."""
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\n"
        'sources:\n  - uri: file://inbox/alpha.txt\n    kind: file\n    sha256: "'
        + "1" * 64
        + '"\n---\nHello world\n',
        encoding="utf-8",
    )
    (b / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\n"
        'sources:\n  - uri: file://inbox/beta.txt\n    kind: file\n    sha256: "'
        + "2" * 64
        + '"\n---\nAnother concept\n',
        encoding="utf-8",
    )
    (b / "index.md").write_text("# Index\n", encoding="utf-8")
    (b / "log.md").write_text("# Bundle history\n", encoding="utf-8")
    return b


def test_attestation_schema_is_well_formed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)


def test_attestation_schema_accepts_unsigned_attestation(tmp_path: Path) -> None:
    """A freshly built attestation must validate against the schema."""
    bundle = _make_bundle(tmp_path)
    payload = build_attestation(bundle)

    # build_attestation must populate schema_version, timestamp, engines.
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(payload, schema)


def test_attestation_schema_accepts_in_toto_statement(tmp_path: Path) -> None:
    """The in-toto projection must remain stable + contain source/output sets."""
    bundle = _make_bundle(tmp_path)
    stmt = build_in_toto_statement(build_attestation(bundle))

    assert stmt["_type"] == "https://in-toto.io/Statement/v1"
    assert stmt["predicateType"] == "https://headcleaner.dev/attestation/v1"
    sources = stmt["predicate"]["sources"]
    outputs = stmt["predicate"]["outputs"]
    assert sources, "in-toto predicate must carry source provenance"
    assert outputs, "in-toto predicate must carry output SHA set"
    # Both must be bundle-relative, sorted, and free of absolute paths.
    paths_s = [s["path"] for s in sources]
    paths_o = [o["path"] for o in outputs]
    assert paths_s == sorted(paths_s)
    assert paths_o == sorted(paths_o)
    for p in paths_s + paths_o:
        assert not p.startswith("/"), p
        assert "\\" not in p, p


def test_attestation_schema_rejects_absolute_source_path(tmp_path: Path) -> None:
    """Source paths must not be absolute; the schema rejects leading '/'."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = {
        "tool": "headcleaner",
        "version": __version__,
        "bundle_root": "x",
        "concept_count": 1,
        "concepts": {"a.md": "f" * 64},
        "source_provenance": {
            "a.md": [{"path": "/etc/passwd", "sha256": "a" * 64}],
        },
        "merkle_root": "0" * 64,
        "schema_version": "1",
        "timestamp": "2026-08-21T00:00:00Z",
        "engines": [],
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_attestation_schema_rejects_unsigned_review_claim(tmp_path: Path) -> None:
    """The schema must reject any field that implies human review/approval."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = {
        "tool": "headcleaner",
        "version": __version__,
        "bundle_root": "x",
        "concept_count": 0,
        "concepts": {},
        "source_provenance": {},
        "merkle_root": "0" * 64,
        "schema_version": "1",
        "timestamp": "2026-08-21T00:00:00Z",
        "engines": [],
        # The schema uses additionalProperties: false so a review claim is rejected.
        "verified_by_human": True,
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_attestation_schema_requires_engine_records(tmp_path: Path) -> None:
    """Attestations must record engine capability/version per Contract 3.5."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = {
        "tool": "headcleaner",
        "version": __version__,
        "bundle_root": "x",
        "concept_count": 0,
        "concepts": {},
        "source_provenance": {},
        "merkle_root": "0" * 64,
        "schema_version": "1",
        "timestamp": "2026-08-21T00:00:00Z",
        # Missing engines → must fail validation.
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


# ---------------------------------------------------------------------------
# Real in-toto Envelope round-trip (Contract 3.5 dependency-safe test gate)
# ---------------------------------------------------------------------------


def test_emitted_in_toto_statement_loads_through_in_toto_envelope(tmp_path: Path) -> None:
    """The statement written by `write_in_toto_statement` must round-trip
    cleanly through the official `in-toto` library DSSE Envelope.

    `Envelope.get_payload()` is link/layout-specific; we decode the raw
    payload bytes ourselves and verify our Statement survives the DSSE
    wrapping without losing the source/output SHA sets.
    """
    from in_toto.models.metadata import Envelope

    from headcleaner.attest import (
        build_in_toto_dsse_envelope,
        build_in_toto_statement,
        write_in_toto_statement,
    )

    bundle = _make_bundle(tmp_path)
    stmt = build_in_toto_statement(build_attestation(bundle))

    envelope = build_in_toto_dsse_envelope(stmt)
    assert envelope.payload_type == "application/vnd.in-toto+json"
    # Payload must round-trip and equal the canonical statement bytes.
    reloaded_stmt = json.loads(envelope.payload.decode("utf-8"))
    assert reloaded_stmt == stmt
    assert reloaded_stmt["_type"] == "https://in-toto.io/Statement/v1"
    assert reloaded_stmt["predicateType"] == "https://headcleaner.dev/attestation/v1"
    assert "sources" in reloaded_stmt["predicate"]
    assert "outputs" in reloaded_stmt["predicate"]

    # File round-trip: dump → load → payload matches.
    out_path = tmp_path / "stmt.intoto.json"
    write_in_toto_statement(stmt, out_path)
    from_disk = Envelope.load(str(out_path))
    assert from_disk.payload_type == "application/vnd.in-toto+json"
    assert json.loads(from_disk.payload.decode("utf-8")) == stmt


def test_in_toto_envelope_round_trip_carries_source_and_output_sha_sets(
    tmp_path: Path,
) -> None:
    """The in-toto Envelope must preserve the bundle-relative source/output
    SHA sets across a full serialise/deserialise round-trip.
    """
    from in_toto.models.metadata import Envelope

    from headcleaner.attest import (
        build_in_toto_dsse_envelope,
        build_in_toto_statement,
        write_in_toto_statement,
    )

    bundle = _make_bundle(tmp_path)
    stmt = build_in_toto_statement(build_attestation(bundle))

    out_path = tmp_path / "stmt.intoto.json"
    write_in_toto_statement(stmt, out_path)

    envelope = Envelope.load(str(out_path))
    pred = json.loads(envelope.payload.decode("utf-8"))["predicate"]

    sources = pred["sources"]
    outputs = pred["outputs"]
    assert [s["path"] for s in sources] == sorted(s["path"] for s in sources)
    assert [o["path"] for o in outputs] == sorted(o["path"] for o in outputs)
    for entry in sources + outputs:
        assert not entry["path"].startswith("/"), entry
        assert "\\" not in entry["path"], entry
