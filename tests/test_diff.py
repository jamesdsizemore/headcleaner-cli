from __future__ import annotations

from headcleaner.model import Element


def test_element_diff_detects_text_change_and_equality() -> None:
    from headcleaner.diff import diff_elements

    left = [Element.create("a" * 64, "paragraph", 0, "before")]
    right = [Element.create("a" * 64, "paragraph", 0, "after")]
    result = diff_elements(left, right, left_ref="left", right_ref="right")
    assert result.changes[0].status == "modified"
    assert diff_elements(left, left, left_ref="left", right_ref="left").changes == ()


def test_markdown_diff_surfaces_frontmatter_and_typed_table_changes() -> None:
    from headcleaner.diff import diff_markdown, render_markdown_report

    result = diff_markdown(
        "---\nstatus: unverified\n---\n\n| Amount |\n|---|\n| 10 |\n",
        "---\nstatus: reviewed\n---\n\n| Amount |\n|---|\n| 20 |\n",
        left_ref="left.md",
        right_ref="right.md",
    )

    assert any(
        change.kind == "frontmatter" and change.status == "modified" for change in result.changes
    )
    assert any(
        change.kind == "table_cell"
        and change.status == "modified"
        and change.before == "10"
        and change.after == "20"
        for change in result.changes
    )
    report = render_markdown_report(result)
    assert "left.md" in report and "right.md" in report
    assert "frontmatter" in report
