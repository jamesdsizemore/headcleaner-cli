"""Tests for the full Attested Computations implementation (Eng #36)."""

from __future__ import annotations

import pytest
import hashlib
from pathlib import Path

from headcleaner.attest import (
    canonical_hash,
    canonical_json_bytes,
    build_in_toto_statement,
    merkle_root,
    merkle_proof,
    build_attestation,
    verify_signature,
    verify_attestation,
)
from headcleaner import __version__


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    """Build a small bundle with 3 concepts, each carrying OKF sources provenance."""
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
    (b / "gamma.md").write_text(
        "---\ntype: Document\ntitle: Gamma\n"
        'sources:\n  - uri: file://inbox/gamma.txt\n    kind: file\n    sha256: "'
        + "3" * 64
        + '"\n---\nThird concept\n',
        encoding="utf-8",
    )
    (b / "index.md").write_text("# Index\n", encoding="utf-8")
    (b / "log.md").write_text("# Bundle history\n", encoding="utf-8")
    return b


def test_canonical_hash_is_stable(bundle_dir: Path) -> None:
    """canonical_hash returns the same SHA-256 for the same content."""
    a = canonical_hash(bundle_dir / "alpha.md")
    b = canonical_hash(bundle_dir / "alpha.md")
    assert a == b
    assert len(a) == 64  # SHA-256 hex


def test_canonical_hash_normalizes_line_endings(tmp_path: Path) -> None:
    """Line-ending normalization makes CRLF and LF inputs hash to the same value."""
    f = tmp_path / "f.md"
    f.write_bytes(b"line1\nline2\n")
    h_lf = canonical_hash(f)
    f.write_bytes(b"line1\r\nline2\r\n")
    h_crlf = canonical_hash(f)
    assert h_lf == h_crlf


def test_canonical_json_bytes_are_stable_for_key_order_and_whitespace() -> None:
    left = {"subject": [{"name": "bundle", "digest": {"sha256": "abc"}}], "version": 1}
    right = {"version": 1, "subject": [{"digest": {"sha256": "abc"}, "name": "bundle"}]}

    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert canonical_json_bytes(left) == (
        b'{"subject":[{"digest":{"sha256":"abc"},"name":"bundle"}],"version":1}'
    )


def test_merkle_root_single_hash() -> None:
    """With one leaf, the root is the leaf hash."""
    assert merkle_root(["abc123"]) == "abc123"


def test_merkle_root_empty() -> None:
    """Empty tree returns the SHA-256 of empty string."""
    import hashlib

    assert merkle_root([]) == hashlib.sha256(b"").hexdigest()


def test_merkle_root_deterministic() -> None:
    """Same leaves in same order produce the same root."""
    leaves = ["aa", "bb", "cc"]
    assert merkle_root(leaves) == merkle_root(leaves)


def test_merkle_root_changes_with_order() -> None:
    """Different leaf order produces different roots."""
    assert merkle_root(["aa", "bb"]) != merkle_root(["bb", "aa"])


def test_merkle_root_odd_count_uses_rfc9162_split_point() -> None:
    """A three-leaf RFC 9162 tree differs from duplicate-last-leaf padding."""
    assert merkle_root(["aa", "bb", "cc"]) != merkle_root(["aa", "bb", "cc", "cc"])


def test_merkle_proof_inclusion_single() -> None:
    """With one leaf, the proof is empty."""
    assert merkle_proof(["abc123"], "abc123") == []


def test_merkle_proof_inclusion_two() -> None:
    """With two leaves, the proof is the sibling hash."""
    leaves = ["aa", "bb"]
    # merkle_root = H(0x01 || a || b)
    proof = merkle_proof(leaves, "aa")
    assert proof == ["bb"]


def test_merkle_proof_unknown_target() -> None:
    """Proof for non-existent leaf returns empty."""
    assert merkle_proof(["aa", "bb"], "cc") == []


