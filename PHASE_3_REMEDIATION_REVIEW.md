# HeadCleaner Phase 3 remediation review

**Status:** comprehensive review handoff — uncommitted
**Review date:** 2026-08-21
**Published baseline:** `origin/main` = `e022b80b6c00a343c9522ec96b90c301ae5b2603`
**Review scope:** published Phase 3 implementation and governance claims at `e022b80`; local uncommitted changes are explicitly excluded from completion evidence.

---

## Executive conclusion

**Do not represent Phase 3 as complete.**

The repository contains a functional Phase 1–2 conversion/index/search platform and a partially implemented Phase 3 safety/governance layer. The clean Phase 3 worktree has a green test suite, but the published implementation does not satisfy several authoritative Phase 3 contract requirements. The Phase 3 documentation audit also passed structurally while making materially false claims about documentation updates.

Recommended status:

```text
Phase 3: remediation required
```

Do not use:

```text
Phase 3: complete
```

---

## Exact repository state

### Published state

| Item | Value |
|---|---|
| Published remote branch | `origin/main` |
| Published/local main SHA | `e022b80b6c00a343c9522ec96b90c301ae5b2603` |
| Active phase in published tree | `phase-3` |
| Published Phase 3 commits | `b084ea9`, `34522ff`, `d530e70`, `63e0cee`, `3287fc4`, `e022b80` |
| Dedicated Phase 3 worktree | `C:\Users\james\developer\headcleaner-cli-phase3` |
| Dedicated worktree status | clean at `e022b80` |

### Current local main worktree

The main worktree has **uncommitted recovery/documentation work**. It is not a release candidate and must not be counted as delivered.

- 22 modified tracked files.
- Approximately 588 inserted / 65 deleted lines at review time.
- New root-level `CONTEXT_BUDGET_GUARDRAILS.md` is uncommitted.
- Preserved untracked items include `.hermes/`, `.ignore`, `docs/plans/`, `docs/integrations/research/`, and `docs/integrations/integrations-scope-plan.md`.

Do not stage broad `.`. Do not delete or silently absorb the preserved untracked items.

### Test and static quality evidence

| Gate | Result | Interpretation |
|---|---|---|
| `unset PYTHONPATH && uv run --no-sync --python 3.13 pytest` | JUnit: 612 total, 0 failures, 0 errors, 10 skipped = 602 passed | Regression-green only; does not prove contract completion. |
| `pytest -W error` | exit 0 in clean worktree | Warnings are not blocking the tested paths. |
| Phase 3 `ruff check` | **38 errors** | Published Phase 3 code/tests are not lint-clean. |
| Phase 3 `ruff format --check` | **14 files would be reformatted** | Published Phase 3 code/tests are not format-clean. |
| `git diff --check` at published boundary | clean | Whitespace check only; not a contract audit. |

---

## Authoritative Phase 3 source

The authoritative requirements are in:

```text
docs/_archive/legacy-docs/master-enhancement-development-plan.md
```

Relevant contract sections:

```text
Contract 3.1 — Evidence-first review workbench
Contract 3.2 — Versioned policy packs
Contract 3.3 — Proposed PII/secret redaction derivatives
Contract 3.4 — Inspect/quarantine untrusted inputs
Contract 3.5 — Reproducible attestations and in-toto statements
Contract 3.6 — Explainable risk-based review queues
Contract 3.7 — Evidence-based readiness grades
Contract 3.8 — Public benchmark transparency artifact
```

The review below evaluates published code against those contracts—not against commit messages or green tests alone.

---

# Contract findings

## Contract 3.1 — Evidence-first review workbench

**Assessment:** partial implementation.

### Working implementation

| Requirement | Evidence |
|---|---|
| Read-only evidence projection | `src/headcleaner/review_workbench.py:40-63`, `build_packet()` reads the concept and builds `ReviewPacket` without writing. |
| Immutable packet object | `ReviewPacket` is a frozen dataclass in `src/headcleaner/review_workbench.py:20-28`. |
| JSON/HTML render | `render_packet()` at `src/headcleaner/review_workbench.py:66-77`. |
| Browse path does not mutate concept | `tests/test_review_workbench.py::test_packet_is_a_read_only_evidence_projection`. |
| Decision requires evidence refs | `tests/test_review_workbench.py::test_decision_requires_evidence_and_appends_audit_record`. |

