# Releasing headcleaner

Step-by-step checklist for cutting a public release. The automation
handles ~90%; the rest is review.

## One-time setup

- [ ] Create the public repo (e.g., `github.com/yourname/headcleaner`)
- [ ] Push the local repo: `git remote add origin <URL>` then `git push -u origin main`
- [ ] In the GitHub repo settings → **Environments** → create `pypi` environment
- [ ] In **Settings → Actions → General → Workflow permissions**, enable "Read and write permissions"
- [ ] Register the repo on PyPI:
  - Go to https://pypi.org/manage/account/publishing/
  - Add a new pending publisher:
    - Owner: yourname
    - Repository: headcleaner
    - Workflow filename: publish.yml
    - Environment name: pypi
- [ ] (Optional) Submit the Homebrew formula: create a `homebrew-headcleaner` repo and push `packaging/homebrew/headcleaner.rb` to its `Formula/` dir

## Per-release workflow

### 1. Update version + changelog

```bash
# Bump pyproject.toml + __init__.py
$EDITOR pyproject.toml src/headcleaner/__init__.py

# Write the CHANGELOG entry under docs/CHANGELOG.md
$EDITOR docs/CHANGELOG.md
```

### 2. Run the full test suite

```bash
uv run pytest
```

Must be 100% green before tagging.

### 3. Commit + tag

```bash
git add -A
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>"
```

### 4. Push

```bash
git push origin main
git push origin vX.Y.Z
```

The push of the tag triggers `.github/workflows/publish.yml` and
`.github/workflows/docker.yml`:

- **publish.yml**: runs pytest → builds wheel → publishes to PyPI (or TestPyPI if the tag contains "test")
- **docker.yml**: builds the multi-arch Docker image and pushes to `ghcr.io/yourname/headcleaner`

### 5. Watch the Actions

https://github.com/yourname/headcleaner/actions

The publish.yml workflow needs to be approved once because the `pypi`
environment is protected. Approve it from the Actions UI.

### 6. Create the GitHub Release

Once PyPI shows the new version:

- https://github.com/yourname/headcleaner/releases/new
- Choose the tag you just pushed
- Release title: `vX.Y.Z`
- Description: copy the relevant section from `docs/CHANGELOG.md`
- Attach build artifacts (if you also produced a PyInstaller binary or Docker image, attach them here)

### 7. Smoke-test the install

```bash
# Clean machine (or venv):
pip install --upgrade headcleaner
headcleaner --version
headcleaner agents
mkdir -p /tmp/inbox && echo "hello" > /tmp/inbox/note.txt
headcleaner /tmp/inbox --format both --output /tmp/out
ls /tmp/out
```

### 8. Smoke-test the Docker image

```bash
docker run --rm -v /tmp/inbox:/inbox -v /tmp/out:/out \
    ghcr.io/yourname/headcleaner:latest \
    convert /inbox --output /out
ls /tmp/out
```

### 9. Update external packages

- [ ] Homebrew: push updated formula to `homebrew-headcleaner/Formula/headcleaner.rb`
- [ ] Winget: PR to `winget-pkgs/manifests/l/local/headcleaner/<version>/`
- [ ] Scoop: PR to `ScoopInstaller/Scoop/bucket/headcleaner.json`
- [ ] Chocolatey: push updated `.nuspec` to `chocolatey-packages/headcleaner/`

### 10. Announce (optional)

- [ ] Post on social channels
- [ ] Update the README badges if you added any
- [ ] Write a release notes blog post / changelog post

## Post-release checklist

- [ ] `pip install --upgrade headcleaner` works for end users
- [ ] `pipx install headcleaner` works
- [ ] `uv tool install headcleaner` works
- [ ] Docker image pulls and runs (`docker pull ghcr.io/yourname/headcleaner:X.Y.Z`)
- [ ] Homebrew formula builds on macOS and Linux
- [ ] GitHub release page has the changelog
- [ ] All four external package managers show the new version
