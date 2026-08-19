from __future__ import annotations

import sys
import types

import pytest

from headcleaner.engines.pdf import PdfAdapter
from headcleaner.ocr import (
    OCR_PROFILES,
    OCRProfile,
    get_profile,
    installed_languages,
    validate_requested_languages,
)


def test_shipped_ocr_profiles_are_immutable_and_selectable() -> None:
    profile = get_profile("balanced")

    assert profile is OCR_PROFILES["balanced"]
    assert profile.tesseract_psm == 6
    assert profile.requested_languages == ("eng",)
    with pytest.raises(AttributeError):
        profile.name = "mutated"  # type: ignore[misc]


def test_unknown_ocr_profile_is_actionable() -> None:
    with pytest.raises(ValueError, match="unknown OCR profile"):
        get_profile("unknown")


def test_ocr_profile_rejects_undeclared_name() -> None:
    with pytest.raises(ValueError, match="invalid OCR profile"):
        OCRProfile("custom", (), 6, ("eng",), "none")


def test_installed_languages_parses_one_tesseract_invocation(monkeypatch) -> None:
    calls = []

    class Result:
        stdout = "List of available languages in C:\\tessdata (3):\neng\nfra\ndeu\n"

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    monkeypatch.setattr("headcleaner.ocr.subprocess.run", fake_run)

    assert installed_languages("tesseract") == ("deu", "eng", "fra")
    assert calls == [
        (["tesseract", "--list-langs"], {"capture_output": True, "text": True, "check": True})
    ]


def test_requested_ocr_languages_fail_with_machine_readable_code() -> None:
    assert validate_requested_languages(("eng", "fra", "eng"), ("eng", "fra")) == ("eng", "fra")

    with pytest.raises(ValueError, match="OCR_LANGUAGE_UNAVAILABLE: deu"):
        validate_requested_languages(("eng", "deu"), ("eng",))


def test_image_only_ocr_uses_declared_profile_and_languages(monkeypatch) -> None:
    calls = []
    fake_tesseract = types.SimpleNamespace(
        image_to_string=lambda image, **kwargs: calls.append((image, kwargs)) or " recognized "
    )
    monkeypatch.setitem(sys.modules, "pytesseract", fake_tesseract)

    class Page:
        def to_image(self, *, resolution):
            assert resolution == 300
            return types.SimpleNamespace(original="page-image")

    adapter = PdfAdapter(ocr=True, ocr_lang="eng+fra", ocr_profile="archival")

    assert adapter._ocr_page(Page()) == "recognized"
    assert calls == [("page-image", {"lang": "eng+fra", "config": "--psm 4"})]
