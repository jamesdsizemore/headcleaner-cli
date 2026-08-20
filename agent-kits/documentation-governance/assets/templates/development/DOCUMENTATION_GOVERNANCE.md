# Documentation governance

Documentation is a deliverable surface. Every phase audits root `README.md` and all active `docs/**/*.md` pages; archives are historical records and are classified separately.

For each page, record exactly one evidenced decision in the phase audit: `updated`, `reviewed`, or `not-applicable`. A phase cannot be called complete until `python scripts/verify_docs.py --phase <phase>` passes.

Before every commit, update `DEVELOPMENT_HISTORY.md`, stage the current phase audit, and let `.githooks/pre-commit` validate staged evidence. The hook is installed with `sh scripts/install-git-hooks.sh`.

Never use generated boilerplate to disguise an unreviewed page. Do not place secrets or personal data in audit evidence.