### Contract gaps

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| `headcleaner review-workbench BUNDLE [--concept ID] [--format tui|html|json]` | CLI is `review-workbench BUNDLE CONCEPT_REF --format json|html`. | Make concept optional via `--concept`; implement or explicitly approved-remove TUI mode; retain HTML/JSON. |
| TUI capability selection and fixed pane order | No TUI implementation or terminal-capability selection. | Implement Textual view with required panes, or revise authority only with approval. |
| Workbench decision route requiring reviewer/decision/reason/evidence | Decision logic exists separately in `review.py`; no workbench CLI decision surface. | Add explicit workbench decision command or integrate existing decision lifecycle into workbench. |
| Missing preview must be labeled unavailable | Not specifically reviewed/tested. | Add fixture and regression test. |

---

## Contract 3.2 — Versioned policy packs

**Assessment:** mostly implemented core; downstream integration missing.

### Working implementation

| Requirement | Evidence |
|---|---|
| Local TOML packs | `src/headcleaner/policy_packs.py`. |
| Safe pack identifiers/path handling | `_safe_pack_path()` at `policy_packs.py:71-79`. |
| Depth-first inheritance/cycle rejection | `load_pack()` at `policy_packs.py:116-150`; inheritance test in `tests/test_policy_packs.py`. |
| Deterministic bundle traversal | `evaluate_pack()` walks sorted Markdown concepts at `policy_packs.py:173-194`. |
| Policy test CLI | `tests/test_policy_packs.py::test_policy_test_cli_uses_bundle_local_pack_and_returns_error_exit`. |

### Gaps

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| Policy packs define queue weights used by Contract 3.6 | `PolicyPack` has no `queue_weights`; `load_pack()` does not parse/serialize it. | Extend TOML schema, `PolicyPack`, parser, serialization, validation, and queue integration. |
| Conditions only documented manifest/diagnostic/readiness/redaction fields | Existing conditions are frontmatter based and include a `readiness.not_ready` check, but no generated readiness-report integration exists. | Decide data source and enforce documented data model. |
| CLI error semantics / config invalidity | Core behavior exists but should receive full CLI contract tests including invalid pack and explain paths. | Add CLI tests covering all documented exit codes. |

---

## Contract 3.3 — Proposed PII/secret redaction derivatives

**Assessment:** safe secret-redaction derivative implemented; full PII/policy contract absent.

### Working implementation

| Requirement | Evidence |
|---|---|
| Canonical concepts preserved | `write_derivative()` writes only `<bundle>/_redacted/`; `tests/test_redact.py` verifies canonical contents unchanged. |
| Persistent reports avoid raw secret | `RedactionFinding.to_dict()` contains `value_sha256`, not raw value; schema rejects `raw_value` in `tests/test_redaction_schema.py`. |
| Deterministic basic secret proposal | `propose_redactions()` walks sorted Markdown and applies `_SECRET` regex. |
| Suppression recorded | `tests/test_redact_suppression.py`. |

### Gaps

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| Regexes first, then policy-configured Presidio analyzer | Only one regex exists: `_SECRET = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")`. No Presidio dependency or integration. | Define policy config, add analyzer dependency/runtime gating, detector metadata, synthetic PII fixtures. |
| `headcleaner redact BUNDLE [--write-derivative] [--policy PACK] [--json]` | CLI exposes only `--write-derivative` and `--json`. | Implement `--policy PACK`, deterministic policy consumption, tests. |
| Overlap resolution / detector priority | Single detector only. | Implement documented longest-span/priority dedupe with tests. |
| General PII coverage | Current implementation detects a narrow `sk-` key pattern only. | Add a policy-gated PII analyzer and documented categories. |

---

## Contract 3.4 — Inspect/quarantine untrusted inputs

**Assessment:** strongest Phase 3 slice; doctor integration unproven/missing.

### Working implementation

| Requirement | Evidence |
|---|---|
| ZIP traversal detection without extraction | `inspect_file()` and `tests/test_inspect.py::test_inspection_quarantines_traversal_archive_without_extracting_members`. |
| Encryption detection | `tests/test_inspect.py::test_inspection_quarantines_encrypted_archive_without_reading_members`. |
| Macro indicator detection | `tests/test_inspect.py`. |
| Type mismatch / malformed archive | `tests/test_inspect.py`. |
| Pre-routing quarantine in sequential and parallel pipeline | `tests/test_run.py::test_run_pipeline_quarantines_hostile_top_level_archive_before_routing`. |
| CLI JSON + quarantine exit | `tests/test_inspect_cli.py::test_inspect_cli_json_quarantines_hostile_archive`. |

