"""EML adapter — RFC 5322 email files.

Parses with stdlib `email` (no new dep). Renders a Markdown body
containing:
- the headers (From, To, Subject, Date, Message-ID, ...) as a bullet list
- the body (text/plain preferred; text/html fallback with markdownify)
- attachments listed as separate sections
"""

from __future__ import annotations

import email
import email.policy
import re
from email.message import Message
from pathlib import Path

from markdownify import markdownify

from .base import Adapter, AdapterError


class EmlAdapter(Adapter):
    name = "eml"
    extensions = {".eml"}

    def extract(self, source: Path, *, progress=None) -> dict:
        try:
            raw = source.read_bytes()
            msg = email.message_from_bytes(raw, policy=email.policy.default)
        except (OSError, ValueError) as e:
            raise AdapterError(f"eml parse failed on {source}: {e}") from e

        title = msg.get("Subject", source.stem) or source.stem
        headers_md = self._render_headers(msg)
        body_md = self._render_body(msg)
        attachments_md = self._render_attachments(msg)

        full_md = "\n\n".join(s for s in (headers_md, body_md, attachments_md) if s)

        return {
            "title": str(title).strip()[:200] or source.stem,
            "body_md": full_md + "\n",
            "metadata": {
                "engine": self.name,
                "source_format": ".eml",
                "from": str(msg.get("From", "")),
                "to": str(msg.get("To", "")),
                "subject": str(msg.get("Subject", "")),
                "date": str(msg.get("Date", "")),
                "message_id": str(msg.get("Message-ID", "")),
                "byte_size": source.stat().st_size,
            },
            "attachments": [],
        }

    @staticmethod
    def _render_headers(msg: Message) -> str:
        headers = []
        for key in ("From", "To", "Cc", "Bcc", "Subject", "Date", "Message-ID"):
            v = msg.get(key)
            if v:
                headers.append(f"- **{key}**: {v}")
        if not headers:
            return ""
        return "## Headers\n\n" + "\n".join(headers) + "\n"

    def _render_body(self, msg: Message) -> str:
        if msg.is_multipart():
            # Prefer text/plain; fall back to text/html
            text_part = msg.get_body(preferencelist=("plain", "html"))
            if text_part is None:
                return ""
            content_type = text_part.get_content_type()
            payload = text_part.get_content()
        else:
            content_type = msg.get_content_type()
            payload = msg.get_content()

        if content_type == "text/html":
            try:
                md = markdownify(payload, heading_style="ATX", bullets="-")
                return "## Body\n\n" + md.strip() + "\n"
            except Exception:
                # Fall through to plain
                content_type = "text/plain"
                payload = re.sub(r"<[^>]+>", "", payload) if payload else ""

        if content_type == "text/plain":
            return "## Body\n\n```text\n" + (payload or "").rstrip() + "\n```\n"
        return ""

    @staticmethod
    def _render_attachments(msg: Message) -> str:
        if not msg.is_multipart():
            return ""
        attachments = []
        for part in msg.iter_attachments():
            filename = part.get_filename() or "(unnamed)"
            content_type = part.get_content_type()
            size = len(part.get_payload(decode=True) or b"")
            attachments.append(f"- `{filename}` ({content_type}, {size:,} bytes)")
        if not attachments:
            return ""
        return "## Attachments\n\n" + "\n".join(attachments) + "\n"
