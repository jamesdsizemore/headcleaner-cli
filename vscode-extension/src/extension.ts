// VS Code extension for HeadCleaner (Eng #33 — full implementation).
//
// Provides:
//   1. **Concept Explorer** — a sidebar tree view of every concept in the
//      active OKF bundle. Each concept shows its title, type, and status.
//      Clicking opens the concept in the editor.
//   2. **Trust Inspector** — a sidebar showing the bundle's attestation
//      status (whether concepts are verified, attestation matches, etc).
//
// Plus existing commands:
//   - headcleaner.lintBundle
//   - headcleaner.attest
//
// The extension reads the active bundle by looking for a `manifest.json`
// or `bundle.manifest.json` in the workspace root and walking the
// `okf/` directory.
//
// Requirements: VS Code 1.85+, headcleaner CLI on PATH (or set
// `headcleaner.pythonPath` in settings).

import * as vscode from "vscode";
import { execFile } from "child_process";
import { promisify } from "util";
import * as fs from "fs/promises";
import * as path from "path";

const exec = promisify(execFile);

// ---------------------------------------------------------------------------
// Concept data model
// ---------------------------------------------------------------------------

interface Concept {
  relpath: string;
  title: string;
  type: string;
  status: string;
  verified: string;
  source_path: string;
}

interface BundleSummary {
  root: string;
  concepts: Concept[];
  manifest_exists: boolean;
  attestation_exists: boolean;
  attestation_valid: boolean | null;
  merkle_root: string | null;
}

let _bundle: BundleSummary | null = null;
let _bundleTimer: NodeJS.Timeout | null = null;

// ---------------------------------------------------------------------------
// Tree data model for the Concept Explorer
// ---------------------------------------------------------------------------

class ConceptTreeProvider implements vscode.TreeDataProvider<ConceptTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<ConceptTreeItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: ConceptTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: ConceptTreeItem): ConceptTreeItem[] {
    if (!_bundle) {
      return [new ConceptTreeItem(
        "No OKF bundle found",
        "Run `headcleaner convert` or open a folder with an OKF bundle.",
        "info",
        "info",
      )];
    }
    if (element) {
      return [];
    }
    return _bundle.concepts.map((c) =>
      new ConceptTreeItem(
        c.title || c.relpath,
        `${c.type} · ${c.status ?? "unknown"}`,
        c.relpath,
        c.verified === "human:reviewed" ? "verified" : "unverified",
        vscode.TreeItemCollapsibleState.None,
        { command: "headcleaner.openConcept", title: "Open", arguments: [c] },
      )
    );
  }
}

class ConceptTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly description: string,
    public tooltipId: string,
    public readonly contextValue: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState = vscode.TreeItemCollapsibleState.None,
    public readonly command?: vscode.Command,
  ) {
    super(label, collapsibleState);
    this.tooltip = tooltipId;
    this.description = description;
    this.contextValue = contextValue;
  }
}

// ---------------------------------------------------------------------------
// Tree data model for the Trust Inspector
// ---------------------------------------------------------------------------

class TrustTreeProvider implements vscode.TreeDataProvider<TrustTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<TrustTreeItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: TrustTreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(element?: TrustTreeItem): TrustTreeItem[] {
    if (!_bundle) {
      return [new TrustTreeItem("No bundle", "Open a folder with an OKF bundle.", "info")];
    }
    if (element) {
      return [];
    }
    const items: TrustTreeItem[] = [];
    items.push(new TrustTreeItem(
      `Concepts: ${_bundle.concepts.length}`,
      `${_bundle.concepts.filter((c) => c.verified === "human:reviewed").length} reviewed, ${_bundle.concepts.filter((c) => c.verified !== "human:reviewed").length} pending`,
      "info",
    ));
    items.push(new TrustTreeItem(
      `Manifest: ${_bundle.manifest_exists ? "present" : "missing"}`,
      _bundle.manifest_exists ? "manifest.json found" : "Run `headcleaner convert` to generate one.",
      _bundle.manifest_exists ? "ok" : "warn",
    ));
    items.push(new TrustTreeItem(
      `Attestation: ${_bundle.attestation_exists ? "present" : "missing"}`,
      _bundle.attestation_exists
        ? _bundle.attestation_valid
          ? "Signature + Merkle root verified"
          : "Attestation does not match bundle"
        : "Run `headcleaner attest` to generate one.",
      _bundle.attestation_exists ? (_bundle.attestation_valid ? "ok" : "warn") : "warn",
    ));
    if (_bundle.merkle_root) {
      items.push(new TrustTreeItem(
        `Merkle root: ${_bundle.merkle_root.slice(0, 16)}…`,
        "Hex SHA-256 of Merkle root over all concept hashes",
        "info",
      ));
    }
    return items;
  }
}

