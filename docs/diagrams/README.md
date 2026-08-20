# Diagrams

This directory holds the dark-themed SVG diagrams referenced from the user-facing documentation. The developer guide uses ASCII diagrams instead; this directory exists only for the user pages.

## Palette

Every diagram in this directory uses the headcleaner brand palette:

- Background: `#0b0f1a` (near-black, low blue cast)
- Cyan accent (`stroke-cyan`, `fill-cyan`): `#22D3EE`
- Pink accent (`stroke-pink`, `fill-pink`): `#EC4899`
- Purple accent (`stroke-purple`, `fill-purple`): `#A855F7`
- Muted stroke (`stroke-muted`): `#64748b`
- Main text: `#e2e8f0`
- Muted text: `#94a3b8`

The semantics of the colors are consistent across all four diagrams:

- Cyan marks the canonical path: input, output, the trust invariants, the search index.
- Pink marks active state: the pipeline itself, the convert action, the failure-but-recoverable conditions.
- Purple marks derivatives and supporting state: the rebuildable derivatives, the hidden state directory, the bundle-internal evidence.

No diagram uses red or yellow. The palette is enforced by convention.

## The diagrams

| Diagram | Used by | What it shows |
|---|---|---|
| `overview.svg` | `README.md`, the product landing page | Source folder in, headcleaner pipeline in the middle, output folder out, four derivative cards, the search index below. |
| `pipeline.svg` | `docs/getting-started/first-run.md` | The four pipeline stages (walk, route, normalize, emit) with the trust invariant banner and the four derivative outputs. |
| `output-folder.svg` | `docs/getting-started/first-run.md`, `docs/user-guide/checking-converted-output.md` | The output folder layout: manifest, REPORT, `_md/`, `okf/`, `.headcleaner/`, with the trust-frontmatter annotation. |
| `safety-guarantees.svg` | `docs/safety/safety-overview.md` | The five safety guarantees as five cards. |

## How to add a new diagram

When you need a new diagram:

1. Choose the diagram's palette role. If it is canonical path information, use cyan. If it is active state, use pink. If it is derivative or supporting state, use purple. Most diagrams combine the three.
2. Use the existing color variables in the SVG's `<style>` block. Do not introduce inline colors.
3. Keep the composition sparse. The editorial standard is "every node earns its place; the accent color is reserved for the 1–2 things the reader should look at first."
4. Verify the diagram renders correctly at 1440×900 and 1920×1080. The `<svg viewBox>` should be sized for both.
5. Reference the diagram from the relevant docs page using the relative path from the docs root (e.g. `../diagrams/overview.svg` from a docs page, or `docs/diagrams/overview.svg` from the root README).
6. Add a row to the table above documenting what the diagram shows and where it is referenced.

## How to update an existing diagram

When you change a diagram:

1. Update the SVG file in place.
2. If the diagram's semantic content changes (not just the visual styling), update the description in the table above.
3. If the diagram is referenced from a docs page, check that the surrounding prose still describes it accurately. Update the prose if needed.
4. Do not introduce a new file with a similar name; rename the existing one and update its references.

## SVG authoring conventions

The diagrams are hand-written SVG. The conventions:

- One `<svg>` root with explicit `viewBox` and `role="img"` plus `aria-labelledby` pointing at the `<title>` element.
- One `<defs>` block with `<style>` containing the class definitions. Do not put styles inline on individual elements.
- One `<title>` element as the first child of `<svg>` for accessibility.
- A `<rect>` background covering the full viewBox with class `bg`.
- Group shapes by semantic role using `<g>` wrappers. Each `<g>` should have a comment explaining what it represents.
- Use `<line>` and `<polygon>` for arrows rather than complex path expressions; this keeps the diagrams diff-friendly.
- Use `<text>` elements with explicit positioning. Do not rely on auto-layout.

## Tools

The diagrams can be viewed in any modern browser by opening the file directly. They can be edited in any text editor. For complex diagrams that require composition tools, prefer hand-written SVG over Figma exports; the brand discipline and the editorial standard are easier to maintain in code.

The `archify` skill is available for programmatic generation of architecture diagrams. It produces self-contained HTML with inline SVG and is appropriate for new diagrams that require tooling beyond hand-writing. The existing diagrams in this directory are hand-written; new ones may use either approach, but they must follow the palette and conventions above.