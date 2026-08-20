# Versioning and compatibility

This page documents how headcleaner is versioned, how breaking changes are introduced, and how downstream consumers should track compatibility.

## Semantic versioning

Headcleaner follows semantic versioning. The version is `MAJOR.MINOR.PATCH` where:

- **MAJOR** increments for breaking changes to the public surface (CLI flags, output schema, public Python API).
- **MINOR** increments for backward-compatible additions (new commands, new optional flags, new fields in the manifest).
- **PATCH** increments for backward-compatible fixes (bug fixes, performance improvements).

The version is defined in `src/headcleaner/__version__`. The CLI's `--version` flag reads from there.

## The public surface

The public surface is the set of things downstream consumers depend on. Breaking changes to any of these require a MAJOR version bump:

- The CLI command names, flag names, and flag semantics.
- The manifest schema (`schema_version`).
- The OKF v0.2 frontmatter schema (`docs/schemas/okf-frontmatter.schema.json`).
- The chunk derivative schema (`docs/schemas/chunk.schema.json`).
- The graph derivative schema (`docs/schemas/graph.schema.json`).
- The MCP tool signatures and return shapes.
- The HTTP API endpoint shapes and response envelopes.
- The Python API for the modules documented in the developer guide.

Things that are not part of the public surface can change without a MAJOR bump:

- Internal module structure (refactoring).
- Private helper functions.
- Internal data structures used only within a single module.
- Log message wording.
- Performance characteristics.

## Schema versioning

Every derivative carries a `schema_version` or equivalent version field. When a derivative's schema changes in a backward-incompatible way, the version increments and downstream tools can detect the change.

The current versions:

- Manifest: `1`
- Chunks: `1` (the `chunking_version` field)
- Graph: `1` (the `algorithm_version` field)
- Dedupe: `1` (the `algorithm_version` field)
- Claims: `1` (the `algorithm_version` field)

Adding a new optional field is backward-compatible and does not require a version bump. Removing a field or changing a field's type does.

## Deprecation policy

When a feature is deprecated, the deprecation is announced in:

- The `CHANGELOG.md` file (preserved in the archive).
- The CLI help text for the deprecated command or flag.
- A warning emitted on stderr when the deprecated feature is used.

The deprecated feature continues to work for at least one MINOR release. After that, it may be removed in a subsequent MINOR release with appropriate notice in `CHANGELOG.md`.

## Compatibility matrix

The compatibility matrix is in the [compatibility reference](../reference/compatibility.md). The summary:

- Python 3.12 and 3.13 are supported.
- Windows 10+, macOS 12+, and current Linux distributions are supported.
- The `mcp` library is pinned to `1.29.0`; `mcp 2.x` would require a separate migration task.
- The `qdrant-client` library is pinned to a specific version that is tested against the Qdrant server versions headcleaner supports.

When a dependency has a major version bump that requires migration work, headcleaner pins the new version explicitly and documents the migration in `CHANGELOG.md`.

## Release process

The release process is:

1. Cut a release branch from main.
2. Update `CHANGELOG.md` with the release notes.
3. Bump the version in `src/headcleaner/__version__`.
4. Run the full test suite on every supported platform.
6. Tag the release.
7. Publish the release artifacts (wheel and sdist).

Releases are not automatic; a maintainer explicitly authorizes each step.

## What to read next

The [compatibility reference](../reference/compatibility.md) is the platform support matrix. The [support runbook](support-runbook.md) covers bug reports. The [incident and security runbook](incident-and-security.md) covers security releases.