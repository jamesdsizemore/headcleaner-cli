"""Tests for the VS Code extension package + concept parser (Eng #33 full impl)."""
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
EXT_DIR = ROOT / "vscode-extension"
PKG_PATH = EXT_DIR / "package.json"
EXT_TS = EXT_DIR / "src" / "extension.ts"
README = EXT_DIR / "README.md"


def test_package_json_exists() -> None:
    """package.json is the extension manifest."""
    assert PKG_PATH.exists()


def test_package_json_is_valid_json() -> None:
    """package.json parses as JSON."""
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    assert pkg["name"] == "headcleaner"
    assert pkg["displayName"] == "HeadCleaner"
    assert pkg["version"]


def test_package_json_registers_concept_explorer_view() -> None:
    """The package.json declares the Concept Explorer view."""
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    views = pkg.get("contributes", {}).get("views", {})
    found = any(
        "headcleaner.concepts" in view_def["id"] and view_def.get("name") == "Concept Explorer"
        for view_list in views.values()
        for view_def in view_list
    )
    assert found, f"Concept Explorer view not declared: {views}"


def test_package_json_registers_trust_inspector_view() -> None:
    """The package.json declares the Trust Inspector view."""
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    views = pkg.get("contributes", {}).get("views", {})
    found = any(
        "headcleaner.trust" in view_def["id"] and view_def.get("name") == "Trust Inspector"
        for view_list in views.values()
        for view_def in view_list
    )
    assert found, f"Trust Inspector view not declared: {views}"


def test_package_json_includes_activitybar_container() -> None:
    """The extension contributes an activity-bar container so the icon shows up."""
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    containers = pkg.get("contributes", {}).get("viewsContainers", {}).get("activitybar", [])
    assert any(c.get("id") == "headcleaner-explorer" for c in containers)


def test_package_json_registers_open_concept_command() -> None:
    """The package.json declares the openConcept command."""
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    commands = [c["command"] for c in pkg["contributes"]["commands"]]
    assert "headcleaner.openConcept" in commands
    assert "headcleaner.refreshBundle" in commands
    assert "headcleaner.verify" in commands


def test_extension_ts_has_concept_tree_provider() -> None:
    """extension.ts implements ConceptTreeProvider with the tree-data API."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "class ConceptTreeProvider" in text
    assert "implements vscode.TreeDataProvider" in text
    assert "_onDidChangeTreeData" in text
    assert "getTreeItem" in text
    assert "getChildren" in text


def test_extension_ts_has_trust_tree_provider() -> None:
    """extension.ts implements TrustTreeProvider with the tree-data API."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "class TrustTreeProvider" in text
    assert "implements vscode.TreeDataProvider" in text


def test_extension_ts_registers_both_views() -> None:
    """extension.ts registers both the Concept Explorer and Trust Inspector views."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert 'registerTreeDataProvider("headcleaner.concepts"' in text
    assert 'registerTreeDataProvider("headcleaner.trust"' in text


def test_extension_ts_parses_frontmatter() -> None:
    """extension.ts implements frontmatter parsing for concepts."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "parseConceptMd" in text
    assert "verified" in text
    assert "status" in text
    assert "title" in text
    assert "type" in text


def test_extension_ts_uses_status_bar() -> None:
    """extension.ts creates a status-bar item so users see the extension is active."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "createStatusBarItem" in text
    assert "HeadCleaner" in text


def test_extension_ts_skips_index_and_log() -> None:
    """extension.ts skips index.md and log.md when building the concept tree."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "index.md" in text
    assert "log.md" in text


def test_extension_ts_handles_attestation() -> None:
    """extension.ts reads attestation.json and surfaces a Merkle root preview."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "attestation.json" in text
    assert "merkle_root" in text


def test_extension_ts_lint_bundle_command() -> None:
    """extension.ts registers the lintBundle command."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "headcleaner.lintBundle" in text
    assert "lint" in text  # CLI subcommand


def test_extension_ts_attest_command() -> None:
    """extension.ts registers the attest command."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "headcleaner.attest" in text
    assert "attest" in text


def test_extension_ts_verify_command() -> None:
    """extension.ts registers the verify command."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "headcleaner.verify" in text


def test_extension_ts_uses_workspace_folders() -> None:
    """extension.ts uses workspace folders to find the active bundle."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "workspace.workspaceFolders" in text
    assert "onDidChangeWorkspaceFolders" in text


def test_extension_ts_handles_empty_bundle() -> None:
    """extension.ts gracefully handles the case where no OKF bundle is present."""
    text = EXT_TS.read_text(encoding="utf-8")
    assert "No OKF bundle found" in text or "No bundle" in text


def test_ext_test_file_exists() -> None:
    """The TypeScript test file exists at the expected path."""
    test_path = EXT_DIR / "test" / "parse_concept.test.ts"
    assert test_path.exists()


def test_ext_test_file_runs_assertions() -> None:
    """The TypeScript test file uses real assertions, not just a placeholder."""
    text = (EXT_DIR / "test" / "parse_concept.test.ts").read_text(encoding="utf-8")
    assert "assertEq" in text
    assert "passed" in text
    assert "parseConceptMd" in text


def test_ext_icon_exists() -> None:
    """The extension icon SVG exists."""
    icon = EXT_DIR / "resources" / "headcleaner.svg"
    assert icon.exists()
    svg = icon.read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "22D3EE" in svg or "22d3ee" in svg  # brand cyan


def test_ext_readme_documents_features() -> None:
    """The extension README documents the Concept Explorer and Trust Inspector."""
    text = README.read_text(encoding="utf-8")
    assert "Concept Explorer" in text
    assert "Trust Inspector" in text
    assert "Lint" in text
    assert "Attest" in text
