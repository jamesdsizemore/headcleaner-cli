from __future__ import annotations

from pathlib import Path


def test_collect_watch_changes_retains_deleted_sources_and_excludes_output(tmp_path: Path) -> None:
    from headcleaner.watch import collect_watch_changes

    input_root = tmp_path / "input"
    output_root = input_root / "out"
    input_root.mkdir()
    output_root.mkdir()
    modified = input_root / "modified.txt"
    modified.write_text("new", encoding="utf-8")
    deleted = input_root / "deleted.txt"
    generated = output_root / "generated.md"
    generated.write_text("generated", encoding="utf-8")

    changed = collect_watch_changes(
        {(1, str(modified)), (3, str(deleted)), (2, str(generated))},
        output_root=output_root,
    )

    assert changed == {modified, deleted}