### Gap

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| `doctor.py` integration | `doctor.py` is not in Phase 3 diff. | Add doctor capability/inspection status or formally narrow the contract. |
| External scanner configuration hooks | Not reviewed as delivered; no scanner execution should occur in tests. | Implement explicitly configured, sanitized hook or record approved deferment. |

---

## Contract 3.5 — Reproducible attestations and in-toto statements

**Assessment:** partial implementation with critical correctness defects.

### Working implementation

| Requirement | Evidence |
|---|---|
| Canonical JSON utility | `canonical_json_bytes()` in `src/headcleaner/attest.py`. |
| RFC 9162 split-point Merkle behavior | `merkle_root()` / `_merkle_root_bytes()` plus `tests/test_attest.py`. |
| Source/output SHA set projection | `build_in_toto_statement()` at `attest.py:406-460`. |
| In-toto dependency / DSSE media type | `in-toto==3.1.0` in `pyproject.toml`; envelope uses `application/vnd.in-toto+json`. |
| Schema / library round trip | `tests/test_attestation_schema.py`. |

### Critical defects

#### Broken legacy command

Published code:

```python
# src/headcleaner/cli.py:659
from .verify import verify_attestation
```

`src/headcleaner/verify.py` does not exist.

Actual runtime command:

```bash
headcleaner verify .
```

Actual result:

```text
ModuleNotFoundError: No module named 'headcleaner.verify'
```

**Fix:** import `verify_attestation` from `.attest`; add end-to-end alias regression tests.

#### CLI drops config and lock inputs

Published CLI at `src/headcleaner/cli.py:635-638` does:

```python
statement = build_in_toto_statement(payload)
write_in_toto_statement(statement, in_toto_path)
```

It supplies neither `config` nor `lock_path`.

Result:

- `config_sha256` is always a hash of `{}`.
- `lock_sha256` is absent from CLI-generated statements.

#### Predicate lacks required engine records and timestamp

`build_in_toto_statement()` includes source/output hashes but does not include engine records or timestamp in the predicate. Those exist only in outer `attestation.json`.

#### Signature covers too little

Current signature input is only:

```python
{
  "merkle_root": root,
  "concept_count": len(concepts),
  "version": __version__,
}
```

It does not sign provenance, outputs, config hash, lock hash, engine data, schema version, or timestamp.

#### DSSE envelope remains unsigned

`build_in_toto_dsse_envelope()` creates:

```python
signatures={}
```

regardless of `--key`.

#### Source URI normalization bug

The code claims:

```text
file://inbox/foo.txt -> inbox/foo.txt
```

but treats `inbox` as a host segment and returns `foo.txt`. This can collapse source roots.

### Required remediation

1. Define one canonical signed payload.
2. Include source/output/config/lock/engine/schema/timestamp in signed scope.
3. Pass actual normalized CLI configuration and lock path.
4. Decide/sign DSSE semantics explicitly.
5. Correct `file://` source normalization.
6. Add changed-config, changed-lock, changed-engine, changed-source, and legacy-verify CLI tests.

---

## Contract 3.6 — Explainable risk-based review queues

**Assessment:** ranking exists; durable review queue contract incomplete.

### Working implementation

| Requirement | Evidence |
|---|---|
| Queue item / factor structure | `QueueItem`, `FactorSpec`, `FACTOR_REGISTRY` in `review_queue.py`. |
| Allow-listed factors | diagnostic severity, OCR fallback, sensitivity, policy errors, stale state, age. |
| Priority ordering | `queue.sort(key=lambda i: (-i.priority, i.source_sha256, i.concept_ref))`. |
| Claim race test | `tests/test_review_queue.py::test_claim_race_second_reviewer_rejected`. |
| No direct concept trust mutation | `test_queue_commands_never_change_verified_in_frontmatter`. |

### Gaps

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| Nested CLI `review queue` / `review claim` | Published top-level `review-queue` / `review-claim`; `review` is not a group. | Implement nested shape or formally revise authority. |
| Pack-defined weights | CLI advertises `--pack`, but policy packs do not carry weights. | Implement parser/data/serialization/queue use. |
| Durable queue state | `build_queue()` always emits `pending`; does not replay sidecar audit. | Load audit state and reconstruct claimed/decided/suppressed. |
| Durable decisions/suppression/removal | `decide_item()` and `suppress_item()` are in-memory only. | Add command/API and append-only audit transitions. |
| Deterministic full JSON | Factor evidence includes `_now()` timestamps. | Inject explicit run timestamp/seed or exclude volatile data from deterministic output. |

