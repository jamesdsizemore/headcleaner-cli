# Reference

This is the lookup index for headcleaner's reference documentation. The pages here are organized by what you are trying to look up, not by which source module does the work. Use this index when you already know what you want to read; if you are still figuring out where to start, the [user guide index](../user-guide/index.md) is a friendlier on-ramp.

## The pages

[CLI reference](cli-reference.md) documents every command headcleaner ships, organized by what each command does for you. Each command entry covers its purpose, when to use it, the basic command form, useful options, what it checks, possible results, mutability, the optional tools it may need, and related commands.

[Result reference](result-reference.md) documents every field of `manifest.json`, `REPORT.md`, and the per-file result records. It explains the exit-code conventions and shows how to consume the JSON output programmatically.

[Configuration reference](configuration-reference.md) documents every field of the headcleaner policy file. It explains what each field does, what values it accepts, and what the default is when you do not set it.

[Engine directory](engine-directory.md) is the per-engine directory. For every engine headcleaner ships, this page explains what the engine does, who needs it, how to install it, how headcleaner decides to use it, what the user sees when the engine is missing, and how to recover from common failures.

[MCP tool reference](mcp-tool-reference.md) documents every tool the headcleaner MCP server exposes. For each tool, the page lists the parameters, the return shape, the schema version, and the safety properties.

[Serve API reference](serve-api-reference.md) documents every endpoint of the local HTTP server. The server uses the same underlying implementation as the CLI search, so the page focuses on the URL shapes, query parameters, and response shapes.

[Environment variables](environment-variables.md) documents every environment variable headcleaner reads. Most users do not need to set any of them, but the page is here when you do.

[Compatibility](compatibility.md) documents the platforms and Python versions headcleaner supports, the optional tools it knows how to detect, and the known limitations on each platform.

## Conventions used in this reference

Reference pages are lookup-shaped, not narrative. They are organized so you can scan for the section you need and read that section without reading the whole page. Lists and tables are used freely because reference content is information-dense by design.

The reference never uses red or yellow. Headcleaner's status colors are cyan, pink, and purple; the reference pages do not introduce new colors and do not change the meaning of the existing ones.

Every reference page cross-links to the related tutorial or user-guide page where appropriate, so if you arrived here because you were looking up a term you do not yet understand, the back-link will take you to the more narrative explanation.