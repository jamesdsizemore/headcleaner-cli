"""Doctor guidance must use the same readpst discovery as the PST adapter."""

from __future__ import annotations

import headcleaner.doctor as doctor


def test_doctor_reports_readpst_found_by_adapter_discovery(monkeypatch) -> None:
    monkeypatch.setattr(
        doctor,
        "_readpst_available",
        lambda: r"C:\msys64\ucrt64\bin\readpst.exe",
        raising=False,
    )

    result = doctor.check_readpst()

    assert result.status == doctor.STATUS_OK
    assert "C:\\msys64\\ucrt64\\bin\\readpst.exe" in result.detail


def test_doctor_recommends_verified_msys2_provisioning(monkeypatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)

    result = doctor.check_readpst()

    assert result.status == doctor.STATUS_WARN
    assert result.fix is not None
    assert "mingw-w64-ucrt-x86_64-libpst" in result.fix
    assert "HEADCLEANER_READPST" in result.fix
