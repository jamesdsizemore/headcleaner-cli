from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from headcleaner.cli import cli
from headcleaner.engine_plan import EngineCapability, build_engine_plan
from headcleaner.router import engine_capabilities


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


def test_default_plan_schedules_fallback_only_when_explicitly_allowed() -> None:
    first = EngineCapability("primary", frozenset({".txt"}), (), "never", 1, frozenset())
    second = EngineCapability("fallback", frozenset({".txt"}), (), "never", 2, frozenset())

    strict = build_engine_plan(Path("note.txt"), [first, second])
    permissive = build_engine_plan(Path("note.txt"), [first, second], allow_fallback=True)

    assert [attempt.engine for attempt in strict.attempts] == ["primary"]
    assert [attempt.engine for attempt in permissive.attempts] == ["primary", "fallback"]


def test_plan_records_unavailable_required_tool_before_fallback() -> None:
    unavailable = EngineCapability(
        "primary", frozenset({".txt"}), ("missing-tool",), "never", 1, frozenset()
    )
    fallback = EngineCapability("fallback", frozenset({".txt"}), (), "never", 2, frozenset())

    plan = build_engine_plan(
        Path("note.txt"),
        [unavailable, fallback],
        allow_fallback=True,
        available_tools=frozenset(),
    )

    assert [(attempt.engine, attempt.outcome) for attempt in plan.attempts] == [
        ("primary", "unavailable"),
        ("fallback", "planned"),
    ]
    assert plan.attempts[0].reason == "required-tool-unavailable"
    assert plan.attempts[0].diagnostic_codes == ("ENGINE_REQUIRED_TOOL_UNAVAILABLE",)


def test_network_capability_requires_explicit_permission() -> None:
    network = EngineCapability("remote", frozenset({".txt"}), (), "explicit", 1, frozenset())

    with pytest.raises(ValueError, match="allow-network"):
        build_engine_plan(Path("note.txt"), [network])

    allowed = build_engine_plan(Path("note.txt"), [network], allow_network=True)
    assert allowed.attempts[0].engine == "remote"


def test_live_router_capabilities_preserve_current_extension_precedence() -> None:
    capabilities = engine_capabilities()

    plan = build_engine_plan(Path("note.txt"), capabilities)

    assert plan.attempts[0].engine == "txt"


def test_convert_help_exposes_engine_plan_policy_flags() -> None:
    result = CliRunner().invoke(cli, ["convert", "--help"])

    assert result.exit_code == 0
    for option in ("--engine", "--no-fallback", "--allow-fallback", "--allow-network"):
        assert option in result.output