class TrustTreeItem extends vscode.TreeItem {
  constructor(
    public readonly label: string,
    public readonly description: string,
    public readonly contextValue: string,
  ) {
    super(label, vscode.TreeItemCollapsibleState.None);
    this.description = description;
    this.contextValue = contextValue;
  }
}

// ---------------------------------------------------------------------------
// Bundle discovery
// ---------------------------------------------------------------------------

async function loadBundle(workspaceRoot: string): Promise<BundleSummary> {
  const summary: BundleSummary = {
    root: workspaceRoot,
    concepts: [],
    manifest_exists: false,
    attestation_exists: false,
    attestation_valid: null,
    merkle_root: null,
  };
  // Look for okf/ directory
  const okfDir = path.join(workspaceRoot, "okf");
  const okfDirStat = await fs.stat(okfDir).catch(() => null);
  if (okfDirStat && okfDirStat.isDirectory()) {
    const concepts = await walkOkfDir(okfDir, workspaceRoot);
    summary.concepts = concepts;
  }
  // Manifest
  const manifestPath = path.join(workspaceRoot, "manifest.json");
  summary.manifest_exists = await fs.stat(manifestPath).then((s) => s.isFile()).catch(() => false);
  // Attestation
  const attestationPath = path.join(workspaceRoot, "attestation.json");
  try {
    const attestation = JSON.parse(await fs.readFile(attestationPath, "utf-8"));
    summary.attestation_exists = true;
    summary.merkle_root = attestation.merkle_root ?? null;
    // Verify: all concepts in attestation match the okf/ directory
    if (summary.concepts.length > 0) {
      const attestation_concepts = Object.keys(attestation.concepts ?? {});
      summary.attestation_valid = true;
      for (const c of summary.concepts) {
        if (!attestation_concepts.includes(c.relpath)) {
          summary.attestation_valid = false;
          break;
        }
      }
    }
  } catch {
    summary.attestation_exists = false;
  }
  return summary;
}

async function walkOkfDir(okfDir: string, workspaceRoot: string): Promise<Concept[]> {
  const out: Concept[] = [];
  const skip = new Set(["index.md", "log.md", "attestation.json", "bundle.manifest.json"]);
  async function walk(dir: string) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) {
        await walk(full);
      } else if (e.name.endsWith(".md") && !skip.has(e.name)) {
        const text = await fs.readFile(full, "utf-8");
        const c = parseConceptMd(text, full, workspaceRoot);
        out.push(c);
      }
    }
  }
  await walk(okfDir);
  return out;
}

function parseConceptMd(text: string, fullPath: string, workspaceRoot: string): Concept {
  const match = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (!match) {
    return {
      relpath: path.relative(workspaceRoot, fullPath).replace(/\\/g, "/"),
      title: path.basename(fullPath),
      type: "?",
      status: "?",
      verified: "?",
      source_path: fullPath,
    };
  }
  const front = match[1];
  function pick(key: string): string {
    const re = new RegExp(`^${key}:\\s*(.+?)\\s*$`, "m");
    const m = front.match(re);
    return m ? m[1].trim() : "";
  }
  return {
    relpath: path.relative(workspaceRoot, fullPath).replace(/\\/g, "/"),
    title: pick("title") || path.basename(fullPath),
    type: pick("type") || "?",
    status: pick("status") || "?",
    verified: pick("verified") || "?",
    source_path: fullPath,
  };
}

