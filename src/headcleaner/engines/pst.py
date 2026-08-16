"""PST adapter — Outlook Personal Folders (best-effort).

Requires `libpff-python` which ships binary wheels only for Windows x64
and macOS arm64. On Linux, install from source (needs libpff headers) or
convert PST to MSG first with `readpst -e`.

If the library is not installed, the adapter raises AdapterError with a
clear hint. The router treats AdapterError as a graceful failure (the
file is recorded as 'failed' in the manifest, not a crash).
"""
from __future__ import annotations

from pathlib import Path

from .base import Adapter, AdapterError


class PstAdapter(Adapter):
    name = "pst"
    extensions = {".pst"}

    def __init__(self) -> None:
        try:
            import libpff  # noqa: F401
            self._libpff = libpff
        except ImportError:
            self._libpff = None

    def extract(self, source: Path) -> dict:
        if self._libpff is None:
            raise AdapterError(
                f"libpff-python not installed; cannot read PST: {source}. "
                f"Install with `uv pip install libpff-python` (binary wheels: "
                f"Windows x64 + macOS arm64) or convert PST to MSG first "
                f"with `readpst -e <input.pst> <output_dir>`."
            )

        # We don't fully implement PST traversal in v0.3 — that's a much
        # larger piece of work (folder hierarchy, message metadata,
        # attachments, MIME conversion). We surface what libpff exposes
        # at the root: a count of top-level items.
        try:
            file_obj = self._libpff.file()
            file_obj.open(str(source))
            try:
                root = file_obj.get_root_folder()
                count = self._count_items(root) if root else 0
            finally:
                file_obj.close()
        except Exception as e:
            raise AdapterError(f"libpff failed on {source}: {e}") from e

        body_md = (
            f"# {source.stem}\n\n"
            f"> PST archive with **{count}** top-level item(s).\n\n"
            f"Full message extraction is tracked in "
            f"[ENHANCEMENTS.md #12](../ENHANCEMENTS.md). "
            f"For now, this stub records the item count so the manifest "
            f"captures the archive's existence.\n"
        )

        return {
            "title": source.stem,
            "body_md": body_md,
            "metadata": {
                "engine": self.name,
                "source_format": ".pst",
                "byte_size": source.stat().st_size,
                "item_count": count,
            },
            "attachments": [],
        }

    @staticmethod
    def _count_items(folder) -> int:
        """Recursively count items in a libpff folder. Best-effort."""
        try:
            n = folder.get_number_of_items() if hasattr(folder, "get_number_of_items") else 0
            for i in range(n):
                try:
                    sub = folder.get_item(i)
                    if sub is not None:
                        n += PstAdapter._count_items(sub)
                except Exception:
                    continue
            return n
        except Exception:
            return 0
