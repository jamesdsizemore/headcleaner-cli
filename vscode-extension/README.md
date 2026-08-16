# HeadCleaner — VS Code Extension (Eng #33 full impl)

Browse and lint headcleaner OKF bundles in VS Code.

## Features

### Concept Explorer (sidebar)

A tree view of every concept in the active OKF bundle. Each concept shows its title, type, and status. Click a concept to open its source file.

### Trust Inspector (sidebar)

A summary of the bundle's trust state: number of concepts, how many are reviewed vs pending, manifest and attestation presence, Merkle root preview.

### Commands

- `HeadCleaner: Lint OKF Bundle` — runs `headcleaner lint <bundle-dir>` on the active workspace.
- `HeadCleaner: Attest Bundle` — runs `headcleaner attest <bundle-dir>` after prompting for a path.
- `HeadCleaner: Verify Bundle` — runs `headcleaner verify <bundle-dir>`.
- `HeadCleaner: Refresh Bundle` — re-scans the workspace and rebuilds the tree views.

## Configuration

- `headcleaner.pythonPath` — path to the headcleaner executable (default: `headcleaner`).
- `headcleaner.theme` — color theme selector (neon/light/dark/mono).

## Build

```bash
cd vscode-extension
npm install
npm run build
```

Then F5 in VS Code to launch the extension development host.
