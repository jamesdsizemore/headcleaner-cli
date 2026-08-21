"""Bounded pre-routing inspection for untrusted conversion inputs."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InspectionResult:
    source_ref: str
    declared_type: str
    detected_type: str
    archive_summary: dict[str, object]
    encryption: bool
    macro_indicators: tuple[str, ...]
    findings: tuple[dict[str, object], ...]
    disposition: str


def _declared_type(path: Path) -> str:
    return {".zip": "zip", ".docx": "docx", ".xlsx": "xlsx", ".pptx": "pptx"}.get(
        path.suffix.lower(), "unknown"
    )


def inspect_file(source: Path) -> InspectionResult:
    """Inspect signatures and ZIP inventory only; never extract or execute content."""
    source = Path(source)
    declared = _declared_type(source)
    header = source.read_bytes()[:4]
    detected = (
        "zip"
        if header.startswith(b"PK\x03\x04")
        else "pdf"
        if header.startswith(b"%PDF")
        else "unknown"
    )
    findings: list[dict[str, object]] = []
    summary: dict[str, object] = {"member_count": 0}
    encryption = False
    macros: list[str] = []
    if detected == "zip":
        try:
            with zipfile.ZipFile(source) as archive:
                members = archive.infolist()
                summary = {"member_count": len(members)}
                for member in members:
                    normalized = member.filename.replace("\\", "/")
                    if normalized.startswith("/") or any(part == ".." for part in normalized.split("/")):
                        findings.append({"code": "archive_traversal", "member": normalized})
                    if member.flag_bits & 0x1:
                        encryption = True
                    if normalized.lower().endswith("vbaProject.bin".lower()):
                        macros.append(normalized)
        except zipfile.BadZipFile:
            findings.append({"code": "malformed_archive"})
    if detected == "zip" and declared in {"docx", "xlsx", "pptx"}:
        detected = declared
    if declared != "unknown" and detected != "unknown" and declared != detected:
        findings.append({"code": "type_mismatch", "declared": declared, "detected": detected})
    if encryption:
        findings.append({"code": "archive_encrypted"})
    if macros:
        findings.append({"code": "macro_indicator", "members": tuple(macros)})
    disposition = "quarantine" if findings else "allow"
    return InspectionResult(
        source_ref=source.name,
        declared_type=declared,
        detected_type=detected,
        archive_summary=summary,
        encryption=encryption,
        macro_indicators=tuple(macros),
        findings=tuple(findings),
        disposition=disposition,
    )
