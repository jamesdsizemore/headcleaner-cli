"""Bounded attachment-recursion policy and deterministic child provenance."""

from __future__ import annotations

import io
import mimetypes
import stat
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import fromstring as safe_xml_fromstring

from .policy import AttachmentLimits

__all__ = (
    "AttachmentBudget",
    "AttachmentIdentity",
    "AttachmentLimits",
    "expand_archive_payload",
    "is_archive_payload",
)


@dataclass
class AttachmentBudget:
    """Run-scoped counters shared by every recursive expansion call."""

    members: int = 0
    total_bytes: int = 0


@dataclass(frozen=True)
class AttachmentIdentity:
    parent_source_sha256: str
    parent_attachment_id: str
    child_ordinal: int
    original_filename: str
    media_type: str
    extracted_sha256: str

    @classmethod
    def from_payload(
        cls,
        *,
        parent_source_sha256: str,
        parent_attachment_id: str,
        child_ordinal: int,
        original_filename: str,
        media_type: str,
        payload: bytes,
    ) -> AttachmentIdentity:
        if len(parent_source_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in parent_source_sha256
        ):
            raise ValueError("parent_source_sha256 must be lowercase SHA-256")
        if child_ordinal < 0:
            raise ValueError("child_ordinal must be non-negative")
        if not parent_attachment_id:
            raise ValueError("parent_attachment_id is required")
        return cls(
            parent_source_sha256=parent_source_sha256,
            parent_attachment_id=parent_attachment_id,
            child_ordinal=child_ordinal,
            original_filename=original_filename,
            media_type=media_type,
            extracted_sha256=sha256(payload).hexdigest(),
        )

    @property
    def source_uri(self) -> str:
        return (
            f"attachment:{self.parent_source_sha256}/"
            f"{self.parent_attachment_id}/{self.child_ordinal}"
        )

    @property
    def output_stem(self) -> str:
        return f"{self.parent_source_sha256[:16]}-{self.child_ordinal:04d}"


def _quarantined(reason: str, ordinal: int, **evidence: object) -> dict:
    diagnostic = {
        "code": "ATTACHMENT_QUARANTINED",
        "reason": reason,
        "ordinal": ordinal,
    }
    if evidence:
        diagnostic["evidence"] = evidence
    return diagnostic


def _normalized_member_name(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        return None
    if len(path.parts[0]) >= 2 and path.parts[0][1] == ":":
        return None
    return path.as_posix()


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    return member.create_system == 3 and stat.S_ISLNK(member.external_attr >> 16)


def _read_bounded_member(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    limits: AttachmentLimits,
    budget: AttachmentBudget,
) -> tuple[bytes | None, str | None]:
    if member.file_size > limits.max_member_bytes:
        return None, "max_member_bytes"
    chunks: list[bytes] = []
    member_bytes = 0
    try:
        with archive.open(member, "r") as stream:
            while True:
                chunk = stream.read(min(64 * 1024, limits.max_member_bytes + 1))
                if not chunk:
                    break
                member_bytes += len(chunk)
                if member_bytes > limits.max_member_bytes:
                    return None, "max_member_bytes"
                if budget.total_bytes + member_bytes > limits.max_total_bytes:
                    return None, "max_total_bytes"
                chunks.append(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile):
        return None, "archive_read_error"
    payload = b"".join(chunks)
    budget.total_bytes += len(payload)
    return payload, None


def is_archive_payload(attachment: dict) -> bool:
    """Return true only for explicitly declared ZIP attachments, not ZIP-based Office files."""
    payload = attachment.get("payload")
    if not isinstance(payload, bytes):
        return False
    media_type = str(attachment.get("media_type") or "").lower()
    filename = str(attachment.get("filename") or "").replace("\\", "/")
    suffix = PurePosixPath(filename).suffix.lower()
    zip_media_types = {"application/zip", "application/x-zip-compressed"}
    declared_zip = media_type in zip_media_types or suffix == ".zip"
    return declared_zip and zipfile.is_zipfile(io.BytesIO(payload))


def expand_archive_payload(
    parent: dict,
    limits: AttachmentLimits,
    *,
    depth: int,
    budget: AttachmentBudget | None = None,
) -> tuple[list[dict], list[dict]]:
    """Safely expand a ZIP payload into logical children without filesystem extraction."""
    payload = parent.get("payload")
    if not isinstance(payload, bytes) or not is_archive_payload(parent):
        return [], []
    if depth > limits.max_depth:
        return [], [_quarantined("max_depth", int(parent.get("child_ordinal", 0)), depth=depth)]

    active_budget = budget or AttachmentBudget()
    children: list[dict] = []
    diagnostics: list[dict] = []
    seen_member_ids: set[str] = set()
    parent_sha = str(parent.get("sha256") or sha256(payload).hexdigest())
    parent_attachment_id = str(parent.get("attachment_id") or "archive")

    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile:
        return [], [_quarantined("malformed_archive", int(parent.get("child_ordinal", 0)))]

    with archive:
        for ordinal, member in enumerate(archive.infolist()):
            if member.is_dir():
                continue
            normalized_name = _normalized_member_name(member.filename)
            if normalized_name is None:
                diagnostics.append(_quarantined("path_traversal", ordinal, member=member.filename))
                continue
            if normalized_name in seen_member_ids:
                diagnostics.append(
                    _quarantined("duplicate_member_id", ordinal, member=normalized_name)
                )
                continue
            seen_member_ids.add(normalized_name)
            if _is_symlink(member):
                diagnostics.append(_quarantined("symlink", ordinal, member=normalized_name))
                continue
            if member.flag_bits & 0x1:
                diagnostics.append(_quarantined("encrypted", ordinal, member=normalized_name))
                continue
            if active_budget.members >= limits.max_members:
                diagnostics.append(_quarantined("max_members", ordinal, member=normalized_name))
                continue
            active_budget.members += 1
            member_payload, reason = _read_bounded_member(archive, member, limits, active_budget)
            if reason is not None:
                diagnostics.append(_quarantined(reason, ordinal, member=normalized_name))
                continue
            assert member_payload is not None
            if normalized_name.lower().endswith((".xml", ".xhtml", ".svg")):
                try:
                    safe_xml_fromstring(member_payload)
                except (DefusedXmlException, ValueError):
                    diagnostics.append(_quarantined("unsafe_xml", ordinal, member=normalized_name))
                    active_budget.total_bytes -= len(member_payload)
                    continue
            attachment_id = f"{parent_attachment_id}:zip-member:{normalized_name}"
            identity = AttachmentIdentity.from_payload(
                parent_source_sha256=parent_sha,
                parent_attachment_id=attachment_id,
                child_ordinal=ordinal,
                original_filename=normalized_name,
                media_type=mimetypes.guess_type(normalized_name)[0] or "application/octet-stream",
                payload=member_payload,
            )
            children.append(
                {
                    "attachment_id": attachment_id,
                    "parent_source_sha256": identity.parent_source_sha256,
                    "parent_attachment_id": identity.parent_attachment_id,
                    "child_ordinal": ordinal,
                    "filename": identity.original_filename,
                    "media_type": identity.media_type,
                    "payload": member_payload,
                    "source_uri": identity.source_uri,
                    "sha256": identity.extracted_sha256,
                    "depth": depth,
                }
            )
    return children, diagnostics
