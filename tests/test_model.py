from __future__ import annotations

import pytest

from headcleaner.model import Element


def test_element_id_is_deterministic_from_source_kind_ordinal_and_content() -> None:
    first = Element.create("source-sha", "paragraph", 2, "  Shared text  ")
    second = Element.create("source-sha", "paragraph", 2, "Shared text")

    assert first.id == second.id
    assert first.kind == "paragraph"


@pytest.mark.parametrize("kind", ["unknown", "Heading"])
def test_element_rejects_unknown_kinds(kind: str) -> None:
    with pytest.raises(ValueError, match="kind"):
        Element.create("source-sha", kind, 0, "text")


def test_element_rejects_non_json_safe_attributes() -> None:
    with pytest.raises(ValueError, match="attributes"):
        Element.create("source-sha", "paragraph", 0, "text", attributes={"bad": {1}})


def test_element_rejects_malformed_source_location() -> None:
    with pytest.raises(ValueError, match="source_location"):
        Element.create("source-sha", "paragraph", 0, "text", source_location={"page": "one"})
