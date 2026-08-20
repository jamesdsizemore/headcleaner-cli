# Incident and security runbook

This page is the maintainer's reference for handling security incidents and severe bugs. It covers how to receive a security report, how to triage, how to fix, and how to communicate.

## Receiving a security report

Security reports should be received through a private channel. The project maintains a security policy; check the repository for the contact information. Do not discuss security issues in public issues until a fix is ready.

When you receive a security report:

1. Acknowledge receipt within one business day.
2. Confirm you understand the report by writing a brief summary.
3. Open a private tracker (or a security advisory) to track the fix.
4. Do not discuss the report in public until a fix is ready.

## Triage

The first step is to confirm the vulnerability reproduces. The criteria:

- Does the bug reproduce on the latest main?
- Does the bug violate one of the safety guarantees documented in the [safety overview](../safety/safety-overview.md)?
- Does the bug require attacker control of input, or can it be triggered by a normal user?

If the bug violates a safety guarantee and can be triggered by a normal user, it is a critical security issue. Treat it as such.

If the bug does not reproduce on the latest main, the report may be against a stale version. Ask the reporter to confirm the version and try again.

If the bug requires attacker control of input but is in a code path that handles attacker-controlled input (e.g. attachments, email), treat it as serious but not necessarily critical.

## Fixing

The fix process follows the same RED/GREEN cycle as any other change:

1. Write a failing test that reproduces the vulnerability.
2. Confirm the test fails for the documented reason.
3. Make the smallest change that makes the test pass.
4. Confirm the test passes.
5. Run the full test suite to confirm no regressions.

The fix should be minimal. Do not refactor; do not add features; do not change unrelated code. A security fix that introduces new behavior is a security fix that needs more review.

## Communication

For critical security issues, the disclosure process is:

1. Fix the issue and add a regression test.
2. Prepare a security advisory with the affected versions, the fix description, and a workaround.
3. Coordinate with the reporter on the disclosure timeline. Most reporters will agree to a 90-day window.
4. Release the fix and publish the advisory on the same day.
5. Update the [compatibility reference](../reference/compatibility.md) and the [safety overview](../safety/safety-overview.md) if the fix changes documented behavior.

## Severity classification

The severity classification follows the standard CVSS approach:

- **Critical:** the bug allows remote code execution, data exfiltration, or unauthorized access to user data without user interaction.
- **High:** the bug allows one of the above with user interaction (e.g. opening a malicious file).
- **Medium:** the bug allows denial of service or partial information disclosure.
- **Low:** the bug is a nuisance or a defense-in-depth gap.

The classification affects the disclosure timeline. Critical issues are disclosed faster than low-severity issues.

## Postmortem

After a critical or high-severity issue is fixed, write a postmortem. The postmortem documents:

- What happened.
- How it was discovered.
- How long it was present.
- How it was fixed.
- What we learned.

The postmortem is published alongside the advisory. The goal is to help other projects avoid the same bug, not to assign blame.

## Continuous improvement

Every security incident is an opportunity to improve. The improvements to consider:

- Add a regression test that catches the bug and any similar future bugs.
- Add a documentation note about the failure mode.
- Add a defensive check in the code path that catches the bug class.
- Review other code paths for the same pattern.

## What to read next

The [support runbook](support-runbook.md) covers non-security bug reports. The [versioning and compatibility reference](versioning-and-compatibility.md) covers how security fixes are versioned. The [safety overview](../safety/safety-overview.md) documents the safety guarantees that security incidents may violate.