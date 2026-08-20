# 0005 — Neon cyan/pink/purple palette, no red or yellow

**Status:** Accepted
**Date:** 2026-08-20
**Context:** Headcleaner's CLI and TUI use color to communicate status. Common status-color conventions map failed/error to red and warn to yellow. Headcleaner's brand mark is a lightning-bolt jar in a neon palette.

**Decision:** Headcleaner's palette is strictly neon cyan, neon pink, and neon purple. Status maps as: ok and success → neon cyan, active and running → neon pink, info → neon purple, failed → bright pink (not red), skipped and muted → grey. Yellow is forbidden.

**Consequences:**

- The palette is consistent across CLI and TUI.
- Users cannot use color alone to determine status; they must read the status word. This is intentional.
- Adding new UI strings requires following the palette; no exception.
- The brand mark (⚡) is always rendered in cyan or pink, never red or yellow.

## Supersedes

None.