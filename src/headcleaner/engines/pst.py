"""PST adapter — Outlook Personal Folders (Eng #7 full impl).

Two backends, tried in order:

1. **`readpst` subprocess** (preferred, cross-platform) — runs the
   `readpst` CLI from `libpst` (`brew install libpst` on macOS,
   `apt install libpst-tools` on Linux, available in MSYS2 on Windows).
   Output is parsed with stdlib `mailbox.mbox()`.

2. **`libpff-python`** (Windows/macOS fallback) — native bindings when
   `readpst` is not available. Walks the folder hierarchy and emits
   summary lines per message (no body — libpff doesn't expose MIME).

**Per-message emission:** Every message becomes a separate OKF concept
via the `extract_messages()` adapter interface. The runner detects it
and emits one concept per message instead of one per source file.

If neither backend is available, raises AdapterError with a clear hint.
The router treats AdapterError as a graceful failure (the file is
recorded as 'failed' in the manifest, not a crash).
"""

from __future__ import annotations

import email
import mailbox
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from .base import Adapter, AdapterError


_READPST_NAMES = ("readpst", "readpst.exe")
_REC_SUBJECT = re.compile(r"^\s*Subject:\s*(.*?)\s*$", re.MULTILINE | re.IGNORECASE)
_REC_FROM = re.compile(r"^\s*From:\s*(.*?)\s*$", re.MULTILINE | re.IGNORECASE)
_REC_TO = re.compile(r"^\s*To:\s*(.*?)\s*$", re.MULTILINE | re.IGNORECASE)
_REC_DATE = re.compile(r"^\s*Date:\s*(.*?)\s*$", re.MULTILINE | re.IGNORECASE)


def _sanitize_slug(s: str, max_len: int = 80) -> str:
    """Turn an email subject into a filename-safe slug."""
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("._-")
    return s[:max_len] or "untitled"


