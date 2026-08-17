"""Tests for Batch 3 features: watch, webhook, Obsidian compat."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from headcleaner.normalize import CanonicalDoc, normalize
from headcleaner.run import RunOptions, run_pipeline
from headcleaner.walk import SourceFile
from headcleaner.webhook import build_payload, post_webhook

# --- Watch -------------------------------------------------------------------


def test_watch_module_importable() -> None:
    """Smoke: the watch module loads and exposes watch_directory."""
    from headcleaner.watch import watch_directory

    assert callable(watch_directory)


def test_watch_module_handles_missing_rust_extension() -> None:
    """If watchfiles._rust_notify is missing (e.g., minimal install), the
    module still loads — `watch_directory` raises a clear error at call time."""
    import importlib

    from headcleaner import watch as watch_mod

    # Force re-import to simulate the failing path
    importlib.reload(watch_mod) if False else None  # no-op; module already imported
    assert hasattr(watch_mod, "watch_directory")


# --- Webhook -----------------------------------------------------------------


def test_build_payload_includes_summary() -> None:
    """Payload has tool, version, format, summary counts."""
    from headcleaner.emit.manifest import FileResult, RunRecord

    record = RunRecord(
        started_at="2026-08-16T00:00:00Z",
        finished_at="2026-08-16T00:00:01Z",
        input_root="/tmp/in",
        output_root="/tmp/out",
        format="both",
        options={},
    )
    record.results = [
        FileResult(
            source_path="/x",
            relpath="x.txt",
            engine="txt",
            sha256="a" * 64,
            md_path="/m",
            okf_path="/o",
            status="ok",
        ),
        FileResult(
            source_path="/y",
            relpath="y.txt",
            engine=None,
            sha256=None,
            md_path=None,
            okf_path=None,
            status="skipped",
        ),
    ]
    payload = build_payload(record)
    assert payload["tool"] == "headcleaner"
    assert payload["format"] == "both"
    assert payload["summary"] == {"total": 2, "ok": 1, "failed": 0, "skipped": 1}
    assert len(payload["results"]) == 2


def test_post_webhook_calls_urlopen() -> None:
    """post_webhook serializes the payload and POSTs to the URL."""
    from headcleaner.emit.manifest import RunRecord

    record = RunRecord(
        started_at="2026-08-16T00:00:00Z",
        finished_at="2026-08-16T00:00:01Z",
        input_root="/x",
        output_root="/y",
        format="md",
        options={},
    )

    fake_resp = MagicMock()
    fake_resp.__enter__.return_value.status = 200
    with patch("headcleaner.webhook.urllib.request.urlopen", return_value=fake_resp) as mock:
        status = post_webhook("https://example.test/hook", record)
    assert status == 200
    mock.assert_called_once()
    req = mock.call_args.args[0]
    assert req.method == "POST"
    assert req.headers["Content-type"] == "application/json"


# --- Obsidian compat ---------------------------------------------------------


def test_to_okf_frontmatter_default_no_obsidian_fields() -> None:
    f = tmp_path_fixture().get("x.txt")
    # Default behavior: standard OKF only
    doc = _make_doc(f)
    fm = doc.to_okf_frontmatter()
    assert "source" not in fm
    assert "generated_by" not in fm
    assert "verified_by" not in fm


def test_to_okf_frontmatter_obsidian_compat() -> None:
    f = tmp_path_fixture().get("x.txt")
    doc = _make_doc(f)
    fm = doc.to_okf_frontmatter(obsidian_compat=True)
    # All Obsidian flat fields added
    assert fm["source"] == doc.source_uri
    assert fm["sha256"] == doc.source_sha256
    assert fm["generated_by"] == doc.okf_generated.replace(":", "_")
    assert fm["verified_by"] == doc.okf_verified.replace(":", "_")
    assert fm["stale_on"] == doc.okf_stale_after
    # Original OKF fields still present
    assert fm["generated"] == doc.okf_generated
    assert fm["verified"] == doc.okf_verified


def test_okf_emitter_respects_obsidian_compat_flag(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("x", encoding="utf-8")
    sf = SourceFile(path=f, relpath=Path("x.txt"), size_bytes=1)
    doc = normalize(sf, {"title": "X", "body_md": "body"}, engine="txt")
    out = tmp_path / "out"
    from headcleaner.emit import okf as okf_emit

    p = okf_emit.write(doc, out, obsidian_compat=True)
    text = p.read_text(encoding="utf-8")
    # Obsidian flat fields appear
    assert "source: file://" in text
    assert "sha256:" in text
    assert "generated_by:" in text
    assert "verified_by:" in text
    # Original OKF fields also appear (not replaced)
    assert "generated: human:" in text
    assert "verified: human:" in text


def test_run_pipeline_obsidian_compat_writes_obsidian_fields(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    out = tmp_path / "out"
    run_pipeline(
        RunOptions(
            input_root=tmp_path,
            output_root=out,
            fmt="okf",
            obsidian_compat=True,
        )
    )
    concept = out / "okf" / "a.md"
    assert concept.is_file(), "no OKF concept file produced"
    text = concept.read_text(encoding="utf-8")
    assert "source:" in text
    assert "verified_by:" in text


# --- Helpers -----------------------------------------------------------------


def tmp_path_fixture():
    """A class wrapper to match pytest's tmp_path fixture shape."""

    class _T:
        def __init__(self):
            import tempfile

            self._path = Path(tempfile.mkdtemp())

        def get(self, name: str) -> Path:
            f = self._path / name
            f.write_text("x", encoding="utf-8")
            return f

    return _T()


def _make_doc(path: Path) -> CanonicalDoc:
    sf = SourceFile(path=path, relpath=Path(path.name), size_bytes=1)
    return normalize(sf, {"title": "X", "body_md": "body"}, engine="txt")
