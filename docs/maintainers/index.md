# Maintainer documentation

This directory holds documentation for headcleaner maintainers: the people who triage issues, cut releases, respond to security reports, and make decisions about the project's direction.

Maintainer documentation is separate from contributor documentation for the same reason user documentation is separate: the audience has different needs. A contributor wants to add a feature; a maintainer wants to keep the project healthy.

## The pages

[Support runbook](support-runbook.md) covers the common categories of user reports and the diagnostic steps for each.

[Incident and security runbook](incident-and-security.md) covers security incidents and severe bugs: how to receive a report, how to triage, how to fix, how to communicate.

[Versioning and compatibility](versioning-and-compatibility.md) documents semantic versioning, the public surface, schema versioning, the deprecation policy, and the compatibility matrix.

[Documentation style guide](documentation-style-guide.md) defines the writing conventions for headcleaner's documentation: the two-audience split, the voice discipline, and the rule for which docs must change when a feature is added.

[Architecture decision records](adr/) capture significant design decisions. Each ADR is immutable once accepted; superseded ADRs point at their replacements.

## What maintainers do not do

Maintainers do not unilaterally decide product direction. Major changes require consultation with the user community, typically through an issue thread or a discussion in the project's communication channels. The maintainer's role is to facilitate the decision, not to make it.

Maintainers do not release without explicit authorization. Releases are deliberate acts that affect downstream consumers; the [versioning and compatibility](versioning-and-compatibility.md) page documents the process.

## How to become a maintainer

The project does not have a formal maintainer-onboarding process. New maintainers are typically existing contributors who have demonstrated sustained, high-quality contributions across multiple phases. The transition is initiated by an existing maintainer and confirmed by the rest of the team.

If you are interested in becoming a maintainer, the best path is to keep contributing. Substantial, well-reviewed contributions are the qualification.

## Where to read next

The [documentation style guide](documentation-style-guide.md) is the writing reference for all maintainer-facing docs. The [incident and security runbook](incident-and-security.md) is the right starting point during a security incident. The [versioning and compatibility](versioning-and-compatibility.md) page is the right reference when cutting a release.