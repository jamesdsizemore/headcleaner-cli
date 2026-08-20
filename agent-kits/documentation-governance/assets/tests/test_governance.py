#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
VERIFY = KIT / "assets/scripts/verify_docs.py"
BOOTSTRAP = KIT / "assets/scripts/bootstrap.py"
RECORDS = ("BACKLOG.md", "ISSUES.md", "MEMORY.md", "DEVELOPMENT_HISTORY.md", "DEPENDENCIES.md", "PINS.md", "AGENTS.md", "CLAUDE.md")


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=False)


def complete_project(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "README.md").write_text("# Root\n\n[Guide](docs/guide.md#hello-world)\n", encoding="utf-8")
    (root / "docs/guide.md").write_text("# Hello world\n", encoding="utf-8")
    for record in RECORDS:
        (root / record).write_text(f"# {record}\n", encoding="utf-8")
    audit = root / "docs/development/phase-audits/phase-1.json"
    audit.parent.mkdir(parents=True)
    audit.write_text(json.dumps({"schema_version": 1, "phase": "phase-1", "status": "complete", "documents": [{"path": "README.md", "disposition": "reviewed", "evidence": "Reviewed root navigation."}, {"path": "docs/guide.md", "disposition": "reviewed", "evidence": "Reviewed guide contract."}]}, indent=2), encoding="utf-8")


class DocumentationGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_complete_phase_validates_links_records_and_audit(self) -> None:
        complete_project(self.root)
        result = run(str(VERIFY), "--root", str(self.root), "--phase", "phase-1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ACTIVE_DOCS=2", result.stdout)
        self.assertIn("PHASE_AUDIT=phase-1: complete", result.stdout)

    def test_bad_anchor_and_missing_audit_evidence_fail(self) -> None:
        complete_project(self.root)
        (self.root / "README.md").write_text("# Root\n\n[Broken](docs/guide.md#missing)\n", encoding="utf-8")
        payload = json.loads((self.root / "docs/development/phase-audits/phase-1.json").read_text(encoding="utf-8"))
        payload["documents"][0]["evidence"] = ""
        (self.root / "docs/development/phase-audits/phase-1.json").write_text(json.dumps(payload), encoding="utf-8")
        result = run(str(VERIFY), "--root", str(self.root), "--phase", "phase-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing anchor", result.stderr)
        self.assertIn("lacks concrete evidence", result.stderr)

    def test_bootstrap_is_additive_and_creates_in_progress_audit(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git required")
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        (self.root / "README.md").write_text("# Example\n", encoding="utf-8")
        result = run(str(BOOTSTRAP), str(self.root), "--phase", "release-1", "--install-hook")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / ".githooks/pre-commit").is_file())
        audit = json.loads((self.root / "docs/development/phase-audits/release-1.json").read_text(encoding="utf-8"))
        self.assertEqual(audit["status"], "in_progress")
        self.assertIn(".plans/", (self.root / ".gitignore").read_text(encoding="utf-8"))
        self.assertEqual(subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=self.root, text=True, capture_output=True, check=True).stdout.strip(), ".githooks")
        audit["status"] = "complete"
        for entry in audit["documents"]:
            entry["disposition"] = "reviewed"
            entry["evidence"] = "Reviewed bootstrap output."
        audit_path = self.root / "docs/development/phase-audits/release-1.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        subprocess.run(["git", "add", "DEVELOPMENT_HISTORY.md", "docs/development/phase-audits/release-1.json"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Governance test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "governance-test@example.invalid"], cwd=self.root, check=True)
        commit = subprocess.run(["git", "commit", "-m", "test: documentation governance hook"], cwd=self.root, text=True, capture_output=True, check=False)
        self.assertEqual(commit.returncode, 0, commit.stderr)

    def test_bootstrap_refuses_to_replace_existing_agent_instructions(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git required")
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        (self.root / "README.md").write_text("# Example\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Existing agents\n", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("# Existing Claude\n", encoding="utf-8")
        result = run(str(BOOTSTRAP), str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "# Existing agents\n")
        self.assertEqual((self.root / "CLAUDE.md").read_text(encoding="utf-8"), "# Existing Claude\n")


if __name__ == "__main__":
    unittest.main()
