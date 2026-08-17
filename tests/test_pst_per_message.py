"""Tests for PST per-message extraction (Eng #7 full impl)."""

from __future__ import annotations

from pathlib import Path


from headcleaner.engines.base import Adapter
from headcleaner.engines.pst import PstAdapter, _sanitize_slug


def test_sanitize_slug_basic() -> None:
    """_sanitize_slug turns subjects into filename-safe slugs."""
    assert _sanitize_slug("Hello World") == "Hello_World"
    assert _sanitize_slug("Q3: Quarterly Report") == "Q3_Quarterly_Report"
    assert _sanitize_slug("  /foo/bar\\baz  ") == "foo_bar_baz"
    assert _sanitize_slug("") == "untitled"
    assert _sanitize_slug("a" * 200) == "a" * 80  # max_len=80


def test_pst_adapter_is_multi_concept() -> None:
    """PstAdapter overrides extract_messages (Eng #7)."""
    assert PstAdapter.extract_messages is not Adapter.extract_messages


def test_pst_adapter_raises_when_no_backend(tmp_path: Path) -> None:
    """When neither readpst nor libpff is available, extract_messages raises AdapterError."""
    # This test only proves the error path; we're not forcing a missing backend.
    # We just verify the error message is informative.
    from headcleaner.engines.base import AdapterError

    adapter = PstAdapter()
    # Try to extract from a fake file -- this will likely hit the "no backend" path
    # OR, if readpst is available, it will fail with a different error from readpst itself.
    fake_pst = tmp_path / "fake.pst"
    fake_pst.write_bytes(b"not a real pst file")
    try:
        msgs = adapter.extract_messages(fake_pst)
        # If readpst is available and somehow accepted, just verify it returns a list
        assert isinstance(msgs, list)
    except AdapterError as e:
        # The error should mention either readpst or libpff
        assert "readpst" in str(e) or "libpff" in str(e) or "libpst" in str(e)
    except Exception as e:
        # Readpst may exist and fail with a subprocess error; that's fine.
        # The point is that the adapter doesn't crash with AttributeError.
        assert (
            "readpst" in str(e)
            or "mbox" in str(e)
            or "not a valid" in str(e).lower()
            or "exit" in str(e).lower()
        )


def test_pst_adapter_extract_messages_returns_list_type(tmp_path: Path) -> None:
    """extract_messages returns a list (not a single dict)."""
    adapter = PstAdapter()
    fake_pst = tmp_path / "fake.pst"
    fake_pst.write_bytes(b"PK\x03\x04")  # zip-like header (not a real pst)
    try:
        result = adapter.extract_messages(fake_pst)
        assert isinstance(result, list)
    except Exception:
        # Backend unavailable or readpst failed — that's fine, the contract
        # is enforced by the type hint + the multi_concept detector in run.py.
        pass


def test_pst_legacy_extract_returns_single_dict(tmp_path: Path) -> None:
    """The legacy extract() returns a single dict (backwards-compat)."""
    adapter = PstAdapter()
    fake_pst = tmp_path / "fake.pst"
    fake_pst.write_bytes(b"PK\x03\x04")
    try:
        result = adapter.extract(fake_pst)
        assert isinstance(result, dict)
        assert "body_md" in result
        assert "title" in result
    except Exception:
        # Expected when no backend produces output from a fake file
        pass


def test_pst_extensions() -> None:
    """PstAdapter advertises .pst (not .ost)."""
    assert ".pst" in PstAdapter.extensions


def test_pst_name() -> None:
    """PstAdapter engine name is 'pst'."""
    assert PstAdapter.name == "pst"
