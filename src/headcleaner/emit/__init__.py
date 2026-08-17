"""Output emitters — turn `CanonicalDoc` into Markdown and/or OKF on disk.

The Markdown emitter writes `<name>.md` with YAML frontmatter.
The OKF emitter writes one concept per source file plus auto-generated
`index.md` files at every directory level for OKF v0.2 progressive disclosure.
See `docs/OKF_NOTES.md` for the contract these emitters follow.
"""

__all__ = ["markdown", "okf", "okf_index", "manifest"]
