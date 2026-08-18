from __future__ import annotations

from pathlib import Path

import pytest

from headcleaner.engine_plan import EngineCapability, build_engine_plan


def test_default_plan_starts_with_router_selection_and_is_deterministic() -> None:
    capability = EngineCapability("txt", frozenset({".txt"}), (), "never", 10, frozenset())

    plan = build_engine_plan(Path("note.txt"), [capability])

    assert plan.attempts[0].engine == "txt"
    assert plan.requested_engine is None


def test_named_engine_disables_fallback_unless_explicitly_allowed() -> None:
    first = EngineCapability("primary", frozenset({".txt"}), (), "never", 1, frozenset())
    second = EngineCapability("fallback", frozenset({".txt"}), (), "never", 2, frozenset())

    strict = build_engine_plan(Path("note.txt"), [first, second], requested_engine="primary")
    permissive = build_engine_plan(
        Path("note.txt"), [first, second], requested_engine="primary", allow_fallback=True
    )

    assert [attempt.engine for attempt in strict.attempts] == ["primary"]
    assert [attempt.engine for attempt in permissive.attempts] == ["primary", "fallback"]


def test_network_capability_requires_explicit_permission() -> None:
    network = EngineCapability("remote", frozenset({".txt"}), (), "explicit", 1, frozenset())

    with pytest.raises(ValueError, match="allow-network"):
        build_engine_plan(Path("note.txt"), [network])

    allowed = build_engine_plan(Path("note.txt"), [network], allow_network=True)
    assert allowed.attempts[0].engine == "remote"
