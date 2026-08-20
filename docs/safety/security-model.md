# Security model

This page documents headcleaner's threat model: what headcleaner is designed to defend against, what it explicitly does not defend against, and the mitigations in place for each threat.

The threat model is intentionally narrow. Headcleaner is a CLI tool that runs on your machine and reads your files. The threats it cares about are the ones that arise from that scope.

## In-scope threats

The threats headcleaner defends against are:

### Source file corruption

**Threat:** a bug in headcleaner or one of its adapters causes a write to the source folder.

**Mitigation:** headcleaner never opens a source file for writing. Every command that reads from `INPUT` writes to `OUTPUT`. The implementation enforces this through code paths that take `INPUT` as a read-only path. The behavior is tested: every test that creates a fixture source folder asserts that the source folder's contents are unchanged after the run.

### Unauthorized network calls

**Threat:** headcleaner or one of its adapters sends data to a remote endpoint without the user's knowledge.

**Mitigation:** every code path that would result in a network call is gated on `--allow-network`. The flag is per-command; passing it on one command does not affect any other. The implementation tests this with fake HTTP providers and fake Qdrant clients that assert zero calls without permission.

### Unauthorized remote uploads

**Threat:** headcleaner uploads embeddings or chunks to a remote vector database without the user's knowledge.

**Mitigation:** the Qdrant adapter is gated on `--allow-network` plus `--qdrant-endpoint`. The endpoint URL is validated before any chunk is read or embedding computed, so the permission check happens before any data is touched.

### Silent trust promotion

**Threat:** headcleaner auto-converts a file and marks it as `verified: human:reviewed`, bypassing the human review step.

**Mitigation:** headcleaner always emits `verified: human:pending` on auto-converted files. The field is set in code; no code path changes it during a run. Changing it requires a manual edit by a human reviewer.

### Archive bomb attacks

**Threat:** a malicious archive (ZIP, PST) contains a member that, when extracted, fills the disk or exhausts memory.

**Mitigation:** the attachment handler enforces per-member and total-byte limits. The default member limit is 25 MB and the default total is 100 MB. Both can be tightened in the policy file. On breach, headcleaner aborts the extraction, purges the partial staging data, and quarantines the offending member with a `QUARANTINED` diagnostic.

### Path traversal attacks

**Threat:** an archive contains a member whose path is `../../etc/passwd` or similar, and the extraction writes outside the intended directory.

**Mitigation:** the attachment handler normalizes paths and rejects any member whose resolved path escapes the staging directory. The check happens before extraction; unsafe members are quarantined.

### Symlink attacks

**Threat:** an archive contains a symlink that points outside the staging directory, and the extraction follows it.

**Mitigation:** the attachment handler rejects symlinks that escape the staging directory. The check happens before extraction.

### Encrypted member handling

**Threat:** an archive member is encrypted with a password, and headcleaner prompts for the password (potentially logging it) or extracts garbage.

**Mitigation:** headcleaner does not prompt for passwords. Encrypted members are quarantined with a clear `ENCRYPTED_MEMBER` diagnostic. The user must decrypt the archive manually before passing it to headcleaner.

### Plugin supply chain

**Threat:** a third-party plugin adapter exfiltrates data or corrupts output.

**Mitigation:** headcleaner's plugin system uses Python entry points with a documented manifest format. Plugins run in the same process as headcleaner. The risk is bounded by the trust the user places in the plugins they install; headcleaner cannot defend against a malicious plugin any more than `pip` can defend against a malicious package. The mitigation is the same as for any Python dependency: install plugins from sources you trust.

## Out-of-scope threats

The threats headcleaner explicitly does not defend against:

- **Compromise of your machine.** If an attacker has shell access to your machine, headcleaner's protections are moot.
- **Compromise of your dependencies.** If a malicious version of a transitive dependency is installed, headcleaner's protections are moot. The lockfile and the `uv lock --check` step are the mitigations here.
- **Compromise of the MCP client.** If your AI coding assistant is compromised, headcleaner's MCP server does not add any protection beyond not exposing write tools.
- **Side-channel attacks on the embedding model.** Headcleaner does not defend against information leakage through the embedding model itself; that is the model's concern.
- **Legal compliance.** Headcleaner does not promise compliance with HIPAA, GDPR, or any other regulatory framework. Use headcleaner's output as input to a compliance-aware system.

## Reporting a vulnerability

If you find a security issue — a code path that violates one of the mitigations above, or a vulnerability in any of headcleaner's dependencies — please report it privately. The project maintains a security policy; check the repository for the contact information.

## Where to read next

The [safety overview](safety-overview.md) is the single-page summary of the guarantees. The [privacy and data handling page](privacy-and-data-handling.md) explains what headcleaner does with the data you give it. The [permissions page](permissions.md) documents every flag that affects the security boundary.