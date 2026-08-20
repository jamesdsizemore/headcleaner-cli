"""On-demand, non-destructive render/fidelity verification."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenderVerification:
    """Structured result for comparing already-created source/output artifacts."""

    source_ref: str
    output_ref: str
    renderer: str | None
    page_results: tuple[dict[str, object], ...]
    aggregate: dict[str, object]
    warnings: tuple[str, ...]
    status: str


def _anchors(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8")
    return tuple(re.sub(r"^#+\s*", "", line).strip() for line in text.splitlines() if line.strip())


def verify_render(
    source: Path,
    output: Path,
    *,
    output_dir: Path | None = None,
) -> RenderVerification:
    """Compare supported already-created artifacts without mutating conversion output."""
    supported = {".txt", ".md"}
    if source.suffix.lower() not in supported or output.suffix.lower() not in supported:
        return RenderVerification(
            source_ref=str(source),
            output_ref=str(output),
            renderer=None,
            page_results=(),
            aggregate={},
            warnings=("No compatible renderers are registered for these artifacts.",),
            status="unavailable",
        )

    matches = _anchors(source) == _anchors(output)
    page_results = (
        {
            "page_index": 0,
            "dimensions": None,
            "text_anchors_match": matches,
            "embedded_image_hashes_match": None,
            "diagnostic_codes": (),
        },
    )
    report = RenderVerification(
        source_ref=str(source),
        output_ref=str(output),
        renderer="text-structural",
        page_results=page_results,
        aggregate={"text_anchors_match": matches},
        warnings=() if matches else ("Text anchors differ; review fidelity.",),
        status="ok",
    )
    if output_dir is not None:
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        destination = output_dir / digest
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "report.json").write_text(
            json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8"
        )
    return report
