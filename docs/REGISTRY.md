# Bundle Registry (v0.13.0)

The MCP server can reference bundles by friendly `@slug` aliases instead of
absolute paths.

## Quick start

```python
# Register a bundle under a slug
okf_registry_add(slug="docs", bundle_path="C:/Users/me/Documents/okf")

# Now reference it from any tool
okf_search(term="readme", bundle="docs")
okf_get_concept("@docs/readme")
okf_search(term="shared", all_bundles=True)  # search every loaded bundle
```

## File format

Default: `~/.config/headcleaner/registry.toml`. Override with
`$HEADCLEANER_REGISTRY`.

```toml
[bundles]
docs = "C:/Users/me/Documents/okf"
archive = "/mnt/old-archive"
"my-org/kb" = "C:/work/kb-v2"
```

## Slug rules

- Cannot be empty, contain `@`, or contain spaces
- Path-separator characters (`/`, `\`) are allowed so `my-org/kb` works
- Lookup is exact; no fuzzy matching

## Tool reference

| Tool | Purpose |
|---|---|
| `okf_registry_list` | List all `@slug` aliases |
| `okf_registry_add(slug, bundle_path)` | Add a new alias |
| `okf_registry_remove(slug)` | Remove an alias |
| `okf_registry_resolve("@slug/concept")` | Resolve to bundle path + concept id |

## Behavior

When you reference `@slug/concept-name` in `okf_get_concept` /
`okf_context` / `okf_related` / `okf_impact`:

1. Slug is resolved via the registry file.
2. If the bundle isn't already loaded, it's auto-loaded.
3. The remaining path after `@slug/` is used as the concept target.

If the slug isn't registered, the tool returns an empty result (not an
error — registry is best-effort). Register it first via
`okf_registry_add`.
