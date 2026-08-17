# OKF frontmatter schema

`okf-frontmatter.schema.json` is a Draft-7 JSON Schema for the YAML frontmatter
emitted by headcleaner in OKF v0.2 concepts. It validates the required `type`
and `title`, trust/status fields, source provenance, SHA-256 patterns, and the
optional Obsidian-compatible flat fields.

## VS Code

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

## JetBrains IDEs

Open **Settings → Languages & Frameworks → Schemas and DTDs → JSON Schema
Mappings**, add `okf-frontmatter.schema.json`, and map it to the relevant
`okf/**/*.md` files. Enable YAML frontmatter schema support if the IDE prompts
for it.

The schema is intentionally permissive about additional properties so OKF
bundles can add domain-specific metadata without breaking editor validation.
