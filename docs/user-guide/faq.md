# Frequently asked questions

This page answers the practical questions that come up most often. If you have a question that is not answered here, the [user troubleshooting guide](troubleshooting.md) is symptom-driven and may get you to an answer faster than reading this page end to end.

## Is headcleaner a Python application?

Yes. Headcleaner is implemented in Python and runs on Python 3.12 or 3.13. You do not need to know Python to use headcleaner, but you do need a working Python installation. The recommended way to install Python for headcleaner is via the `uv` tool, which the [installation guide](../getting-started/installation.md) covers in detail.

## Does headcleaner work on Windows?

Yes. Headcleaner supports Windows 10 and 11, macOS, and Linux. The installation steps differ slightly across platforms; the [installation guide](../getting-started/installation.md) covers each. There are a few Windows-specific behaviors worth noting: line endings in the lockfile are CRLF, the system `USERNAME` environment variable is used for the `generated` frontmatter field, and `uv` is the recommended way to install Python because the official Python installer for Windows can interact poorly with Microsoft Store Python aliases.

## Does headcleaner touch my source files?

Never. Headcleaner reads from the directory you specify as input and writes to the directory you specify as output. Your source files are not modified by any headcleaner command. The output is rebuildable: you can delete it and rerun the conversion to regenerate it byte-identically.

## Does headcleaner make network calls?

Not by default. Every network-capable feature requires an explicit flag (`--allow-network`) and explicit configuration of the destination. The local search index and the local Sentence Transformers model both work without any network access. Embedding via a remote provider, talking to a remote vector database, and any future networked integration all require you to opt in.

## How does headcleaner know if a file has been reviewed by a human?

Every auto-converted file starts with `verified: human:pending` in its frontmatter. Changing that field is a manual step that lives in your editor; headcleaner will not change it for you. This is the safety guarantee that prevents downstream systems from treating auto-converted content as if a human had checked it. The full explanation is in [Citations and trust](citations-and-trust.md).

## Can I customize what headcleaner does?

Yes. The configuration knobs are documented in the [configuration reference](../reference/configuration-reference.md). You can set policy rules that determine which sources are converted, what frontmatter fields are required, and which statuses are accepted. The configuration is read from a TOML file in the bundle's `.headcleaner/policies/` directory, or from a path you pass explicitly.

## Does headcleaner support my file format?

The list of supported formats is in the [engine directory](../reference/engine-directory.md). Each engine entry explains what the format is, what headcleaner can do with it, and which optional tools may be required. If your format is not in the list, you can add a custom adapter; the [tool and engine development guide](../developer/tool-and-engine-development.md) walks through that.

## Can headcleaner run on a schedule or in CI?

Yes. Headcleaner is a CLI tool that runs from start to finish and exits; it has no long-running state of its own beyond the files it writes. CI usage is described in the [CI overview](../integrations/ci-overview.md) and the [tutorial on CI integration](../tutorials/ci-integration.md). Headcleaner exits with documented codes that make it easy to fail a CI step on policy violations or unrecoverable errors.

## How do I get help if I am stuck?

The [user troubleshooting guide](troubleshooting.md) is symptom-driven. The [configuration reference](../reference/configuration-reference.md) and the [result reference](../reference/result-reference.md) are complete field-by-field references. If you have found a bug or want to request a feature, open an issue in the project's issue tracker with the smallest possible reproduction and the output of `headcleaner --version`.

## What if I have a question that is not here?

Read the [glossary](../getting-started/glossary.md) for unfamiliar terms. Search the [user guide](index.md) for the area of headcleaner you are working with. If you cannot find the answer, open an issue and include a clear description of what you tried, what you expected, and what happened.