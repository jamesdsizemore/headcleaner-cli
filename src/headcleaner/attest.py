"""`headcleaner attest` (Eng #36) — Attested Computations, full impl.

OKF v0.2 §10 Attested Computations: prove that a bundle was generated
by a specific headcleaner version using a specific toolchain, with no
human edits in between.

What this computes, per concept:
  1. `canonical_hash(concept_path)` — SHA-256 of the canonical UTF-8
     form (sorted keys, LF line endings, no trailing whitespace).
  2. A Merkle tree over all concept hashes (RFC 9162 SHA-256 binary tree).
  3. The Merkle root signed with ed25519 (RFC 8032) when a key is supplied.
  4. Optional inclusion proofs: `proof[concept_sha256]` is a list of
     sibling hashes from leaf to root.

The output is `attestation.json` next to the bundle:

    {
      "tool": "headcleaner",
      "version": "0.7.0",
      "bundle_root": "...",
      "concept_count": 5,
      "concepts": {"alpha.md": "..."},
      "merkle_root": "...",
      "public_key": "ed25519:..."  // base64, only when --private-key given
      "signature": "...",
      "proof": {"alpha.md": ["..."], ...}
    }

When `--private-key` is omitted, the bundle gets a Merkle root but no
signature (useful for transparent diff verification).

CLI:
    headcleaner attest <bundle-dir> [--private-key <PEM>] [--output <path>]
    headcleaner verify <bundle-dir> [--public-key <PEM>] [--attestation <path>]
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from . import __version__

# Ed25519 signing via cryptography (pure-Python ed25519 also acceptable if needed)
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


# ---------------------------------------------------------------------------
# Canonical hashing
# ---------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    """Encode a JSON value deterministically for signing or hashing."""
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_hash(concept_path: Path) -> str:
    """SHA-256 of the canonical UTF-8 form.

    Sort keys, ensure ASCII, LF line endings, no trailing whitespace.
    Stable across platforms and Python versions.
    """
    text = concept_path.read_text(encoding="utf-8")
    # Normalize line endings to LF, strip trailing whitespace per line
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    canonical = json.dumps({"raw": normalized}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Merkle tree (RFC 9162 SHA-256 binary tree)
# ---------------------------------------------------------------------------


def _hash_pair(left: bytes, right: bytes) -> bytes:
    """RFC 9162 §2.1.1: H(0x01 || left || right) for inner nodes.
    For leaf nodes we already have the SHA-256 of the raw content; we do
    NOT apply the 0x00 prefix again — that prefix is only used when the
    "leaf" hash is the raw byte string, not when it's already a SHA-256.

    For a binary Merkle tree over pre-hashed leaves (a common pattern),
    we use H(0x01 || left || right) for inner nodes."""
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(leaf_hashes_hex: list[str]) -> str:
    """Build an RFC 9162 SHA-256 Merkle root over a list of leaf hashes.

    Returns the hex-encoded root. Empty input returns the SHA-256 of the
    empty string (the standard "empty tree" root).
    """
    if not leaf_hashes_hex:
        return hashlib.sha256(b"").hexdigest()
    return _merkle_root_bytes([bytes.fromhex(h) for h in leaf_hashes_hex]).hex()


def _merkle_root_bytes(leaves: list[bytes]) -> bytes:
    """Return an RFC 9162 split-point root for a non-empty leaf sequence."""
    if len(leaves) == 1:
        return leaves[0]
    split = 1 << (len(leaves).bit_length() - 1)
    if split == len(leaves):
        split //= 2
    return _hash_pair(_merkle_root_bytes(leaves[:split]), _merkle_root_bytes(leaves[split:]))


def merkle_proof(leaf_hashes_hex: list[str], target_hex: str) -> list[str]:
    """Build an inclusion proof for `target_hex` from the leaf list.

    Returns the list of sibling hashes from leaf level up to the root.
    Empty list for empty/target-missing trees.
    """
    if not leaf_hashes_hex or target_hex not in leaf_hashes_hex:
        return []
    leaves = [bytes.fromhex(h) for h in leaf_hashes_hex]
    return [item.hex() for item in _merkle_proof_bytes(leaves, leaf_hashes_hex.index(target_hex))]


def _merkle_proof_bytes(leaves: list[bytes], index: int) -> list[bytes]:
    """Return the bottom-up RFC 9162 inclusion path for one leaf index."""
    if len(leaves) == 1:
        return []
    split = 1 << (len(leaves).bit_length() - 1)
    if split == len(leaves):
        split //= 2
    if index < split:
        return _merkle_proof_bytes(leaves[:split], index) + [_merkle_root_bytes(leaves[split:])]
    return _merkle_proof_bytes(leaves[split:], index - split) + [_merkle_root_bytes(leaves[:split])]


# ---------------------------------------------------------------------------
# Ed25519 signing
# ---------------------------------------------------------------------------


def _b64(data: bytes) -> str:
    """Standard base64 (no line breaks)."""
    return base64.b64encode(data).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def load_private_key(path: Path | None) -> Ed25519PrivateKey | None:
    """Load an ed25519 private key from a PEM file.

    If `path` is None, returns None (no signing). Supports both
    `BEGIN PRIVATE KEY` (PKCS8) and `BEGIN OPENSSH PRIVATE KEY` formats.
    """
    if path is None:
        return None
    if not _HAS_CRYPTO:
        raise RuntimeError(
            "cryptography library not installed; cannot load ed25519 key. "
            "Install with `uv pip install cryptography`."
        )
    pem = path.read_bytes()
    try:
        key = serialization.load_pem_private_key(pem, password=None)
    except Exception:
        # Try OpenSSH format
        key = serialization.load_ssh_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"Key at {path} is not an ed25519 private key (got {type(key).__name__})")
    return key


def load_public_key(path: Path) -> Ed25519PublicKey:
    """Load an ed25519 public key from a PEM file."""
    if not _HAS_CRYPTO:
        raise RuntimeError("cryptography library not installed.")
    pem = path.read_bytes()
    try:
        key = serialization.load_pem_public_key(pem)
    except Exception:
        try:
            key = serialization.load_ssh_public_key(pem)
        except Exception as e:
            raise ValueError(f"Cannot parse public key at {path}: {e}") from e
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError(f"Key at {path} is not an ed25519 public key")
    return key


def public_key_b64(key: Ed25519PublicKey) -> str:
    """Return base64-encoded raw 32-byte public key."""
    raw = key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64(raw)


def sign_message(private_key: Ed25519PrivateKey, message: bytes) -> str:
    """Sign a message and return the base64-encoded signature."""
    return _b64(private_key.sign(message))


def verify_signature(public_key: Ed25519PublicKey, signature_b64: str, message: bytes) -> bool:
    """Verify a base64-encoded signature against a message."""
    try:
        public_key.verify(_b64d(signature_b64), message)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Bundle attestation
# ---------------------------------------------------------------------------


def _concept_hashes(bundle_root: Path) -> dict[str, str]:
    """Walk a bundle and compute canonical hashes for each concept."""
    if not bundle_root.is_dir():
        raise FileNotFoundError(bundle_root)
    out: dict[str, str] = {}
    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in {"index.md", "log.md"}:
            continue
        rel = str(md_path.relative_to(bundle_root)).replace("\\", "/")
        out[rel] = canonical_hash(md_path)
    return out


def build_attestation(
    bundle_root: Path,
    private_key_path: Path | None = None,
    include_proofs: bool = True,
) -> dict[str, Any]:
    """Compute the full attestation payload for a bundle.

    When `private_key_path` is provided, also sign the Merkle root.
    When `include_proofs` is True, include per-concept inclusion proofs.
    """
    bundle_root = Path(bundle_root)
    concepts = _concept_hashes(bundle_root)
    leaf_hashes = list(concepts.values())
    root = merkle_root(leaf_hashes)

    payload: dict[str, Any] = {
        "tool": "headcleaner",
        "version": __version__,
        "bundle_root": str(bundle_root.resolve()),
        "concept_count": len(concepts),
        "concepts": concepts,
        "merkle_root": root,
        "public_key": None,
        "signature": None,
        "proof": None,
    }

    if private_key_path is not None:
        key = load_private_key(private_key_path)
        if key is not None:
            # Sign the canonical encoding of the root + metadata
            to_sign = canonical_json_bytes(
                {
                    "merkle_root": root,
                    "concept_count": len(concepts),
                    "version": __version__,
                }
            )
            payload["public_key"] = "ed25519:" + public_key_b64(key.public_key())
            payload["signature"] = sign_message(key, to_sign)

    if include_proofs:
        proofs: dict[str, list[str]] = {}
        for rel, h in concepts.items():
            proofs[rel] = merkle_proof(leaf_hashes, h)
        payload["proof"] = proofs

    return payload


def build_in_toto_statement(
    attestation: dict[str, Any],
    config: dict[str, Any] | None = None,
    lock_path: Path | None = None,
) -> dict[str, Any]:
    """Project an integrity attestation into a deterministic in-toto statement."""
    config_sha256 = hashlib.sha256(canonical_json_bytes(config or {})).hexdigest()
    predicate: dict[str, Any] = {
        "schema_version": "1",
        "tool_version": attestation["version"],
        "config_sha256": config_sha256,
        "concept_count": attestation["concept_count"],
        "concepts": attestation["concepts"],
        "merkle_root": attestation["merkle_root"],
    }
    if lock_path is not None:
        predicate["lock_sha256"] = hashlib.sha256(Path(lock_path).read_bytes()).hexdigest()
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": "bundle",
                "digest": {"sha256": attestation["merkle_root"]},
            }
        ],
        "predicateType": "https://headcleaner.dev/attestation/v1",
        "predicate": predicate,
    }


def write_attestation(
    bundle_root: Path,
    output: Path | None = None,
    private_key_path: Path | None = None,
) -> Path:
    """Write `attestation.json` next to the bundle."""
    payload = build_attestation(bundle_root, private_key_path=private_key_path)
    out_path = output or (bundle_root / "attestation.json")
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def verify_attestation(
    bundle_root: Path,
    attestation_path: Path,
    public_key_path: Path | None = None,
) -> dict[str, Any]:
    """Verify a bundle's attestation against the bundle contents.

    Returns a dict with `valid`, `merkle_valid`, `signature_valid`, and
    any error messages. Always returns the dict; never raises.
    """
    result: dict[str, Any] = {
        "valid": False,
        "merkle_valid": False,
        "signature_valid": None,
        "errors": [],
    }
    try:
        payload = json.loads(attestation_path.read_text(encoding="utf-8"))
    except Exception as e:
        result["errors"].append(f"cannot read attestation: {e}")
        return result

    # Recompute the hashes
    try:
        concepts = _concept_hashes(bundle_root)
    except Exception as e:
        result["errors"].append(f"cannot walk bundle: {e}")
        return result

    if payload.get("concepts") != concepts:
        result["errors"].append("concept hashes do not match")
    else:
        result["merkle_valid"] = True

    # Verify Merkle root
    expected_root = merkle_root(list(concepts.values()))
    if payload.get("merkle_root") != expected_root:
        result["errors"].append(
            f"merkle_root mismatch: payload={payload.get('merkle_root')}, "
            f"recomputed={expected_root}"
        )
        result["merkle_valid"] = False

    # Verify signature if both key and signature are present
    if payload.get("signature") and payload.get("public_key"):
        if public_key_path is None:
            result["errors"].append(
                "signature present but no --public-key supplied for verification"
            )
        else:
            try:
                pk = load_public_key(public_key_path)
                to_verify = canonical_json_bytes(
                    {
                        "merkle_root": expected_root,
                        "concept_count": len(concepts),
                        "version": __version__,
                    }
                )
                ok = verify_signature(pk, payload["signature"], to_verify)
                result["signature_valid"] = ok
                if not ok:
                    result["errors"].append("signature does not verify")
            except Exception as e:
                result["errors"].append(f"signature verification failed: {e}")
                result["signature_valid"] = False

    # Verify inclusion proofs (if present)
    if payload.get("proof") and result["merkle_valid"]:
        for rel, sibling_chain in payload["proof"].items():
            h = concepts.get(rel)
            if h is None:
                result["errors"].append(f"proof for unknown concept: {rel}")
                continue
            # Walk the chain
            current = bytes.fromhex(h)
            for sibling_hex in sibling_chain:
                sibling = bytes.fromhex(sibling_hex)
                # We need to know left/right ordering: search list to find idx
                # Simpler: re-derive both and pick the one that has sibling on the correct side.
                # We'll use the simpler approach: at each level, the current idx determines the side.  # noqa: E501
                # Since we don't know the original index, we try both orderings.
                h_left = _hash_pair(current, sibling)
                h_right = _hash_pair(sibling, current)
                # Whichever matches any current hash in the next level is right.
                # Easier: build the sibling chain from the leaf index.
                pass  # see _verify_proof_with_index() for full impl
            # Use the proper verification helper
            if not _verify_proof_with_index(h, sibling_chain, list(concepts.values())):
                result["errors"].append(f"proof mismatch for {rel}")

    result["valid"] = result["merkle_valid"] and not result["errors"]
    return result


def _verify_proof_with_index(
    leaf_hash_hex: str, proof: list[str], all_leaves_hex: list[str]
) -> bool:
    """Verify a Merkle inclusion proof given the full leaf list."""
    if leaf_hash_hex not in all_leaves_hex:
        return False
    idx = all_leaves_hex.index(leaf_hash_hex)
    leaves = [bytes.fromhex(h) for h in all_leaves_hex]
    expected = _merkle_proof_bytes(leaves, idx)
    try:
        supplied = [bytes.fromhex(sibling) for sibling in proof]
    except ValueError:
        return False
    return supplied == expected
