"""Deterministic, local-only versioned policy packs.

Packs are declarative TOML. They never execute expressions, fetch remote content,
or replace the legacy :mod:`headcleaner.policy` conversion policy.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_PACK_ID = re.compile(r"^[a-z][a-z0-9-]*$")
_SEVERITIES = {"info", "warning", "error"}
_CONDITIONS = {
    "sources.missing",
    "verified.pending",
    "diagnostics.present",
    "readiness.not_ready",
    "redaction.proposed",
    "stale.expired",
}


@dataclass(frozen=True)
class PackRule:
    id: str
    severity: str
    when: str
    message: str


@dataclass(frozen=True)
class PolicyPack:
    id: str
    version: str
    description: str
    rules: tuple[PackRule, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialize stable pack metadata without altering declared rule order."""
        return {
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "rules": [
                {
                    "id": rule.id,
                    "severity": rule.severity,
                    "when": rule.when,
                    "message": rule.message,
                }
                for rule in self.rules
            ],
        }


@dataclass(frozen=True)
class PackFinding:
    rule_id: str
    severity: str
    message: str
    concept_ref: str
    evidence: dict[str, Any]


def _safe_pack_path(root: Path, pack_id: str) -> Path:
    if not _PACK_ID.fullmatch(pack_id):
        raise ValueError("pack id must be a lowercase local identifier")
    candidate = (root / f"{pack_id}.toml").resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("pack path escapes its policy directory") from exc
    return candidate


def _parse_pack(path: Path) -> tuple[dict[str, Any], tuple[PackRule, ...], tuple[str, ...]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    required = ("id", "version", "extends", "description", "rules")
    if any(key not in data for key in required):
        raise ValueError(f"pack {path.name} is missing required metadata")
    if not isinstance(data["id"], str) or not _PACK_ID.fullmatch(data["id"]):
        raise ValueError("pack id must be a lowercase local identifier")
    if not isinstance(data["version"], str) or not data["version"]:
        raise ValueError("pack version is required")
    if not isinstance(data["description"], str):
        raise ValueError("pack description must be a string")
    extends = data["extends"]
    if not isinstance(extends, list) or any(not isinstance(item, str) for item in extends):
        raise ValueError("extends must be a list of local pack ids")
    rules_raw = data["rules"]
    if not isinstance(rules_raw, list):
        raise ValueError("rules must be an array")
    rules: list[PackRule] = []
    for raw in rules_raw:
        if not isinstance(raw, dict) or set(raw) != {"id", "severity", "when", "message"}:
            raise ValueError("each rule must contain id, severity, when, and message")
        rule = PackRule(**raw)
        if not _PACK_ID.fullmatch(rule.id):
            raise ValueError("rule id must be a lowercase local identifier")
        if rule.severity not in _SEVERITIES:
            raise ValueError("rule severity must be info, warning, or error")
        if rule.when not in _CONDITIONS:
            raise ValueError(f"unknown policy field path: {rule.when}")
        if not rule.message:
            raise ValueError("rule message is required")
        rules.append(rule)
    return data, tuple(rules), tuple(extends)


def load_pack(
    pack_id: str, *, installed_dir: Path, bundle_root: Path | None = None
) -> PolicyPack:
    """Resolve a pack depth-first from installed or bundle-local policy directories."""
    roots = [Path(installed_dir)]
    if bundle_root is not None:
        roots.append(Path(bundle_root) / ".headcleaner" / "policies")
    visiting: set[str] = set()
    resolved: list[PackRule] = []
    seen_rules: set[str] = set()

    def resolve(current_id: str) -> tuple[dict[str, Any], tuple[PackRule, ...]]:
        if current_id in visiting:
            raise ValueError("policy pack inheritance cycle")
        visiting.add(current_id)
        path = next((candidate for root in roots if (candidate := _safe_pack_path(root, current_id)).is_file()), None)
        if path is None:
            raise ValueError(f"policy pack not found: {current_id}")
        metadata, rules, parents = _parse_pack(path)
        if metadata["id"] != current_id:
            raise ValueError("pack id does not match its requested local identifier")
        for parent in parents:
            resolve(parent)
        for rule in rules:
            if rule.id in seen_rules:
                raise ValueError(f"duplicate rule id: {rule.id}")
            seen_rules.add(rule.id)
            resolved.append(rule)
        visiting.remove(current_id)
        return metadata, rules

    metadata, _ = resolve(pack_id)
    return PolicyPack(
        id=metadata["id"], version=metadata["version"], description=metadata["description"], rules=tuple(resolved)
    )


def _condition(when: str, frontmatter: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    if when == "sources.missing":
        value = frontmatter.get("sources")
        return not isinstance(value, list) or not value, {"field": "sources", "value": value or None}
    if when == "verified.pending":
        value = frontmatter.get("verified")
        return value == "human:pending", {"field": "verified", "value": value}
    if when == "diagnostics.present":
        value = frontmatter.get("diagnostics")
        return bool(value), {"field": "diagnostics", "value": bool(value)}
    if when == "readiness.not_ready":
        value = frontmatter.get("readiness")
        return value not in {None, "ready"}, {"field": "readiness", "value": value}
    if when == "redaction.proposed":
        value = frontmatter.get("redaction_status")
        return value == "proposed", {"field": "redaction_status", "value": value}
    value = frontmatter.get("stale_after")
    return bool(value), {"field": "stale_after", "value": value}


def evaluate_pack(pack: PolicyPack, bundle_root: Path) -> list[PackFinding]:
    """Return deterministic findings for an unchanged local bundle."""
    findings: list[PackFinding] = []
    bundle_root = Path(bundle_root)
    for path in sorted(bundle_root.rglob("*.md")):
        if path.name in {"index.md", "log.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            continue
        try:
            frontmatter = yaml.safe_load(text.split("---\n", 2)[1]) or {}
        except (IndexError, yaml.YAMLError):
            continue
        if not isinstance(frontmatter, dict) or "type" not in frontmatter:
            continue
        concept_ref = path.relative_to(bundle_root).as_posix()
        for rule in pack.rules:
            matched, evidence = _condition(rule.when, frontmatter)
            if matched:
                findings.append(PackFinding(rule.id, rule.severity, rule.message, concept_ref, evidence))
    return findings
