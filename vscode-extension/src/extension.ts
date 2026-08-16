// VS Code extension entry point for HeadCleaner (Eng #33 stub).
//
// SKELETON: full implementation lands in v0.6 with two side panels:
//   1. Concept Explorer — tree view of every concept in the bundle
//   2. Trust Inspector — frontmatter validation against a policy file
//
// For now this just registers two commands that shell out to the CLI.

import * as vscode from "vscode";
import { execFile } from "child_process";
import { promisify } from "util";

const exec = promisify(execFile);

export function activate(context: vscode.ExtensionContext) {
  const cfg = vscode.workspace.getConfiguration("headcleaner");
  const binPath = cfg.get<string>("pythonPath", "headcleaner");

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
    })
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
      } catch (e: any) {
        vscode.window.showErrorMessage(`Attest failed: ${e.message ?? e}`);
      }
    })
  );
}

export function deactivate() {}