---

## Contract 3.7 — Evidence-based readiness grades

**Assessment:** safe frontmatter heuristic; required evidence/policy integration absent.

### Working implementation

| Requirement | Evidence |
|---|---|
| Read-only report | `ReadinessReport`, `build_report()`, `explain_report()`. |
| Grade enum | `blocked | needs_review | conditional | ready`. |
| Schema | `docs/schemas/readiness.schema.json`. |
| CLI | `headcleaner readiness BUNDLE [--profile NAME] [--json]`. |
| No trust mutation | `tests/test_readiness.py::test_build_report_does_not_modify_concept_frontmatter`. |
| Conservative auto-conversion behavior | `human:pending` creates a `-0.3` deduction, preventing default `ready`. |

### Gaps

| Contract requirement | Published behavior | Required remediation |
|---|---|---|
| Read manifest/diagnostic/redaction/policy/review evidence | Reads frontmatter keys only (`chunk_count`, `metrics.ocr_used`, `redaction_findings`, `policy_findings`, etc.). | Build report from generated artifacts and stable citations. |
| Policy packs consume readiness / set routes | No readiness-report call from policy code; no thresholds in packs. | Define and implement readiness policy interface. |
| Evidence citations | Generic strings such as `frontmatter.sources is missing`. | Point to stable source artifact / concept field / diagnostic IDs. |
| Profile configuration | Hard-coded Python dicts. | Define documented profiles and allow policy thresholds where contract requires. |

---

## Contract 3.8 — Public benchmark transparency

**Assessment:** local renderer exists; required CI/public artifact delivery absent.

### Working implementation

| Requirement | Evidence |
|---|---|
| Local HTML/JSON renderer | `src/headcleaner/benchmark_dashboard.py`. |
| Escaped labels / no script tags | `tests/quality/test_dashboard.py`. |
| Non-public fixture rejection | `tests/quality/test_dashboard.py`. |
| Attribution validation | `tests/quality/test_dashboard.py`. |
| Local CLI | `headcleaner benchmark-dashboard CURRENT …`. |
| Quality documentation | `docs/QUALITY.md`. |

### Missing owned surface

Required by authority:

```text
scripts/render_benchmark_dashboard.py
.github/workflows/test.yml changes
benchmark.py changes
docs/CONTRIBUTING.md changes
```

Published state:

```text
scripts/render_benchmark_dashboard.py  missing
benchmark.py                           missing
docs/CONTRIBUTING.md                   missing
CI dashboard render                    missing
CI artifact upload                     missing
```

The published workflow runs pytest only. It does not generate, upload, or fail on the dashboard artifact.

---

# Documentation and governance failures

## Published Phase 3 audit is not evidence of completion

The audit at `docs/development/phase-audits/phase-3.json` passed because `scripts/verify_docs.py` verifies only:

1. audit coverage;
2. allowed disposition strings;
3. non-empty evidence text;
4. local Markdown links.

It does not verify that an `updated` document changed or contains phase content. It does not validate CLI docs against Click registration, claimed tests against test files, or evidence strings against code/tests.

## Root ledgers are stale

| File | Problem |
|---|---|
| `BACKLOG.md` | Phase 3 absent; active work says none. |
| `ISSUES.md` | Says no open issues despite release-critical defects. |
| `DEPENDENCIES.md` | Omits `in-toto==3.1.0`. |
| `DEVELOPMENT_HISTORY.md` | Contracts 3.7/3.8 commit fields say pending; final Git state claim is false; documentation status claims are stale. |
| `ACTIVE_PHASE.md` | Says `phase-3` despite invalid audit and material contract gaps. |

## Required generic audit redesign

Do not use a phase-specific hard-coded keyword script.

The generic verifier must read a per-phase, declarative contract manifest containing:

```json
{
  "phase": "phase-4",
  "contract_sources": ["docs/.../authoritative-plan.md#contract-4-1"],
  "documents": {
    "docs/reference/cli-reference.md": {
      "disposition": "updated",
      "required_terms": ["mcp", "routing profile"],
      "required_cli_commands": ["mcp", "profile"]
    }
  }
}
```

The generic verifier must:

