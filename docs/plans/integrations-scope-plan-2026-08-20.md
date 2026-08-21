# Integration scope plan (research deliverable)

> Phase-status: **research only** — not an implementation phase.
> Artifact: [`docs/integrations/integrations-scope-plan.md`](../integrations/integrations-scope-plan.md)
> Raw evidence: `docs/integrations/research/` (one `.meta.json` / `.readme.md` / `.tree.txt` per repo)

This plan covers 21 candidate third-party repos for headcleaner integration.
Nothing here is implemented. No source file changed. The active phase
remains Phase 2 (documentation governance).

## Headline verdicts

- **Tier A (strong candidate, next-phase material):**
  1. `scaccogatto/okf-skills` (★324, MIT, OKF v0.2 native) — vendor validator + viz
  2. `rvben/rumdl` (★1,441, MIT, Rust) — optional Markdown-body lint engine
  3. `NanoNets/docstrange` (★1,528, MIT, model-based) — opt-in hard-case adapter

- **Tier B (watchlist):** `basnijholt/agent-cli`, `messkan/rag-chunk`,
  `parsehawk/parsehawk`, `thombashi/pytablewriter`, `harshankur/officeParser`,
  `coderaiser/putout`.

- **Tier C (decline-with-reason):** `charmbracelet/glow`, `daaain/claude-code-log`,
  `ZeroSumQuant/claude-conversation-extractor`, `raphaelmansuy/code2prompt`,
  `DavidWells/markdown-magic` (license unclear), `xberg-io/tree-sitter-language-pack`,
  `al1-nasir/codegraph-cli`, `christopherkarani/Wax` (Apple-only),
  `HariSekhon/DevOps-Python-tools`.

- **Tier D (reject):** `HelixDB/helix-db`, `kestra-io/kestra`,
  `johnkerl/miller`.

Full per-repo dossiers and scoring rubric are in
[`docs/integrations/integrations-scope-plan.md`](../integrations/integrations-scope-plan.md).

## Trust stance reminders (carried into integration phase if Tier A is accepted)

- Auto-conversion must keep `status: unverified`, `verified: human:pending`,
  `generated: human:<user>@<host>`.
- `NanoNets/docstrange` adapter must override `generated:` / `verified:` in
  `normalize.py` regardless of what `docstrange` emits — regression test
  required.
- Vendoring `okf-skills`'s validator is preferred over a runtime dep on the
  plugin (so headcleaner works without `claude --plugin-dir`).

## What this plan does NOT do

- Does not create a phase audit. Research deliverable only.
- Does not modify `src/`, `tests/`, `pyproject.toml`, `install.sh`,
  `install.ps1`, or any active-document page.
- Does not advance `docs/development/ACTIVE_PHASE.md` (still phase-2).
- Does not commit, push, merge, or rebase anything.

## Intake template (to use if Tier A is approved)

```
| Tier A integrations | Vendor okf-skills validator + viz; wrap rumdl as optional lint engine; opt-in docstrange adapter. | Active-doc coverage (OKF_NOTES or equivalent), integration pages, vendored-script policy, regression test for trust-field override. | intake |
```

Add this row to `BACKLOG.md` (Active table) and create the matching
`docs/development/phase-audits/<phase>.json` before any source file change.
