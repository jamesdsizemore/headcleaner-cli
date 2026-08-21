# Distribution Hardening Release Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Turn headcleaner’s currently template-only desktop/package-manager distribution materials into reproducible, verified release artifacts for Windows, macOS, and Linux, then submit the completed metadata to the appropriate external package ecosystems.

**Architecture:** Keep PyPI and GHCR as the canonical published Python/container surfaces. Add a tag-triggered binary-build workflow that produces platform-native PyInstaller archives, smoke-tests each archive on its build runner, records checksums, and attaches them to the GitHub Release. Package-manager metadata must consume only those immutable, versioned release artifacts and their generated SHA-256 digests.

**Tech Stack:** Python 3.12 + `uv`; PyInstaller; GitHub Actions; GitHub Releases; PyPI; GHCR; Homebrew Ruby formula; Winget YAML; Scoop JSON; Chocolatey nuspec/PowerShell package files.

---

## Current verified state

- `v0.14.0` is published on GitHub Releases, PyPI, and GHCR.
- The public repository is `jamesdsizemore/headcleaner-cli`.
- PyPI distribution is live as `headcleaner==0.14.0`.
- GHCR tags `ghcr.io/jamesdsizemore/headcleaner-cli:0.14.0` and `:latest` are live.
- All 44 numbered enhancements and all five bonus capabilities are shipped; this is a **distribution-hardening plan**, not a new feature backlog.
- `packaging/pyinstaller/headcleaner.spec` exists but there are no verified release binaries or binary-build CI.
- `packaging/homebrew/headcleaner.rb` and all Windows package manifests still reference the old `local/headcleaner` placeholder repository, version `0.4.0`, placeholder hashes, and non-existent binary URLs.
- `RELEASE.md` still has placeholder ownership/repository values and an outdated release order.
- GitHub currently has no open issues.

## Scope boundaries

### In scope

1. Reproducible native binary artifacts and release automation.
2. Correct, versioned Homebrew, Winget, Scoop, and Chocolatey package definitions.
3. Validation, checksums, release-documentation repair, and external submission-ready PRs.

### Out of scope unless separately approved

- New conversion engines, UI features, broad lint/format cleanup, or dashboard work.
- Source-code signing, macOS notarization, and Windows Authenticode signing without available certificates and explicit approval.
- Representing a package manager as published before its upstream PR has been merged.

## Release policy

- Use a new patch release only after the binary workflow and package metadata are implemented and verified. Select the version (`v0.14.1` or later) immediately before the release commit; do not retag `v0.14.0`.
- Use `unset PYTHONPATH` before every project `uv` command on this Windows Hermes host.
- Do not run a repository-wide Ruff autofix or reformat pass. Historical lint debt is not part of this distribution milestone.
- Build artifacts must be generated in CI for the tag being released; never hand-write checksums or reuse a previous release’s digest.

---

## Phase 1 — Establish artifact and package contracts

### Task 1: Record the distribution matrix

**Objective:** Decide exactly which artifact each external ecosystem consumes before modifying CI or manifests.

**Files:**
- Create: `docs/DISTRIBUTION.md`
- Modify: `RELEASE.md:1-121`

**Steps:**
1. Define the binary matrix:
   - Windows x64: `headcleaner-windows-x64.zip` containing `headcleaner.exe`.
   - macOS arm64 and x64: separate tarballs or universal binary only if CI verifies a universal result.
   - Linux x64: `headcleaner-linux-x64.tar.gz`.
2. Define canonical URLs as GitHub Release asset URLs for the exact version tag.
3. Set package-manager mapping:
   - Winget and Scoop consume the Windows ZIP.
   - Chocolatey consumes the Windows ZIP through `tools/chocolateyinstall.ps1`.
   - Homebrew consumes either the PyPI sdist or a source-release tarball; choose one after validating current Homebrew formula conventions.
4. Document optional engine limitations in binaries: OfficeCLI, LibreOffice, Tesseract, and `readpst` remain externally provisioned unless explicitly bundled and licensed.
5. Update `RELEASE.md` with real repository names/URLs and the actual ordering: validate → tag/push → wait for PyPI/GHCR/binaries → attach/verify release assets → submit ecosystem PRs.

**Validation:**
```bash
unset PYTHONPATH
uv run --no-sync --python 3.13 pytest -q
python -c "from pathlib import Path; assert 'jamesdsizemore/headcleaner-cli' in Path('RELEASE.md').read_text(encoding='utf-8')"
git diff --check
```

**Commit:**
```bash
git add docs/DISTRIBUTION.md RELEASE.md
git commit -m "docs: define supported distribution artifact matrix"
```

---

## Phase 2 — Make native binary builds reproducible

### Task 2: Add a PyInstaller build dependency and smoke-test helper

**Objective:** Make a local and CI binary build use the same repeatable commands.

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `scripts/build_binary.py` or `scripts/build_binary.sh` only if a small cross-platform Python helper reduces duplicated workflow commands.
- Create: `tests/test_binary_distribution.py` if testable helper logic is introduced.

