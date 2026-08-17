"""Pluggable trust policy (Eng #35).

Reads a TOML policy file that declares required trust family fields
for every emitted concept. If any concept violates the policy, the
run is rejected with a clear error report.

Example `policy.toml`:

    [policy]
    # All emitted concepts must have these fields set with non-empty values.
    require_type = "Document"        # or "*" to accept any non-empty string
    require_status = ["unverified"] # or "*" to accept any non-empty string
    require_verified = ["human:pending"]  # or "*"
    require_sources = true           # sources[] must be present + non-empty
    require_sha256 = true            # each source.sha256 must be 64-char hex

    [policy.minimum]
    type = "Document"   # concept.type must equal this string

Usage:
    from headcleaner.policy import Policy, evaluate
    policy = Policy.load(Path("./policy.toml"))
    findings = evaluate(policy, manifest_path)
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PolicyFinding:
    file: Path
    severity: str  # "error" | "warning"
    rule: str
    message: str


@dataclass
class Policy:
    require_type: str = "*"
    require_status: list[str] = field(default_factory=lambda: ["*"])
    require_verified: list[str] = field(default_factory=lambda: ["*"])
    require_sources: bool = False
    require_sha256: bool = False

    @classmethod
    def load(cls, path: Path) -> "Policy":
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        pol = data.get("policy", {})
        return cls(
            require_type=pol.get("require_type", "*"),
            require_status=pol.get("require_status", ["*"]),
            require_verified=pol.get("require_verified", ["*"]),
            require_sources=bool(pol.get("require_sources", False)),
            require_sha256=bool(pol.get("require_sha256", False)),
        )


def _matches(field_value: str, allowed: str | list[str]) -> bool:
    """A field value passes if it matches `allowed`. "*" accepts any non-empty."""
    if allowed == "*" or allowed == ["*"]:
        return bool(field_value)
    if isinstance(allowed, list):
        return field_value in allowed
    return field_value == allowed


def evaluate(policy: Policy, bundle_root: Path) -> list[PolicyFinding]:
    """Walk every concept and check it against the policy.

    Returns one finding per violation (empty list = policy passes).
    """
    out: list[PolicyFinding] = []
    sha_re = re.compile(r"^[0-9a-f]{64}$")

    for md_path in sorted(bundle_root.rglob("*.md")):
        if md_path.name in {"index.md", "log.md"}:
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if "type" not in fm:
            continue  # not an OKF concept

        rel = str(md_path.relative_to(bundle_root))

        # type
        ctype = str(fm.get("type", ""))
        if not _matches(ctype, policy.require_type):
            out.append(
                PolicyFinding(
                    md_path,
                    "error",
                    "policy/type",
                    f"`type` is {ctype!r}, policy requires {policy.require_type!r}",
                )
            )

        # status
        cstatus = str(fm.get("status", ""))
        if not _matches(cstatus, policy.require_status):
            out.append(
                PolicyFinding(
                    md_path,
                    "error",
                    "policy/status",
                    f"`status` is {cstatus!r}, policy requires {policy.require_status!r}",
                )
            )

        # verified
        cverified = str(fm.get("verified", ""))
        if not _matches(cverified, policy.require_verified):
            out.append(
                PolicyFinding(
                    md_path,
                    "error",
                    "policy/verified",
                    f"`verified` is {cverified!r}, policy requires {policy.require_verified!r}",
                )
            )

        # sources
        sources = fm.get("sources")
        if policy.require_sources:
            if not isinstance(sources, list) or not sources:
                out.append(
                    PolicyFinding(
                        md_path,
                        "error",
                        "policy/sources",
                        "`sources[]` must be present and non-empty",
                    )
                )
                continue
            if policy.require_sha256:
                for i, src in enumerate(sources):
                    if not isinstance(src, dict):
                        out.append(
                            PolicyFinding(
                                md_path,
                                "error",
                                "policy/sources-shape",
                                f"sources[{i}] must be a dict",
                            )
                        )
                        continue
                    sha = str(src.get("sha256", ""))
                    if not sha_re.fullmatch(sha):
                        out.append(
                            PolicyFinding(
                                md_path,
                                "error",
                                "policy/sources-sha256",
                                f"sources[{i}].sha256 is not a valid 64-char hex",
                            )
                        )
    return out
