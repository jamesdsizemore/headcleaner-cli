from __future__ import annotations

import hashlib
from pathlib import Path


def test_sync_detects_rename_and_refuses_modified_generated_delete(tmp_path: Path) -> None:
    from headcleaner.sync import SyncRecord, load_state, reconcile

    output = tmp_path / "out"
    generated = output / "old.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated", encoding="utf-8")
    record = SyncRecord("a" * 64, "old.txt", (), ("old.md",), 1, {"old.md": "hash"}, "now")
    plan = reconcile([record], {"new.txt": "a" * 64}, output, dry_run=True)
    assert plan[0]["status"] == "renamed"
    assert not load_state(output)
    applied = reconcile([record], {"new.txt": "a" * 64}, output, apply=True)
    assert applied[0]["status"] == "renamed"
    persisted = load_state(output)
    assert persisted[0].current_relpath == "new.txt"
    assert persisted[0].prior_relpaths == ("old.txt",)
    assert persisted[0].generation == 2
    generated.write_text("user edit", encoding="utf-8")
    deletion = reconcile([record], {}, output, dry_run=True)
    assert deletion[0]["status"] == "SYNC_CONFLICT"
    conflict_apply = reconcile([record], {}, output, apply=True, prune_generated=True)
    assert conflict_apply[0]["status"] == "SYNC_CONFLICT"
    assert load_state(output)[0].current_relpath == "old.txt"


def test_sync_prunes_only_declared_unmodified_generated_output_on_explicit_apply(
    tmp_path: Path,
) -> None:
    from headcleaner.sync import SyncRecord, reconcile

    output = tmp_path / "out"
    generated = output / "old.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated", encoding="utf-8")
    record = SyncRecord(
        "a" * 64,
        "old.txt",
        (),
        ("old.md",),
        1,
        {"old.md": "e0cb800a5ccda4cb1b2ad7990de082aaa1e40e771898c0bcb28fcb23c261e422"},
        "now",
    )

    plan = reconcile([record], {}, output, apply=True, prune_generated=True)

    assert plan[0]["status"] == "pruned"
    assert not generated.exists()


def test_sync_state_round_trip_is_atomic_and_corruption_is_rejected(tmp_path: Path) -> None:
    import pytest

    from headcleaner.sync import SyncRecord, load_state, save_state, state_path

    record = SyncRecord("a" * 64, "source.txt", (), ("source.md",), 1, {}, "now")
    path = save_state(tmp_path, [record])

    assert path == state_path(tmp_path)
    assert load_state(tmp_path) == [record]

    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="SYNC_STATE_CORRUPT"):
        load_state(tmp_path)


def test_sync_cli_reports_corrupt_state_without_traceback(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from headcleaner.cli import cli
    from headcleaner.sync import state_path

    input_root = tmp_path / "input"
    input_root.mkdir()
    output = tmp_path / "output"
    state_path(output).parent.mkdir(parents=True)
    state_path(output).write_text("{not-json", encoding="utf-8")

    result = CliRunner().invoke(cli, ["sync", str(input_root), str(output)])

    assert result.exit_code != 0
    assert "SYNC_STATE_CORRUPT" in result.output
    assert "Traceback" not in result.output


def test_plan_sync_uses_durable_state_and_never_applies_changes(tmp_path: Path) -> None:
    from headcleaner.sync import SyncRecord, plan_sync, save_state

    input_root = tmp_path / "input"
    output_root = tmp_path / "output"
    input_root.mkdir()
    output_root.mkdir()
    source = input_root / "note.html"
    source.write_text("current", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    save_state(
        output_root,
        [SyncRecord(sha, "note.html", (), ("_md/note.html.md",), 1, {}, "now")],
    )

    assert plan_sync(input_root, output_root) == [{"status": "unchanged", "path": "note.html"}]
