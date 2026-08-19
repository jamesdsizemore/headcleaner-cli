"""Immutable OCR profiles and deterministic profile selection."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass

_PROFILE_NAMES = frozenset({"fast", "balanced", "archival", "handwriting_experimental"})


@dataclass(frozen=True)
class OCRProfile:
    name: str
    preprocess_steps: tuple[str, ...]
    tesseract_psm: int
    requested_languages: tuple[str, ...]
    retry_policy: str

    def __post_init__(self) -> None:
        if self.name not in _PROFILE_NAMES:
            raise ValueError(f"invalid OCR profile: {self.name}")
        if self.tesseract_psm < 0:
            raise ValueError("tesseract PSM must be non-negative")
        if not self.requested_languages:
            raise ValueError("OCR profile requires at least one language")


OCR_PROFILES = {
    "fast": OCRProfile("fast", ("grayscale",), 6, ("eng",), "none"),
    "balanced": OCRProfile("balanced", ("grayscale", "deskew"), 6, ("eng",), "rotate_once"),
    "archival": OCRProfile(
        "archival", ("grayscale", "deskew", "denoise"), 4, ("eng",), "rotate_once"
    ),
    "handwriting_experimental": OCRProfile(
        "handwriting_experimental", ("grayscale", "deskew", "denoise"), 11, ("eng",), "rotate_once"
    ),
}


def get_profile(name: str) -> OCRProfile:
    """Return a shipped immutable profile or an actionable selection error."""
    try:
        return OCR_PROFILES[name]
    except KeyError as error:
        available = ", ".join(sorted(OCR_PROFILES))
        raise ValueError(f"unknown OCR profile {name!r}; available: {available}") from error


def installed_languages(executable: str) -> tuple[str, ...]:
    """Return installed Tesseract language codes from one declared invocation."""
    result = subprocess.run(
        [executable, "--list-langs"], capture_output=True, text=True, check=True
    )
    lines = [line.strip() for line in result.stdout.splitlines()]
    return tuple(
        sorted(line for line in lines if line and not line.startswith("List of available"))
    )


def validate_requested_languages(
    requested: Iterable[str], installed: Iterable[str]
) -> tuple[str, ...]:
    """Return normalized requested languages or an actionable availability error."""
    normalized = tuple(dict.fromkeys(code.strip() for code in requested if code.strip()))
    missing = sorted(set(normalized).difference(installed))
    if missing:
        raise ValueError(f"OCR_LANGUAGE_UNAVAILABLE: {', '.join(missing)}")
    return normalized
