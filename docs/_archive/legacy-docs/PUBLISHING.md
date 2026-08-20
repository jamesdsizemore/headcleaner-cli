# Publishing headcleaner to PyPI

A reference workflow for cutting a release. Adjust the project URL
(`--repository-url`) when the public GitHub repo is created.

## One-time setup

```bash
# 1. Create PyPI account and an API token
#    https://pypi.org/manage/account/token/
#    Save the token to ~/.pypirc or use a keyring.

# 2. Install publishing tools
uv tool install twine
# OR just use uv itself:
# uv publish (no install needed)
```

## Per-release workflow

```bash
# 1. Make sure tests are green
uv run pytest

# 2. Make sure the version in pyproject.toml matches the tag
grep '^version' pyproject.toml

# 3. Update CHANGELOG.md with the release notes

# 4. Commit + tag
git add CHANGELOG.md pyproject.toml
git commit -m "release: vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>"

# 5. Build
uv build

# 6. Publish to PyPI (test first!)
uv publish --repository testpypi --token "$PYPI_TEST_TOKEN" dist/*
# OR
twine upload --repository testpypi dist/*

# 7. Verify the test install
pip install --index-url https://test.pypi.org/simple/ headcleaner==X.Y.Z
headcleaner --version

# 8. Publish to the real PyPI
uv publish --token "$PYPI_TOKEN" dist/*
# OR
twine upload dist/*

# 9. Push the tag
git push origin vX.Y.Z
```

## Automated via GitHub Actions

When the project gets a public GitHub repo, replace steps 5–8 with a
workflow that runs on every tag push. Suggested `.github/workflows/publish.yml`:

```yaml
name: publish

on:
  push:
    tags: ['v*']

jobs:
  pypi:
    runs-on: ubuntu-latest
    permissions:
      id-token: write   # for PyPI trusted publishing (OIDC)
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3

      - name: Install OfficeCLI
        run: npm install -g @officecli/officecli

      - name: Run tests
        run: uv run pytest

      - name: Build
        run: uv build

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://upload.pypi.org/legacy/
```

Configure PyPI "trusted publishing" for the repo at
https://pypi.org/manage/account/publishing/ — no API token needed in
the workflow.

## Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0 → 2.0.0) — incompatible OKF format / CLI flag changes
- **MINOR** (0.1.0 → 0.2.0) — new format support, new subcommand, new OKF field
- **PATCH** (0.1.0 → 0.1.1) — bug fixes, doc updates, no API change

Until 1.0.0 we treat MINOR as breaking (anything can change).

## Post-release checklist

- [ ] PyPI shows the new version
- [ ] `pip install --upgrade headcleaner` works
- [ ] GitHub release page has the changelog excerpt
- [ ] Homebrew formula is updated (ENHANCEMENTS.md #24)
- [ ] Docker image is rebuilt (ENHANCEMENTS.md #26)
- [ ] `docs/CHANGELOG.md` is updated with the date