**Steps:**
1. Add PyInstaller as an explicit development/build dependency; do not make it a runtime dependency.
2. Implement a minimal build helper only if needed to:
   - invoke the existing spec file;
   - normalize output names by platform/architecture;
   - archive the generated executable deterministically;
   - write a SHA-256 sidecar file.
3. Keep build logic simple enough to run on a release runner and locally.
4. Ensure compiled gettext catalogs and package data are present in the binary; add explicit data collection only if the PyInstaller spec proves incomplete.

**Validation:**
```bash
unset PYTHONPATH
uv sync --all-extras --python 3.13
uv run --no-sync --python 3.13 pytest tests/test_binary_distribution.py -q
uv run --no-sync --python 3.13 pyinstaller packaging/pyinstaller/headcleaner.spec --clean
# Run the produced executable with --help and --version on the host platform.
git diff --check
```

**Commit:**
```bash
git add pyproject.toml uv.lock packaging/pyinstaller scripts tests
git commit -m "build: make PyInstaller artifacts reproducible"
```

### Task 3: Add tag-triggered multi-platform binary CI

**Objective:** Generate and smoke-test release archives for each supported platform and attach them to the GitHub Release.

**Files:**
- Create: `.github/workflows/binaries.yml`
- Modify: `packaging/pyinstaller/headcleaner.spec` only if CI smoke tests reveal missing modules/data.

**Steps:**
1. Trigger the workflow only for `v*` tags and manual dispatch.
2. Use a matrix for `windows-latest`, `macos-latest`, and `ubuntu-latest`; emit the runner OS, architecture, and artifact name in job output.
3. On each runner:
   - install Python 3.12 and `uv`;
   - sync build dependencies;
   - run PyInstaller;
   - run the generated executable’s `--help` and `--version` commands;
   - archive the executable with a platform-specific name;
   - generate a SHA-256 sidecar;
   - upload the archive and checksum as workflow artifacts.
4. Add a release job that downloads all archives and uploads them to the release for the triggering tag. It must fail if any platform build or smoke test fails.
5. Keep GHCR/PyPI workflows separate; do not add a Docker dependency to binary builds.

**Validation:**
```bash
python -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/binaries.yml').read_text())"
git diff --check
# Push a dedicated test tag only after the local suite is green; verify all matrix jobs.
```

**Acceptance criteria:**
- Each release has downloadable Windows, macOS, and Linux binary artifacts plus SHA-256 files.
- Each artifact’s own runner executes `--help` and `--version` successfully.
- Release attachments are tagged with the exact semantic version.

**Commit:**
```bash
git add .github/workflows/binaries.yml packaging/pyinstaller
# Add exact files only; never git add .
git commit -m "ci: publish smoke-tested native binary artifacts"
```

---

## Phase 3 — Replace package-manager templates with real metadata

### Task 4: Modernize the Homebrew formula

**Objective:** Replace the placeholder formula with a formula that installs the released package from a stable, versioned source.

**Files:**
- Modify: `packaging/homebrew/headcleaner.rb`
- Modify: `docs/DISTRIBUTION.md`

**Steps:**
1. Confirm current Homebrew conventions for Python CLI formulas before editing.
2. Use the real homepage/repository: `https://github.com/jamesdsizemore/headcleaner-cli`.
3. Reference the selected immutable vNext source artifact and its generated SHA-256.
4. Avoid installing OfficeCLI globally in a Homebrew formula unless reviewed for Homebrew policy compatibility; document OfficeCLI as an optional engine setup instead.
5. Run Homebrew formula audit/test on macOS CI or a macOS runner before submitting it.

**Acceptance criteria:**
- No `local/`, `yourname`, `REPLACE_WITH_`, or v0.4.0 reference remains.
- `brew audit --strict` and `brew test` pass against the selected release artifact.

### Task 5: Produce a valid Winget manifest set

**Objective:** Create official Winget manifests for the exact Windows binary release.

**Files:**
- Replace or retire: `packaging/windows/headcleaner.yaml`
- Create: `packaging/windows/winget/<version>/` manifest files in current upstream-compatible layout.
- Modify: `docs/DISTRIBUTION.md`

**Steps:**
1. Confirm the accepted package identifier before implementation; do not assume `local.headcleaner`.
2. Use the immutable Windows ZIP URL from the GitHub Release and its CI-generated SHA-256.
3. Include accurate publisher, license, support URL, tags, nested portable executable path, and command alias.
4. Validate with the current `winget validate` tooling.
5. Prepare an upstream `winget-pkgs` PR only after validation passes.

**Acceptance criteria:**
- Version and URL match the release binary exactly.
- No placeholders or stale repository names remain.
- Validation output is recorded in release evidence.

### Task 6: Produce a valid Scoop manifest

