"""Legacy Office adapter — convert `.doc`, `.xls`, and `.ppt` through LibreOffice.

LibreOffice provides the only broadly maintained cross-platform conversion path
for pre-2007 Office binaries.  This adapter converts each source in an isolated
temporary directory, then delegates the produced DOCX/XLSX/PPTX to the existing
modern Office adapter (office_oxide first, OfficeCLI fallback).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from .base import Adapter, AdapterError

_TARGET_FORMATS = {".doc": "docx", ".xls": "xlsx", ".ppt": "pptx"}
_DEFAULT_BINARIES = ("soffice.com", "libreoffice", "soffice")


def _modern_adapter() -> Adapter:
    """Build the established adapter for post-2007 Office documents."""
    from .officecli import OfficeCLIAdapter

    return OfficeCLIAdapter()


class LegacyOfficeAdapter(Adapter):
    """Convert legacy Office binaries with LibreOffice before extraction."""

    name = "legacy_office"
    extensions = set(_TARGET_FORMATS)

    def __init__(
        self,
        binary: str | None = None,
        timeout: int = 120,
        modern_adapter_factory: Callable[[], Adapter] | None = None,
    ) -> None:
        self.binary = binary
        self.timeout = timeout
        self._modern_adapter_factory = modern_adapter_factory or _modern_adapter

    def _resolve_binary(self) -> str | None:
        candidates = (self.binary,) if self.binary else _DEFAULT_BINARIES
        for candidate in candidates:
            if candidate:
                found = shutil.which(candidate)
                if found:
                    return found
        return None

    def extract(self, source: Path, *, progress=None) -> dict:
        target = _TARGET_FORMATS.get(source.suffix.lower())
        if target is None:
            raise AdapterError(f"Unsupported legacy Office format: {source.suffix}")

        binary = self._resolve_binary()
        if binary is None:
            raise AdapterError(
                f"LibreOffice is required to convert {source.suffix.lower()} files to .{target}. "
                "Install LibreOffice, ensure `soffice` or `libreoffice` is on PATH, then retry. "
                f"Manual equivalent: libreoffice --headless --convert-to {target} {source.name}"
            )

        with tempfile.TemporaryDirectory(prefix="headcleaner-legacy-") as tmp:
            out_dir = Path(tmp)
            profile_dir = out_dir / "libreoffice-profile"
            profile_dir.mkdir()
            command = [
                binary,
                "--headless",
                f"-env:UserInstallation={profile_dir.as_uri()}",
                "--convert-to",
                target,
                "--outdir",
                str(out_dir),
                str(source),
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise AdapterError(f"LibreOffice binary not found: {binary}") from exc
            except subprocess.TimeoutExpired as exc:
                raise AdapterError(
                    f"LibreOffice timed out after {self.timeout}s converting {source.name}"
                ) from exc

            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()[:500]
                message = (
                    f"LibreOffice failed converting {source.name} "
                    f"(exit {completed.returncode}): {detail}"
                )
                raise AdapterError(message)

            converted = out_dir / f"{source.stem}.{target}"
            if not converted.is_file():
                candidates = sorted(out_dir.glob(f"*.{target}"))
                if len(candidates) == 1:
                    converted = candidates[0]
                else:
                    detail = (completed.stderr or completed.stdout).strip()[:500]
                    raise AdapterError(
                        f"LibreOffice reported success but produced no {target.upper()} file for "
                        f"{source.name}. {detail}"
                    )

            result = self._modern_adapter_factory().extract(converted, progress=progress)

        metadata = dict(result.get("metadata", {}))
        metadata.update(
            {
                "engine": self.name,
                "legacy_source_format": source.suffix.lower(),
                "converted_format": f".{target}",
                "converted_with": Path(binary).name,
            }
        )
        return {**result, "metadata": metadata}
