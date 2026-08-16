"""MSG adapter (Eng #10) — Microsoft Outlook .msg files.

Uses `extract-msg` (already a dep). Extracts subject + body + headers
and renders them as a Markdown document. Attachments are listed by
filename + size.
"""
from __future__ import annotations

import email.utils
from pathlib import Path

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

    def extract(self, source: Path) -> Extracted:
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
        try:
            for att in (msg.attachments or []):
                attachments.append({
                    "filename": getattr(att, "longFilename", None) or getattr(att, "shortFilename", None) or "unknown",
                    "size": len(att.data) if getattr(att, "data", None) else 0,
                })
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
            "\n\n## Attachments\n\n" + "\n".join(
                f"- `{a['filename']}` ({a['size']} bytes)" for a in attachments
            )
            if attachments else ""
        )
        body_md = f"# {subject}\n\n{header_block}\n\n## Body\n\n{body or '(empty body)'}{att_block}\n"

        return {
            "title": subject,
            "body_md": body_md,
            "metadata": {
                "format": "msg",
                "sender": sender,
                "date": date,
                "attachment_count": len(attachments),
            },
        }