**Objective:** Replace the template Scoop manifest with one installable from the Windows release ZIP.

**Files:**
- Modify: `packaging/windows/headcleaner.scoop.json`
- Modify: `docs/DISTRIBUTION.md`

**Steps:**
1. Set the released semantic version, real homepage, exact ZIP URL, and generated SHA-256.
2. Declare the extracted executable and command shim in the schema Scoop currently expects.
3. Validate installation in a clean Scoop environment or Windows CI worker.
4. Prepare the appropriate upstream/custom-bucket submission only after clean validation.

### Task 7: Make Chocolatey packaging complete

**Objective:** Convert the nuspec-only template into an installable Chocolatey package.

**Files:**
- Modify: `packaging/windows/headcleaner.nuspec`
- Create: `packaging/windows/tools/chocolateyinstall.ps1`
- Create: `packaging/windows/tools/chocolateyuninstall.ps1` only if required by the selected installation shape.
- Modify: `docs/DISTRIBUTION.md`

**Steps:**
1. Replace v0.4.0/local metadata with the actual project and version.
2. Download the exact GitHub Release Windows ZIP inside the install script, verify its checksum, and install the portable executable using Chocolatey-supported helpers.
3. Build the `.nupkg` and install/uninstall it in an isolated Chocolatey test environment.
4. Submit only the tested package to Chocolatey Community Packages.

**Acceptance criteria:**
- The nuspec includes no placeholders.
- Install, `headcleaner --version`, and uninstall all work from a clean Windows environment.

---

## Phase 4 — Cut and verify the distribution-hardening release

### Task 8: Release a new patch version with binary artifacts

**Objective:** Publish the first release whose distribution claims are backed by real artifacts and validated package metadata.

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/headcleaner/__init__.py`
- Modify: `docs/CHANGELOG.md`
- Modify: `RELEASE.md`
- Modify: package files from Phases 1–3

**Steps:**
1. Select the next available patch version; do not modify `v0.14.0`.
2. Add a changelog section that lists only verified distribution work.
3. Run the full suite and package build after the final code/doc edit:
   ```bash
   unset PYTHONPATH
   export PATH="/c/tmp/zsv-bin:$PATH"
   uv sync --all-extras --python 3.13
   uv run --no-sync --python 3.13 pytest -rs --no-header
   uv build
   git diff --check
   ```
4. Review explicit staged paths and commit the release.
5. Create and push an annotated tag.
6. Wait for Python test, LibreOffice, PyPI, GHCR, and binary-matrix jobs to finish successfully.
7. Verify live PyPI metadata, GHCR manifest(s), release asset checksums, and tag-to-commit parity.

**Acceptance criteria:**
- Full suite is green on the final tree.
- GitHub Release contains source/wheel plus verified native archives/checksums.
- PyPI and GHCR publish are green.
- The repository branch and annotated tag dereference to the same release commit.

---

## Phase 5 — External publication and honest completion record

### Task 9: Submit external package definitions

**Objective:** Move validated package definitions from repository collateral to their real upstream distribution channels.

**External actions:**
- Create/update the Homebrew tap or submit the formula where appropriate.
- Open a Winget PR.
- Open a Scoop PR or publish a maintained custom bucket.
- Submit the Chocolatey package.

**Steps:**
1. Before each submission, re-download the release artifact and compare its SHA-256 to the manifest/package definition.
2. Use one branch/PR/package submission per ecosystem; do not bundle unrelated documentation cleanup.
3. Record upstream PR/package URLs in `docs/DISTRIBUTION.md` once created.
4. Mark an ecosystem **published** only after its upstream merge/indexing succeeds; otherwise mark it **submitted** with the external URL.

**Acceptance criteria:**
- Every ecosystem has an auditable status: `validated`, `submitted`, or `published`.
- No document claims availability through a package manager before that manager’s install command has been verified.

---

## Risks and decisions requiring confirmation at execution time

1. **Binary signing/notarization:** unsigned artifacts can run but may prompt OS warnings. Signing requires certificates/secrets and explicit approval.
2. **Homebrew channel:** decide whether to maintain a custom tap or pursue homebrew-core; policy and maintenance expectations differ.
3. **Winget identifier/publisher identity:** confirm the exact accepted identifier before submitting.
4. **Scoop channel:** decide between the main bucket and a maintained custom bucket.
5. **Chocolatey moderation:** community publication can require package-specific review and may not be immediate.
6. **Optional engines:** native binaries should not silently imply that LibreOffice, OfficeCLI, Tesseract, or `readpst` are bundled.

## Final completion evidence

Do not call this milestone complete until the release record includes:

- Exact tag and commit SHA.
- Final local test command/result.
- GitHub Actions URLs and green job conclusions.
- GitHub Release asset names and SHA-256 values.
- PyPI release URL and version.
- GHCR image tags and digest(s).
- For Homebrew, Winget, Scoop, and Chocolatey: installed/published proof or an explicit upstream submission URL and state.