def test_build_attestation_no_signing(bundle_dir: Path) -> None:
    """build_attestation produces a Merkle root + per-concept hashes without signing."""
    payload = build_attestation(bundle_dir, private_key_path=None)
    assert payload["tool"] == "headcleaner"
    assert payload["version"] == __version__
    assert payload["concept_count"] == 3
    assert "alpha.md" in payload["concepts"]
    assert "beta.md" in payload["concepts"]
    assert "gamma.md" in payload["concepts"]
    assert "index.md" not in payload["concepts"]  # excluded
    assert "log.md" not in payload["concepts"]  # excluded
    assert payload["merkle_root"]
    assert payload["signature"] is None
    assert payload["public_key"] is None
    assert payload["proof"]  # per-concept proofs included


def test_build_attestation_sources_version_from_package(bundle_dir: Path) -> None:
    assert build_attestation(bundle_dir)["version"] == __version__


def test_in_toto_statement_projects_integrity_without_review_claim(bundle_dir: Path) -> None:
    statement = build_in_toto_statement(build_attestation(bundle_dir))

    assert statement["_type"] == "https://in-toto.io/Statement/v1"
    assert statement["subject"] == [
        {"name": "bundle", "digest": {"sha256": build_attestation(bundle_dir)["merkle_root"]}}
    ]
    assert statement["predicateType"] == "https://headcleaner.dev/attestation/v1"
    assert statement["predicate"]["tool_version"] == __version__
    assert "review" not in canonical_json_bytes(statement).decode("utf-8").lower()


def test_in_toto_statement_records_normalized_configuration_hash(bundle_dir: Path) -> None:
    config = {"format": "okf", "options": {"ocr": False}}

    statement = build_in_toto_statement(build_attestation(bundle_dir), config=config)

    assert statement["predicate"]["config_sha256"] == hashlib.sha256(
        canonical_json_bytes(config)
    ).hexdigest()


def test_in_toto_statement_records_lock_hash_without_lock_path(
    bundle_dir: Path, tmp_path: Path
) -> None:
    lock_path = tmp_path / "uv.lock"
    lock_path.write_bytes(b"resolution = 1\n")

    statement = build_in_toto_statement(build_attestation(bundle_dir), lock_path=lock_path)

    assert statement["predicate"]["lock_sha256"] == hashlib.sha256(
        b"resolution = 1\n"
    ).hexdigest()
    assert str(lock_path) not in canonical_json_bytes(statement).decode("utf-8")