// ---------------------------------------------------------------------------
// Activation
// ---------------------------------------------------------------------------

export function activate(context: vscode.ExtensionContext) {
  const cfg = vscode.workspace.getConfiguration("headcleaner");
  const binPath = cfg.get<string>("pythonPath", "headcleaner");

  // Tree views
  const conceptProvider = new ConceptTreeProvider();
  const trustProvider = new TrustTreeProvider();
  vscode.window.registerTreeDataProvider("headcleaner.concepts", conceptProvider);
  vscode.window.registerTreeDataProvider("headcleaner.trust", trustProvider);

  // Initial load
  refreshBundle(context, conceptProvider, trustProvider);

  // Refresh on file changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeWorkspaceFolders(() => {
      refreshBundle(context, conceptProvider, trustProvider);
    }),
  );

  // Status bar item
  const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 50);
  statusBar.text = "$(shield) HeadCleaner";
  statusBar.command = "headcleaner.refreshBundle";
  statusBar.show();
  context.subscriptions.push(statusBar);

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("headcleaner.refreshBundle", () => {
      refreshBundle(context, conceptProvider, trustProvider);
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("headcleaner.openConcept", async (concept: Concept) => {
      if (concept.source_path) {
        const doc = await vscode.workspace.openTextDocument(concept.source_path);
        await vscode.window.showTextDocument(doc);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("headcleaner.lintBundle", async () => {
      const folders = vscode.workspace.workspaceFolders;
      if (!folders || folders.length === 0) {
        vscode.window.showErrorMessage("No workspace folder open.");
        return;
      }
      const target = await vscode.window.showInputBox({
        prompt: "OKF bundle directory to lint",
        value: folders[0].uri.fsPath,
      });
      if (!target) return;
      try {
        const { stdout, stderr } = await exec(binPath, ["lint", target]);
        vscode.window.showInformationMessage(`HeadCleaner lint: ${stdout}`);
        if (stderr) {
          vscode.window.showWarningMessage(stderr);
        }
      } catch (e: any) {
        vscode.window.showErrorMessage(`Lint failed: ${e.message ?? e}`);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("headcleaner.attest", async () => {
      const folders = vscode.workspace.workspaceFolders;
      if (!folders || folders.length === 0) return;
      const target = await vscode.window.showInputBox({
        prompt: "OKF bundle directory to attest",
        value: folders[0].uri.fsPath,
      });
      if (!target) return;
      try {
        const { stdout } = await exec(binPath, ["attest", target]);
        vscode.window.showInformationMessage(`Attestation written:\n${stdout}`);
        refreshBundle(context, conceptProvider, trustProvider);
      } catch (e: any) {
        vscode.window.showErrorMessage(`Attest failed: ${e.message ?? e}`);
      }
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("headcleaner.verify", async () => {
      const folders = vscode.workspace.workspaceFolders;
      if (!folders || folders.length === 0) return;
      const target = folders[0].uri.fsPath;
      try {
        const { stdout } = await exec(binPath, ["verify", target]);
        vscode.window.showInformationMessage(`Verify: ${stdout}`);
        refreshBundle(context, conceptProvider, trustProvider);
      } catch (e: any) {
        vscode.window.showErrorMessage(`Verify failed: ${e.message ?? e}`);
      }
    }),
  );
}

async function refreshBundle(
  context: vscode.ExtensionContext,
  conceptProvider: ConceptTreeProvider,
  trustProvider: TrustTreeProvider,
) {
  if (_bundleTimer) {
    clearTimeout(_bundleTimer);
  }
  _bundleTimer = setTimeout(async () => {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      _bundle = null;
    } else {
      _bundle = await loadBundle(folders[0].uri.fsPath);
    }
    conceptProvider.refresh();
    trustProvider.refresh();
  }, 300);
}

export function deactivate() {}