- Read **staged Git content**, not arbitrary working-tree `rglob()` results.
- Require every `updated` doc to be changed in the staged diff.
- Require declared current-phase terms/anchors in staged content.
- Require `reviewed` entries to cite exact authoritative contract + code/test evidence.
- Require `not-applicable` entries to cite the contract scope that excludes them.
- Validate documented Click commands against actual registration.
- Validate claimed test paths exist.
- Validate claimed schema paths exist.
- Reject phase advancement when contract ledger has `gap` or unapproved `deferred` entries.

The current untracked research/planning Markdown issue should be solved by auditing the staged/tracked release tree, not by moving local files around temporarily.

---

# Remediation program

## P0 — Freeze false completion state

1. Do not commit the current local documentation/audit recovery edits blindly.
2. Create a new branch/worktree, e.g.:

```text
phase3-contract-remediation
```

3. Add repository issues for every P0/P1 item in this review.
4. Change phase status to `phase-3-remediation` or restore Phase 3 to an in-progress state.
5. Correct root ledgers before claiming any remediation milestone complete.

## P0 — Runtime and provenance fixes

1. Fix broken legacy `headcleaner verify` import.
2. Add real CLI regression tests for every advertised Phase 3 command.
3. Define one canonical attestation statement payload and sign all required provenance fields.
4. Wire actual config and lock hash values into CLI in-toto export.
5. Add engine/timestamp fields to predicate.
6. Correct `file://` source path normalization.

## P1 — Complete contract integrations

1. Implement nested review CLI or obtain explicit authority revision.
2. Add queue weights to policy packs.
3. Persist and replay queue claim/decision/suppression state.
4. Integrate readiness with manifest/diagnostics/redaction/policy/review artifacts.
5. Add policy-defined readiness thresholds.
6. Add Presidio/policy redaction path, or explicitly revise/redesign the redaction contract.
7. Build required dashboard script, CI generation, failure behavior, and artifact upload.

## P1 — Documentation remediation

Update real documentation only after code contract fixes land:

- `docs/reference/cli-reference.md`
- `docs/schemas/README.md`
- `docs/safety/permissions.md`
- `docs/safety/privacy-and-data-handling.md`
- `docs/safety/security-model.md`
- relevant `docs/user-guide/` pages
- `docs/integrations/ci-overview.md`
- `docs/integrations/scripts-and-automation.md`
- maintainers ADR/runbook pages
- `BACKLOG.md`, `ISSUES.md`, `DEPENDENCIES.md`, `PINS.md`, `DEVELOPMENT_HISTORY.md`

Every `updated` audit entry must have a real staged diff and current-phase content.

## P2 — Quality gates

Before any remediation push:

```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest

unset PYTHONPATH
uv run --no-sync --python 3.13 pytest -W error

unset PYTHONPATH
uv run --no-sync --python 3.13 ruff check src tests

unset PYTHONPATH
uv run --no-sync --python 3.13 ruff format --check src tests

uv lock --check
git diff --cached --check
```

Then run the generic staged-content documentation verifier and the per-contract acceptance ledger.

---

# Handoff instructions for continuing development outside Hermes

## Start from published code

```text
Repository: C:\Users\james\developer\headcleaner-cli
Published remote baseline: origin/main @ e022b80
```

## Preserve local artifacts

Do not delete or broadly stage:

```text
.hermes/
.ignore
docs/plans/
docs/integrations/research/
docs/integrations/integrations-scope-plan.md
```

## Do not trust

- `ACTIVE_PHASE.md = phase-3`
- `phase-3.json` completion status
- Phase 3 `updated` documentation claims
- `DEVELOPMENT_HISTORY.md` Phase 3 final summary
- Green pytest as proof that Phase 3 contract requirements are complete

## Trust as a starting point

- Clean-worktree regression test result: 602 passed, 10 skipped.
- Hostile-file inspection core behavior.
- Basic policy pack core behavior.
- Basic redaction derivative safety behavior.
- Basic Merkle/attestation primitives.
- Basic queue/readiness/dashboard local functionality.

## First remediation branch objective

Make Contract 3.5 truthful first:

1. Repair `headcleaner verify`.
2. Define complete signed payload semantics.
3. Add end-to-end CLI test coverage.
4. Update real CLI/schema/safety docs.
5. Add contract ledger evidence.
6. Run all test/lint/format/dependency/Git gates.

Only after 3.5 is accepted should later remediation slices proceed.
