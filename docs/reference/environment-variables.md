# Environment variables

This page documents every environment variable headcleaner reads. Most users do not need to set any of these; the defaults work for the common case. The page is here for the cases where you do.

## Variables used during conversion

### `$USER` and `$USERNAME`

Headcleaner reads one of these to populate the `generated` frontmatter field on every auto-converted file. The convention is `human:<user>@<host>`.

On macOS and Linux, the variable is `$USER`. On Windows, the variable is `$USERNAME`. Headcleaner picks the one that is set on the host OS.

If you want this field to read something other than your system username — for example, a shared service identity — set the appropriate variable before running headcleaner:

```bash
# macOS / Linux
export USER=service-account
uv run --no-sync --python 3.13 headcleaner convert ./in ./out

# Windows PowerShell
$env:USERNAME = "service-account"
uv run --no-sync --python 3.13 headcleaner convert .\in .\out
```

### `$HOSTNAME`

Headcleaner reads `$HOSTNAME` (or `$COMPUTERNAME` on Windows) to populate the host portion of the `generated` frontmatter field. The default is whatever your shell reports.

If you want a specific hostname in the generated field, set the variable before running.

## Variables used by optional tools

### OfficeCLI

OfficeCLI is invoked by name. There is no environment variable to configure its location; the binary must be on `PATH`. If you have OfficeCLI installed in a non-standard location, add that location to your `PATH`.

### Tesseract

Tesseract is invoked by name. Same convention as OfficeCLI.

### LibreOffice

LibreOffice is invoked by name on macOS and Linux. On Windows, headcleaner looks for the standard LibreOffice install path under `%ProgramFiles%`. If you have installed LibreOffice to a non-standard location, set the `LIBREOFFICE_PATH` environment variable before running headcleaner.

### `readpst`

`readpst` is invoked by name. The binary must be on `PATH`.

## Variables used during embedding

### `HF_HOME`

When the local Sentence Transformers provider needs to download a model, it uses the `HF_HOME` environment variable to find the HuggingFace cache directory. Headcleaner does not download models implicitly; this variable only matters if you have explicitly asked for a model that is not already cached locally.

If you have set `HF_HOME` for another tool, headcleaner will respect it.

### Proxy variables

The HTTP embedding provider respects standard proxy variables: `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, and their lowercase variants. The provider requires `--allow-network` to be passed on the command line; the proxy variables configure how the network call is made once permission is granted.

If your environment requires a proxy for outbound HTTP, set `HTTPS_PROXY` before running headcleaner:

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
uv run --no-sync --python 3.13 headcleaner index embed BUNDLE --provider openai_compatible_http --model MODEL --allow-network
```

## Variables used by the HTTP server

The HTTP server does not read any environment variable directly. The bind host and port are passed on the command line. If you want the server to bind to a non-loopback interface, pass `--host 0.0.0.0` explicitly; the server does not check environment variables to decide whether to allow this.

## Variables used during CI runs

In CI, the most common variable to set is the GitHub Actions token (for uploading artifacts) and the `GITHUB_STEP_SUMMARY` path (for inline summaries). Neither is read by headcleaner; both are CI-side concerns documented in the [CI integration tutorial](../tutorials/ci-integration.md).

## Variables that headcleaner does NOT read

For clarity, the following variables are sometimes assumed but not used:

- `OPENAI_API_KEY` — headcleaner does not read this directly. If you want to use OpenAI-compatible embedding, pass the endpoint and key through the `--provider openai_compatible_http` configuration; headcleaner will read the key from the configuration object, not the environment.
- `QDRANT_API_KEY` — same convention. Pass through configuration.
- `HEADCLEANER_*` — headcleaner does not use any `HEADCLEANER_*` environment variables. Configuration is through policy files and command-line flags.

## Where to read next

The [configuration reference](configuration-reference.md) is the comprehensive look for of how headcleaner accepts configuration. The [installation guide](../getting-started/installation.md) is the right place to learn about setting up optional tools.