def _readpst_available() -> str | None:
    """Return the path to readpst if available, else None."""
    for name in _READPST_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _run_readpst(pst_path: Path, tmp_dir: Path) -> Path:
    """Run `readpst -e -D` to dump messages into an mbox. Returns the mbox path."""
    binary = _readpst_available()
    if binary is None:
        raise AdapterError(
            "readpst not on PATH. Install libpst: `brew install libpst` "
            "(macOS), `apt install libpst-tools` (Linux), or MSYS2 pacman -S libpst (Windows)."
        )
    # -e = extract to mbox, -D = include deleted items, -q = quiet
    cmd = [binary, "-e", "-D", "-q", "-o", str(tmp_dir), str(pst_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except FileNotFoundError as e:
        raise AdapterError(f"readpst binary not found: {binary}") from e
    except subprocess.TimeoutExpired as e:
        raise AdapterError(f"readpst timed out on {pst_path}") from e
    if result.returncode != 0:
        raise AdapterError(
            f"readpst failed on {pst_path} (exit {result.returncode}): "
            f"{result.stderr.strip()[:200]}"
        )
    # readpst outputs a single mbox file in tmp_dir (the PST's filename with .mbox appended)
    mbox_candidates = sorted(tmp_dir.glob("*.mbox")) + sorted(tmp_dir.glob("*.mbx"))
    if not mbox_candidates:
        # No mbox output — try to find any text file
        any_files = sorted(tmp_dir.iterdir())
        if not any_files:
            raise AdapterError(f"readpst produced no output for {pst_path}")
        # Fall back to the first regular file
        return any_files[0]
    return mbox_candidates[0]


def _mbox_messages(mbox_path: Path) -> list[email.message.Message]:
    """Read an mbox file and return all messages."""
    mbox = mailbox.mbox(str(mbox_path))
    out: list[email.message.Message] = []
    try:
        for msg in mbox:
            try:
                out.append(msg)
            except Exception:
                continue
    finally:
        try:
            mbox.close()
        except Exception:
            pass
    return out


def _first_text(msg: email.message.Message) -> str:
    """Pluck the first text/plain or text/html part from a message."""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True) or b""
                try:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    return payload.decode("utf-8", errors="replace")
        # Fall through to HTML
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                try:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    return payload.decode("utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True) or b""
    try:
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _msg_to_concept_dict(msg: email.message.Message, source: Path, idx: int) -> dict:
    """Convert one email.message.Message into the canonical Adapter output dict."""
    subject = (msg.get("Subject") or "(no subject)").strip()
    if isinstance(subject, str):
        subject = subject.encode("ascii", errors="replace").decode("ascii")
    sender = (msg.get("From") or "").strip()
    to = (msg.get("To") or "").strip()
    date = (msg.get("Date") or "").strip()
    message_id = (msg.get("Message-ID") or "").strip()

    body = _first_text(msg)
    # Strip common HTML tags if no plaintext was found
    if "<html" in body.lower() or "<p>" in body.lower():
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()

    body_md = f"# {subject}\n\n"
    rows = [
        ("From", sender),
        ("To", to),
        ("Date", date),
        ("Source", str(source.name)),
    ]
    if message_id:
        rows.append(("Message-ID", message_id))
    body_md += "| Field | Value |\n|---|---|\n"
    for k, v in rows:
        if v:
            body_md += f"| **{k}** | {v} |\n"
    body_md += "\n"
    if body.strip():
        body_md += f"\n{body}\n"

    return {
        "title": f"{source.stem} — {subject}",
        "body_md": body_md,
        "metadata": {
            "engine": "pst",
            "source_format": ".pst",
            "source_file": str(source),
            "subject": subject,
            "from": sender,
            "to": to,
            "date": date,
            "message_id": message_id,
            "message_index": idx,
        },
        "attachments": [],
    }


class PstAdapter(Adapter):
    name = "pst"
    extensions = {".pst"}

    def __init__(self) -> None:
        try:
            import libpff  # noqa: F401

            self._libpff = libpff
        except ImportError:
            self._libpff = None

    # -- Primary entry: multi-message output (Eng #7) -----------------------

    def extract_messages(
        self, source: Path, *, progress: Callable[[int, int], None] | None = None
    ) -> list[dict]:
        """Return one Adapter output dict per message in the PST."""
        readpst = _readpst_available()
        if readpst is not None:
            return self._extract_via_readpst(source, progress=progress)
        if self._libpff is not None:
            return self._extract_via_libpff(source, progress=progress)
        raise AdapterError(
            f"Cannot read PST {source}: no `readpst` on PATH and libpff-python not installed. "
            f"Install libpst (`brew install libpst`) for cross-platform access, "
            f"or libpff-python (`uv pip install libpff-python`) for Windows native. "
            f"Or convert PST to MSG first with `readpst -e <input.pst> <output_dir>`."
        )

    def _extract_via_readpst(
        self, source: Path, *, progress: Callable[[int, int], None] | None
    ) -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            mbox_path = _run_readpst(source, tmp_dir)
            messages = _mbox_messages(mbox_path)
        total = len(messages)
        out: list[dict] = []
        for i, msg in enumerate(messages, start=1):
            if progress is not None:
                try:
                    progress(i, total)
                except Exception:
                    pass
            out.append(_msg_to_concept_dict(msg, source, i))
        return out

    def _extract_via_libpff(
        self, source: Path, *, progress: Callable[[int, int], None] | None
    ) -> list[dict]:
        """Fallback: libpff walks the folder hierarchy. libpff doesn't expose
        MIME body parts, so we emit per-message summaries with whatever
        metadata libpff exposes (subject, sender, etc., when available)."""
        if self._libpff is None:
            raise AdapterError("libpff-python not installed.")
        try:
            file_obj = self._libpff.file()
            file_obj.open(str(source))
            try:
                root = file_obj.get_root_folder()
                if root is None:
                    return []
                summaries = self._walk_folders(root, source)
            finally:
                try:
                    file_obj.close()
                except Exception:
                    pass
        except Exception as e:
            raise AdapterError(f"libpff failed on {source}: {e}") from e

        total = len(summaries)
        out: list[dict] = []
        for i, summary in enumerate(summaries, start=1):
            if progress is not None:
                try:
                    progress(i, total)
                except Exception:
                    pass
            body_md = (
                f"# {summary['subject'] or '(no subject)'}\n\n"
                f"> Source: `{source}` (libpff fallback; body not available)\n\n"
            )
            rows = [
                ("Subject", summary["subject"]),
                ("From", summary["from"]),
                ("To", summary["to"]),
                ("Date", summary["date"]),
                ("Folder", summary["folder"]),
            ]
            body_md += "| Field | Value |\n|---|---|\n"
            for k, v in rows:
                if v:
                    body_md += f"| **{k}** | {v} |\n"
            out.append(
                {
                    "title": f"{source.stem} — {summary['subject'] or '(no message ' + str(i) + ')'}",  # noqa: E501
                    "body_md": body_md,
                    "metadata": {
                        "engine": "pst",
                        "source_format": ".pst",
                        "source_file": str(source),
                        "subject": summary["subject"],
                        "from": summary["from"],
                        "to": summary["to"],
                        "date": summary["date"],
                        "folder": summary["folder"],
                        "fallback": "libpff-no-body",
                        "message_index": i,
                    },
                    "attachments": [],
                }
            )
        return out

    def _walk_folders(self, folder, source: Path, path: str = "") -> list[dict]:
        """Recursively walk a libpff folder tree and emit per-message summaries."""
        out: list[dict] = []
        try:
            n_items = folder.get_number_of_items() if hasattr(folder, "get_number_of_items") else 0
        except Exception:
            n_items = 0
        for i in range(n_items):
            try:
                sub = folder.get_item(i)
            except Exception:
                continue
            try:
                sub_name = sub.name if hasattr(sub, "name") else f"item_{i}"
            except Exception:
                sub_name = f"item_{i}"
            try:
                if hasattr(sub, "get_number_of_messages"):
                    # It's a folder with messages
                    folder_path = f"{path}/{sub_name}" if path else sub_name
                    n_msgs = sub.get_number_of_messages()
                    for j in range(n_msgs):
                        try:
                            msg = sub.get_message(j)
                            summary = self._summarize_msg(msg, folder_path)
                        except Exception:
                            summary = {
                                "subject": f"(message {j + 1})",
                                "from": "",
                                "to": "",
                                "date": "",
                                "folder": folder_path,
                            }
                        out.append(summary)
                elif hasattr(sub, "get_number_of_items"):
                    # It's a subfolder
                    out.extend(
                        self._walk_folders(sub, source, f"{path}/{sub_name}" if path else sub_name)
                    )
            except Exception:
                continue
        return out

    @staticmethod
    def _summarize_msg(msg, folder_path: str) -> dict:
        """Extract subject/from/to/date from a libpff message via the
        best-effort record API (libpff API varies across versions)."""
        result = {"subject": "", "from": "", "to": "", "date": "", "folder": folder_path}
        try:
            for idx in range(100):
                try:
                    rec = msg.get_record(idx)
                    if rec is None:
                        break
                    entry_type = getattr(rec, "get_entry_type", lambda: None)()
                    if entry_type is None:
                        continue

                    # Best-effort decode strings
                    def _try_str(value):
                        if isinstance(value, bytes):
                            try:
                                return value.decode("utf-8")
                            except UnicodeDecodeError:
                                return value.decode("latin-1", errors="replace")
                        return str(value) if value is not None else ""

                    try:
                        if hasattr(rec, "get_subject"):
                            result["subject"] = _try_str(rec.get_subject())
                        elif hasattr(rec, "get_value_as_string"):
                            txt = _try_str(rec.get_value_as_string())
                            if txt and not result["subject"]:
                                result["subject"] = txt
                    except Exception:
                        pass
                except Exception:
                    break
        except Exception:
            pass
        return result

    # -- Backwards-compatible single-result contract -----------------------

    def extract(self, source: Path, *, progress=None) -> dict:
        """Legacy single-result path. Returns the first message, or a status
        stub if the PST is empty or no backend is available."""
        try:
            msgs = self.extract_messages(source, progress=progress)
        except AdapterError:
            raise
        except Exception as e:
            raise AdapterError(f"PST extraction failed on {source}: {e}") from e
        if not msgs:
            return {
                "title": source.stem,
                "body_md": (f"# {source.stem}\n\n> PST archive contains no messages.\n"),
                "metadata": {
                    "engine": self.name,
                    "source_format": ".pst",
                    "byte_size": source.stat().st_size,
                    "message_count": 0,
                },
                "attachments": [],
            }
        # In the single-result contract, surface the count + first message
        first = msgs[0]
        first["metadata"]["message_count"] = len(msgs)
        return first
