"""Tests for the full Attested Computations implementation (Eng #36)."""

from __future__ import annotations

import pytest
from pathlib import Path

from headcleaner.attest import (
    canonical_hash,
    merkle_root,
    merkle_proof,
    build_attestation,
    verify_attestation,
)


@pytest.fixture
def bundle_dir(tmp_path: Path) -> Path:
    """Build a small bundle with 3 concepts."""
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "alpha.md").write_text(
        "---\ntype: Document\ntitle: Alpha\n---\nHello world\n", encoding="utf-8"
    )
    (b / "beta.md").write_text(
        "---\ntype: Document\ntitle: Beta\n---\nAnother concept\n", encoding="utf-8"
    )
    (b / "gamma.md").write_text(
        "---\ntype: Document\ntitle: Gamma\n---\nThird concept\n", encoding="utf-8"
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


def test_merkle_root_odd_count_duplicates_last() -> None:
    """Odd-numbered leaves: the last is duplicated to make it even."""
    # 3 leaves: [aa, bb, cc] -> [aa, bb, cc, cc] -> [H(aa,bb), H(cc,cc)]
    expected = merkle_root(["aa", "bb", "cc", "cc"])
    assert merkle_root(["aa", "bb", "cc"]) == expected


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
    assert payload["version"] == "0.7.0"
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
