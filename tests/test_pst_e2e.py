"""End-to-end test: PST per-message extraction through the full run pipeline.

We monkey-patch the readpst call to use a real mbox file we build on disk,
so the test doesn't depend on readpst being installed on the host.
"""
from __future__ import annotations

import mailbox
import tempfile
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def fake_mbox(tmp_path: Path) -> Path:
    """Build a mbox with 3 messages and return its path."""
    p = tmp_path / "fake.mbox"
    mbox = mailbox.mbox(str(p))
    try:
        for i, (subject, body) in enumerate(
            [
                ("First message", "Body of message 1"),
                ("Second message", "Body of message 2"),
                ("Third message", "Body of message 3"),
            ],
            start=1,
        ):
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"sender{i}@example.com"
            msg["To"] = f"recipient@example.com"
            msg["Date"] = "Sun, 16 Aug 2026 12:00:00 +0000"
            msg.set_content(body)
            mbox.add(msg)
    finally:
        mbox.close()
    return p


def test_extract_documents_multi_concept(
    tmp_path: Path, fake_mbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PstAdapter.extract_messages returns 3 dicts, _extract_documents maps to 3 pairs."""
    import shutil
    from headcleaner.engines import pst as pst_mod
    from headcleaner.run import _run_adapter

    def fake_readpst_available() -> str | None:
        return "/fake/readpst"

    def fake_run_readpst(pst_path: Path, tmp_dir: Path) -> Path:
        # Copy our fake mbox into tmp_dir where readpst would have written
        dest = tmp_dir / "fake.mbox"
        shutil.copy(fake_mbox, dest)
        return dest

    monkeypatch.setattr(pst_mod, "_readpst_available", fake_readpst_available)
    monkeypatch.setattr(pst_mod, "_run_readpst", fake_run_readpst)

    adapter = pst_mod.PstAdapter()
    pst_path = tmp_path / "inbox.pst"
    pst_path.write_bytes(b"fake pst contents")

    pairs = _run_adapter(adapter, pst_path, "inbox.pst", ocr=False, on_engine_progress=None)
    assert len(pairs) == 3
    relpaths = [rp for rp, _ in pairs]
    # Per-message relpath pattern: inbox-0001.md, inbox-0002.md, inbox-0003.md
    assert relpaths[0] == "inbox-0001.md"
    assert relpaths[1] == "inbox-0002.md"
    assert relpaths[2] == "inbox-0003.md"
    # Each dict has the expected shape
    for _rp, extracted in pairs:
        assert "body_md" in extracted
        assert "title" in extracted
        assert "metadata" in extracted
        assert extracted["metadata"]["engine"] == "pst"
        assert extracted["metadata"]["message_index"] in {1, 2, 3}


def test_run_pipeline_emits_one_concept_per_message(
    tmp_path: Path, fake_mbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full run_pipeline emits N FileResults for a PST with N messages."""
    import shutil
    from headcleaner.engines import pst as pst_mod
    from headcleaner.run import RunOptions, run_pipeline

    monkeypatch.setattr(pst_mod, "_readpst_available", lambda: "/fake/readpst")

    def fake_run_readpst(pst_path: Path, tmp_dir: Path) -> Path:
        dest = tmp_dir / "fake.mbox"
        shutil.copy(fake_mbox, dest)
        return dest

    monkeypatch.setattr(pst_mod, "_run_readpst", fake_run_readpst)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    pst_path = inbox / "archive.pst"
    pst_path.write_bytes(b"fake pst")

    output = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=inbox, output_root=output, fmt="okf"))

    # 3 messages -> 3 OKF concept files (index.md is auto-generated, excluded)
    okf_files = sorted(p for p in (output / "okf").glob("*.md") if p.name != "index.md")
    assert len(okf_files) == 3, f"expected 3 OKF files, got {okf_files}"
    # All records reached the manifest
    assert len(record.results) == 3
    # All messages were emitted successfully
    assert all(r.status == "ok" for r in record.results)
    # Per-message relpaths derived correctly
    relpaths = sorted(r.relpath for r in record.results)
    assert relpaths == ["archive-0001.md", "archive-0002.md", "archive-0003.md"]


def test_run_pipeline_multi_message_via_extra_glob(
    tmp_path: Path, fake_mbox: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A single PST plus a single TXT file: 3 + 1 = 4 results."""
    import shutil
    from headcleaner.engines import pst as pst_mod
    from headcleaner.run import RunOptions, run_pipeline

    monkeypatch.setattr(pst_mod, "_readpst_available", lambda: "/fake/readpst")

    def fake_run_readpst(pst_path: Path, tmp_dir: Path) -> Path:
        dest = tmp_dir / "fake.mbox"
        shutil.copy(fake_mbox, dest)
        return dest

    monkeypatch.setattr(pst_mod, "_run_readpst", fake_run_readpst)

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "archive.pst").write_bytes(b"fake pst")
    (inbox / "notes.txt").write_text("Plain text notes\n", encoding="utf-8")

    output = tmp_path / "out"
    record = run_pipeline(RunOptions(input_root=inbox, output_root=output, fmt="okf"))

    # 3 messages from PST + 1 from TXT = 4 FileResults
    assert len(record.results) == 4
    # 4 OKF files (index.md is auto-generated, excluded)
    okf_files = sorted(p for p in (output / "okf").glob("*.md") if p.name != "index.md")
    assert len(okf_files) == 4
    # Verify the 3 PST concepts all have engine=pst, the TXT has engine=txt
    engines = [r.engine for r in record.results]
    assert engines.count("pst") == 3
    assert engines.count("txt") == 1