def test_build_attestation_with_signing(bundle_dir: Path, tmp_path: Path) -> None:
    """With a private key, signature and public_key are populated."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    priv = Ed25519PrivateKey.generate()
    key_path = tmp_path / "priv.pem"
    key_path.write_bytes(
        priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    payload = build_attestation(bundle_dir, private_key_path=key_path)
    assert payload["signature"]
    assert payload["public_key"]
    assert payload["public_key"].startswith("ed25519:")


def test_signed_attestation_uses_canonical_json_bytes(bundle_dir: Path, tmp_path: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    key_path = tmp_path / "priv.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    payload = build_attestation(bundle_dir, private_key_path=key_path)

    assert verify_signature(
        private_key.public_key(),
        payload["signature"],
        canonical_json_bytes(
            {
                "merkle_root": payload["merkle_root"],
                "concept_count": payload["concept_count"],
                "version": __version__,
            }
        ),
    )


def test_verify_attestation_clean(bundle_dir: Path) -> None:
    """Verify a freshly-created attestation passes."""
    payload = build_attestation(bundle_dir)
    attest_path = bundle_dir / "attestation.json"
    import json

    attest_path.write_text(json.dumps(payload), encoding="utf-8")
    result = verify_attestation(bundle_dir, attest_path)
    assert result["valid"] is True
    assert result["merkle_valid"] is True
    assert result["errors"] == []


def test_verify_attestation_detects_tampering(bundle_dir: Path) -> None:
    """Editing a concept after attestation makes the bundle invalid."""
    import json

    payload = build_attestation(bundle_dir)
    attest_path = bundle_dir / "attestation.json"
    attest_path.write_text(json.dumps(payload), encoding="utf-8")
    # Tamper with a concept
    (bundle_dir / "alpha.md").write_text("---\ntype: Document\n---\nTAMPERED\n", encoding="utf-8")
    result = verify_attestation(bundle_dir, attest_path)
    assert result["valid"] is False
    assert "do not match" in str(result["errors"])


def test_verify_attestation_signed_roundtrip(bundle_dir: Path, tmp_path: Path) -> None:
    """Sign + verify: a signed attestation verifies when the bundle is intact."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    priv = Ed25519PrivateKey.generate()
    key_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    key_path.write_bytes(
        priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    payload = build_attestation(bundle_dir, private_key_path=key_path)
    import json

    attest_path = bundle_dir / "attestation.json"
    attest_path.write_text(json.dumps(payload), encoding="utf-8")
    result = verify_attestation(bundle_dir, attest_path, public_key_path=pub_path)
    assert result["valid"] is True
    assert result["signature_valid"] is True


def test_verify_attestation_signature_fails_on_tampered(bundle_dir: Path, tmp_path: Path) -> None:
    """Signature verification fails when the bundle is modified after signing."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    import json

    priv = Ed25519PrivateKey.generate()
    key_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    key_path.write_bytes(
        priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    payload = build_attestation(bundle_dir, private_key_path=key_path)
    attest_path = bundle_dir / "attestation.json"
    attest_path.write_text(json.dumps(payload), encoding="utf-8")
    # Tamper: edit a concept without re-signing
    (bundle_dir / "beta.md").write_text("---\ntype: Document\n---\nTAMPERED\n", encoding="utf-8")
    result = verify_attestation(bundle_dir, attest_path, public_key_path=pub_path)
    assert result["valid"] is False
    assert result["signature_valid"] is False


def test_bundle_without_md_is_empty() -> None:
    """An empty bundle gets merkle_root = SHA-256(empty)."""
    payload = build_attestation_from_string = None  # placeholder
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        result = build_attestation(Path(td))
        assert result["concept_count"] == 0
        assert result["merkle_root"]  # not None, even for empty
        assert result["concepts"] == {}


def test_attestation_excludes_index_and_log(bundle_dir: Path) -> None:
    """index.md and log.md are not counted as concepts."""
    payload = build_attestation(bundle_dir)
    assert "index.md" not in payload["concepts"]
    assert "log.md" not in payload["concepts"]


# ---------------------------------------------------------------------------
# Contract 3.5 — bundle-relative source/output SHA sets in the in-toto predicate
# ---------------------------------------------------------------------------


def test_in_toto_predicate_includes_bundle_relative_source_sha_set(
    bundle_dir: Path,
) -> None:
    """The predicate must list sources as sorted bundle-relative {path, sha256}.

    Sources come from the OKF frontmatter `sources[].uri/sha256` of each
    concept; the path must be bundle-relative and free of absolute hostnames
    or user information.
    """
    statement = build_in_toto_statement(build_attestation(bundle_dir))

    sources = statement["predicate"].get("sources")
    assert isinstance(sources, list), "predicate.sources must be a list"
    assert sources, "predicate.sources must not be empty when concepts exist"
    for entry in sources:
        assert set(entry.keys()) >= {"path", "sha256"}, entry
        path = entry["path"]
        assert not path.startswith("/"), f"source path must be relative, got {path!r}"
        assert "\\" not in path, f"source path must use POSIX separators, got {path!r}"
        assert not path.startswith(("file://", "http://", "https://")), path
        assert len(entry["sha256"]) == 64
        int(entry["sha256"], 16)  # hex


def test_in_toto_predicate_includes_bundle_relative_output_sha_set(
    bundle_dir: Path,
) -> None:
    """The predicate must list outputs as sorted bundle-relative concept entries."""
    statement = build_in_toto_statement(build_attestation(bundle_dir))

    outputs = statement["predicate"].get("outputs")
    assert isinstance(outputs, list), "predicate.outputs must be a list"
    assert outputs, "predicate.outputs must not be empty when concepts exist"
    paths = [o["path"] for o in outputs]
    assert paths == sorted(paths), "outputs must be sorted by bundle-relative path"
    for entry in outputs:
        assert set(entry.keys()) >= {"path", "sha256"}, entry
        path = entry["path"]
        assert not path.startswith("/"), path
        assert "\\" not in path, path
        assert not path.startswith(("file://", "http://", "https://")), path
        assert path.endswith(".md"), path
        assert len(entry["sha256"]) == 64


def test_in_toto_predicate_source_sha_set_is_deterministic(bundle_dir: Path) -> None:
    """Two consecutive builds must produce identical source/output sets."""
    payload1 = build_attestation(bundle_dir)
    payload2 = build_attestation(bundle_dir)
    stmt1 = build_in_toto_statement(payload1)
    stmt2 = build_in_toto_statement(payload2)

    assert (
        canonical_json_bytes(stmt1["predicate"]["sources"])
        == canonical_json_bytes(stmt2["predicate"]["sources"])
    )
    assert (
        canonical_json_bytes(stmt1["predicate"]["outputs"])
        == canonical_json_bytes(stmt2["predicate"]["outputs"])
    )


def test_in_toto_predicate_source_sha_set_changes_when_concept_changes(
    bundle_dir: Path,
) -> None:
    """Editing a concept's frontmatter sources[0].sha256 must move the SHA set."""
    payload = build_attestation(bundle_dir)
    target = bundle_dir / "alpha.md"
    body = target.read_text(encoding="utf-8").split("---", 2)[-1]
    new_sha = "0" * 64
    target.write_text(
        f'---\ntype: Document\ntitle: Alpha\n'
        f'sources:\n  - uri: file://inbox/alpha.txt\n    kind: file\n    sha256: "{new_sha}"\n'
        f'---\n{body}',
        encoding="utf-8",
    )
    payload2 = build_attestation(bundle_dir)

    stmt_old = build_in_toto_statement(payload)
    stmt_new = build_in_toto_statement(payload2)
    sha_old = {s["sha256"] for s in stmt_old["predicate"]["sources"]}
    sha_new = {s["sha256"] for s in stmt_new["predicate"]["sources"]}
    assert new_sha in sha_new
    assert new_sha not in sha_old


def test_in_toto_predicate_output_sha_set_matches_concept_canonical_hash(
    bundle_dir: Path,
) -> None:
    """The output SHA set must equal the existing per-concept canonical hashes."""
    payload = build_attestation(bundle_dir)
    stmt = build_in_toto_statement(payload)

    by_path = {o["path"]: o["sha256"] for o in stmt["predicate"]["outputs"]}
    assert by_path == payload["concepts"]


def test_in_toto_predicate_source_sha_set_uses_bundle_relative_paths(
    tmp_path: Path,
) -> None:
    """Source paths must be relative even when the bundle lives under nested dirs."""
    nested = tmp_path / "deep" / "nested" / "bundle"
    nested.mkdir(parents=True)
    (nested / "one.md").write_text(
        "---\ntype: Document\ntitle: One\n"
        'sources:\n  - uri: file://x/y.txt\n    kind: file\n    sha256: "'
        + "a" * 64
        + '"\n---\nbody\n',
        encoding="utf-8",
    )
    (nested / "two.md").write_text(
        "---\ntype: Document\ntitle: Two\n"
        'sources:\n  - uri: file://x/y.txt\n    kind: file\n    sha256: "'
        + "b" * 64
        + '"\n---\nbody\n',
        encoding="utf-8",
    )

    stmt = build_in_toto_statement(build_attestation(nested))
    sources = stmt["predicate"]["sources"]
    # All sources point at the same upstream file (x/y.txt) so the path is that
    # bundle-relative path; if the implementation accidentally used absolute
    # paths they would start with the temp dir.
    paths = [s["path"] for s in sources]
    assert paths == sorted(paths)
    for p in paths:
        assert not p.startswith("/"), p
        assert str(tmp_path) not in p, f"absolute path leaked: {p}"
