# OKF frontmatter JSON Schema

HeadCleaner's schema for its emitted OKF v0.2 frontmatter is:

- [`schemas/okf-frontmatter.schema.json`](schemas/okf-frontmatter.schema.json)

It is a JSON Schema Draft 7 document covering the standard output fields, trust and
provenance fields, source hashes, lifecycle statuses, and the optional Obsidian-compatible
flat fields.

## Validate extracted frontmatter

The schema describes the YAML object between a concept file's opening `---` delimiters.
After parsing that YAML into an object, validate it with any Draft 7 validator:

```python
import json
from pathlib import Path

import jsonschema
import yaml

schema = json.loads(
    Path("docs/schemas/okf-frontmatter.schema.json").read_text(encoding="utf-8")
)
frontmatter = yaml.safe_load(frontmatter_text)
jsonschema.validate(frontmatter, schema)
```

## Editor integration

Associate the schema with YAML frontmatter in an editor or extension that supports
Markdown frontmatter schema mappings. For a standalone `.yaml` frontmatter file, the VS
Code YAML extension accepts this workspace setting:

```json
{
  "yaml.schemas": {
    "./docs/schemas/okf-frontmatter.schema.json": "frontmatter/**/*.yaml"
  }
}
```

In JetBrains IDEs, open **Settings → Languages & Frameworks → Schemas and DTDs → JSON
Schema Mappings**, add the schema file, and map it to the YAML files or frontmatter files
used by the project. Native editor support for applying a JSON Schema inside a Markdown
frontmatter block varies by editor; the schema itself remains usable from CI and custom
validation tools.

## Trust behavior

The schema accepts HeadCleaner's lifecycle values (`unverified`,
`machine-confirmed`, `human-reviewed`, `deprecated`, and `stale`).
Auto-conversion still emits only `unverified` with
`verified: human:pending`; schema validation never claims review.
