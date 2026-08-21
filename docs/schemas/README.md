# Schemas

This directory holds Draft-7 JSON Schemas used by headcleaner's documented
contracts. Each schema constrains what a downstream consumer can rely on; the
tests in `tests/` validate emitted payloads against them.

## `okf-frontmatter.schema.json`

The OKF v0.2 concept frontmatter emitted by `headcleaner convert`. Validates
the required `type` and `title`, trust/status fields, source provenance,
SHA-256 patterns, and the optional Obsidian-compatible flat fields.

### VS Code

Add an association to `.vscode/settings.json` in an OKF bundle:

```json
{
  "yaml.schemas": {
    "./docs/schemas/okf-frontmatter.schema.json": [
      "okf/**/*.md"
    ]
  }
}
```

Use an absolute path or a copied schema path if the schema lives outside the
bundle repository.

### JetBrains IDEs

Open **Settings → Languages & Frameworks → Schemas and DTDs → JSON Schema
Mappings**, add `okf-frontmatter.schema.json`, and map it to the relevant
`okf/**/*.md` files. Enable YAML frontmatter schema support if the IDE prompts
for it.

The schema is intentionally permissive about additional properties so OKF
bundles can add domain-specific metadata without breaking editor validation.

## `attestation.schema.json` (Contract 3.5)

The integrity attestation payload emitted by `headcleaner attest`. Requires
`tool`, `version`, `bundle_root`, `concept_count`, `concepts`,
`source_provenance`, `merkle_root`, `schema_version`, `timestamp`, and
`engines`. Rejects absolute paths in `sources[].path`, rejects any field that
implies human review/approval (the schema uses `additionalProperties: false`),
and validates every SHA-256 as a 64-character hex string.

The corresponding in-toto Statement projection is documented in the predicate
contract and validated by `tests/test_attestation_schema.py`, which round-trips
the emitted payload through the real `in-toto==3.1.0` DSSE `Envelope`.

## `readiness.schema.json` (Contract 3.7)

The evidence-based readiness report emitted by `headcleaner readiness`.
Requires `concept_ref`, `grade`, `score`, `deductions`, `requirements`, and
`schema_version`. Grade is restricted to
`blocked | needs_review | conditional | ready`. Each deduction must carry
`rule_id, value, threshold, contribution, citation`. Validated by
`tests/test_readiness.py`.

## `redaction.schema.json` (Contract 3.3)

The redaction finding emitted by `headcleaner redact`. Requires `id`,
`category`, `detector`, `confidence`, `citation`, `replacement`, `status`,
`value_sha256`, `concept_ref`, and `suppression_reason`. The schema refuses
raw matched text — only the SHA-256 digest of the matched value is persisted.
Validated by `tests/test_redaction_schema.py`.
