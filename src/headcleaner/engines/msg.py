"""MSG adapter (Eng #10) — Microsoft Outlook .msg files.

Uses `extract-msg` (already a dep). Extracts subject + body + headers
and renders them as a Markdown document. Attachments are listed by
filename + size.
"""

from __future__ import annotations

import mimetypes
from hashlib import sha256
from pathlib import Path

from ..attachments import AttachmentIdentity
from ..policy import AttachmentLimits
from .base import Adapter

try:
    import extract_msg  # type: ignore[import]

    HAS_EXTRACT_MSG = True
except ImportError:  # pragma: no cover
    HAS_EXTRACT_MSG = False


def _fmt_date(value) -> str:
    if value is None:
        return ""
    try:
        return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


class MsgAdapter(Adapter):
    name = "msg"
    extensions = (".msg",)

    def __init__(self, attachment_limits: AttachmentLimits | None = None) -> None:
        self.attachment_limits = attachment_limits or AttachmentLimits()

    def extract(self, source: Path) -> Extracted:  # noqa: F821
        if not HAS_EXTRACT_MSG:
            return {
                "title": source.stem,
                "body_md": "(extract-msg not installed; cannot parse .msg)",
                "metadata": {"format": "msg", "error": "extract-msg missing"},
            }

        msg = extract_msg.Message(str(source))
        try:
            subject = (msg.subject or source.stem).strip()
        except Exception:
            subject = source.stem
        try:
            sender = (msg.sender or "").strip()
        except Exception:
            sender = ""
        try:
            to = msg.to or ""
        except Exception:
            to = ""
        try:
            cc = msg.cc or ""
        except Exception:
            cc = ""
        try:
            date = _fmt_date(msg.date)
        except Exception:
            date = ""
        try:
            body = (msg.body or "").strip()
        except Exception:
            body = ""

        attachments = []
        attachment_records: list[dict] = []
        attachment_diagnostics: list[dict] = []
        source_sha = sha256(source.read_bytes()).hexdigest()
        total_bytes = 0
        try:
            for ordinal, att in enumerate(msg.attachments or []):
                payload = getattr(att, "data", None) or b""
                reason = None
                if ordinal >= self.attachment_limits.max_members:
                    reason = "max_members"
                elif len(payload) > self.attachment_limits.max_member_bytes:
                    reason = "max_member_bytes"
                elif total_bytes + len(payload) > self.attachment_limits.max_total_bytes:
                    reason = "max_total_bytes"
                if reason is not None:
                    attachment_diagnostics.append(
                        {
                            "code": "ATTACHMENT_QUARANTINED",
                            "reason": reason,
                            "ordinal": ordinal,
                        }
                    )
                    continue
                filename = (
                    getattr(att, "longFilename", None) or getattr(att, "shortFilename", None) or ""
                )
                attachments.append(
                    {
                        "filename": filename or "unknown",
                        "size": len(payload),
                    }
                )
                attachment_id = f"msg-part-{ordinal}"
                media_type = getattr(att, "mimetype", None) or mimetypes.guess_type(filename)[0]
                identity = AttachmentIdentity.from_payload(
                    parent_source_sha256=source_sha,
                    parent_attachment_id=attachment_id,
                    child_ordinal=ordinal,
                    original_filename=filename,
                    media_type=media_type or "application/octet-stream",
                    payload=payload,
                )
                attachment_records.append(
                    {
                        "attachment_id": attachment_id,
                        "parent_source_sha256": source_sha,
                        "parent_attachment_id": attachment_id,
                        "child_ordinal": ordinal,
                        "filename": identity.original_filename,
                        "media_type": identity.media_type,
                        "payload": payload,
                        "source_uri": identity.source_uri,
                        "sha256": identity.extracted_sha256,
                    }
                )
                total_bytes += len(payload)
        except Exception:
            pass

        # Build a Markdown document
        headers = []
        if sender:
            headers.append(f"- **From:** {sender}")
        if to:
            headers.append(f"- **To:** {to}")
        if cc:
            headers.append(f"- **Cc:** {cc}")
        if date:
            headers.append(f"- **Date:** {date}")
        header_block = "\n".join(headers) if headers else "(no headers)"
        att_block = (
            "\n\n## Attachments\n\n"
            + "\n".join(f"- `{a['filename']}` ({a['size']} bytes)" for a in attachments)
            if attachments
            else ""
        )
        body_md = (
            f"# {subject}\n\n{header_block}\n\n## Body\n\n{body or '(empty body)'}{att_block}\n"
        )

        return {
            "title": subject,
            "body_md": body_md,
            "metadata": {
                "format": "msg",
                "sender": sender,
                "date": date,
                "attachment_count": len(attachments),
            },
            "attachments": attachment_records,
            "attachment_diagnostics": attachment_diagnostics,
        }
