# Adapter plugins

HeadCleaner discovers third-party adapters through Python package entry points in the
`headcleaner_plugin` group. A plugin can add formats without modifying or forking
HeadCleaner.

## Package configuration

Register an `Adapter` subclass in the plugin package's `pyproject.toml`:

```toml
[project.entry-points."headcleaner_plugin"]
my-format = "my_headcleaner_plugin.adapter:MyFormatAdapter"
```

The target may be an `Adapter` subclass with a zero-argument constructor or an already
constructed `Adapter` instance.

## Minimal adapter

```python
from pathlib import Path

from headcleaner.engines.base import Adapter


class MyFormatAdapter(Adapter):
    name = "my-format"
    extensions = (".myfmt",)

    def extract(self, source: Path) -> dict:
        return {
            "title": source.stem,
            "body_md": source.read_text(encoding="utf-8"),
            "metadata": {},
            "attachments": [],
            # Optional: typed canonical structure. Dicts are validated and
            # assigned deterministic IDs when omitted.
            "elements": [
                {"kind": "paragraph", "ordinal": 0, "text": "Example"}
            ],
            # Optional structured data. Use only when faithfully available.
            "tabular_assets": [],
        }
```

Install the plugin into the same Python environment as HeadCleaner. The normal routing
path loads entry points lazily on first use:

```bash
uv pip install ./my-headcleaner-plugin
headcleaner templates
headcleaner convert ./inbox --output ./out
```

Built-in adapters have priority. Plugins are intended to claim new extensions; a plugin
cannot silently replace a built-in adapter. A plugin that cannot import, instantiate, or
satisfy the `Adapter` protocol is skipped and reported on stderr instead of preventing
HeadCleaner from starting.

## Testing a plugin

Test the adapter directly, then install the package and verify that its extension appears
in `headcleaner templates`. Plugin authors should cover `extract()` success and malformed
input behavior with pytest.

## Structured-output compatibility

`body_md` remains supported: HeadCleaner creates a deterministic compatibility
element for legacy plugins. New plugins may return `elements` using only the
supported kinds: `heading`, `paragraph`, `list`, `table`, `image`, `code`,
`quote`, `attachment_ref`, and `page_break`. Element attributes must be
JSON-safe, source locations use nullable `page`/`start`/`end`, and a malformed
element fails that source with `INVALID_ELEMENT` rather than corrupting another
file's run.

Plugins that expose structured tables should return `tabular_assets` only when
the underlying cells/metadata are available faithfully. Do not invent formulas,
merged ranges, or source locations. Attachment payloads must use logical source
URIs and must not derive filesystem output paths from attachment filenames.
