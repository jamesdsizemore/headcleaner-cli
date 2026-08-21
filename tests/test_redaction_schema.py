from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path("docs/schemas/redaction.schema.json")


def test_redaction_schema_accepts_a_safe_finding_and_rejects_raw_value() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    finding = {
        "id": "redaction/note.md/1",
        "category": "secret",
        "detector": "regex/openai-key/v1",
        "confidence": 1.0,
        "citation": "note.md:offset:32",
        "replacement": "[REDACTED:secret]",
        "status": "proposed",
        "value_sha256": "a" * 64,
        "concept_ref": "note.md",
        "suppression_reason": None,
    }
    jsonschema.validate(finding, schema)
    finding["raw_value"] = "sk-abcdefghijklmnopqrstuvwxyz123456"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(finding, schema)
