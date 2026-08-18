"""Deterministic engine-selection plans and bounded fallback policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineCapability:
    name: str
    extensions: frozenset[str]
    requires_tools: tuple[str, ...]
    network_mode: str
    priority: int
    supports_traits: frozenset[str]

    def __post_init__(self) -> None:
        if self.network_mode not in {"never", "explicit"}:
            raise ValueError("network_mode must be never or explicit")


@dataclass(frozen=True)
class EngineAttempt:
    engine: str
    reason: str
    outcome: str = "planned"
    diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnginePlan:
    source: Path
    requested_engine: str | None
    attempts: tuple[EngineAttempt, ...]


def build_engine_plan(
    source: Path,
    capabilities: list[EngineCapability],
    *,
    requested_engine: str | None = None,
    allow_fallback: bool = False,
    allow_network: bool = False,
    available_tools: frozenset[str] | None = None,
) -> EnginePlan:
    """Build a stable extension-compatible plan without running an engine."""
    compatible = sorted(
        (
            capability
            for capability in capabilities
            if source.suffix.lower() in capability.extensions
        ),
        key=lambda capability: (capability.priority, capability.name),
    )
    if requested_engine is not None:
        requested = [capability for capability in compatible if capability.name == requested_engine]
        alternatives = [
            capability for capability in compatible if capability.name != requested_engine
        ]
        compatible = requested + alternatives
        if not compatible or compatible[0].name != requested_engine:
            raise ValueError(f"unknown or incompatible engine: {requested_engine}")
        if not allow_fallback:
            compatible = compatible[:1]
    elif not allow_fallback:
        compatible = compatible[:1]
    for capability in compatible:
        if capability.network_mode == "explicit" and not allow_network:
            raise ValueError(f"engine {capability.name} requires --allow-network")
    return EnginePlan(
        source=source,
        requested_engine=requested_engine,
        attempts=tuple(
            EngineAttempt(
                engine=capability.name,
                reason=(
                    "required-tool-unavailable"
                    if available_tools is not None
                    and not set(capability.requires_tools).issubset(available_tools)
                    else "requested"
                    if requested_engine
                    else "router-priority"
                ),
                outcome=(
                    "unavailable"
                    if available_tools is not None
                    and not set(capability.requires_tools).issubset(available_tools)
                    else "planned"
                ),
                diagnostic_codes=(
                    ("ENGINE_REQUIRED_TOOL_UNAVAILABLE",)
                    if available_tools is not None
                    and not set(capability.requires_tools).issubset(available_tools)
                    else ()
                ),
            )
            for capability in compatible
        ),
    )
