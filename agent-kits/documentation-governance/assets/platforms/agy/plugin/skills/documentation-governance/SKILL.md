---
name: documentation-governance
description: Use when a repository needs exhaustive docs audit and Git enforcement.
---

Use the repository documentation-governance workflow. Before phase completion, create and complete a per-document audit with concrete evidence, then run `python scripts/verify_docs.py --phase <phase>`. Before commits, stage `DEVELOPMENT_HISTORY.md` and the active audit; never bypass `.githooks/pre-commit`.
