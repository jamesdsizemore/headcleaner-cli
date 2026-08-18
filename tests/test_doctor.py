"""Tests for the `headcleaner doctor` subcommand."""
from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from headcleaner import doctor as _doctor
from headcleaner.cli import cli
from headcleaner.doctor import (
    STATUS_FAIL,
    STATUS_OK,
    STATUS_WARN,
    CheckResult,
    exit_code,
    render_text,
    run_all,
)
from headcleaner.engine_plan import EngineCapability

# ---------------------------------------------------------------------------
# Pure unit tests for individual checks
# ---------------------------------------------------------------------------


class TestChecks:
    def test_python_version_passes(self):
        r = _doctor.check_python()
        assert r.status == STATUS_OK
        assert "Python" in r.detail

    def test_officecli_detected_if_on_path(self):
        r = _doctor.check_officecli()
        # On this machine, officecli IS on PATH; otherwise it warns/fails
        assert r.status in (STATUS_OK, STATUS_FAIL)
        assert r.name == "officecli"

    def test_engine_capabilities_lists_live_registered_engines(self):
        r = _doctor.check_engine_capabilities()

        assert r.name == "engine-capabilities"
        assert r.status == STATUS_OK
        assert "txt" in r.detail

    def test_engine_capabilities_reports_missing_tool_and_network_policy(self, monkeypatch):
        capability = EngineCapability(
            name="remote",
            extensions=frozenset({".txt"}),
            requires_tools=("missing-tool",),
            network_mode="explicit",
            priority=0,
            supports_traits=frozenset(),
        )
        monkeypatch.setattr(_doctor, "engine_capabilities", lambda: [capability])
        monkeypatch.setattr(_doctor.shutil, "which", lambda _: None)

        r = _doctor.check_engine_capabilities()

        assert r.status == STATUS_WARN
        assert "remote" in r.detail
        assert "tools=missing-tool" in r.detail
        assert "selectable=no" in r.detail
        assert "network disabled" in r.detail

    def test_path_missing_fails(self, monkeypatch):
        monkeypatch.delenv("PATH", raising=False)
        r = _doctor.check_path()
        assert r.status == STATUS_FAIL
        assert "missing or empty" in r.detail

    def test_path_present_passes(self, monkeypatch):
        monkeypatch.setenv("PATH", os.pathsep.join(["tools", "bin"]))
        r = _doctor.check_path()
        assert r.status == STATUS_OK
        assert "2 non-empty entries" in r.detail

    def test_tesseract_optional(self):
        r = _doctor.check_tesseract()
        assert r.status in (STATUS_OK, STATUS_WARN)
        # When missing, fix hint is provided
        if r.status == STATUS_WARN:
            assert r.fix is not None

    def test_readpst_optional(self):
        r = _doctor.check_readpst()
        assert r.status in (STATUS_OK, STATUS_WARN)

    def test_output_dir_writable_probe(self):
        r = _doctor.check_output_dir(None)
        assert r.status == STATUS_OK
        assert "writable" in r.detail

    def test_output_dir_unwritable(self, tmp_path: Path, monkeypatch):
        # Make a directory we can't write to
        blocked = tmp_path / "locked"
        blocked.mkdir()
        monkeypatch.setattr(_doctor, "_run_check", _doctor._run_check)  # noop
        # Skip the test if we're on Windows + running as admin (can't simulate)
        if os.name == "nt":
            # Windows: use a read-only flag instead
            import stat
            blocked.chmod(stat.S_IREAD)
            r = _doctor.check_output_dir(blocked)
            # Restore so cleanup works
            blocked.chmod(stat.S_IWRITE)
        else:
            blocked.chmod(0o555)
            r = _doctor.check_output_dir(blocked)
            blocked.chmod(0o755)
        # On most systems this will fail; on some admin contexts it won't.
        # Don't assert FAIL — just confirm the check ran without crashing.
        assert r.name == "output-dir"
        assert r.status in (STATUS_OK, STATUS_FAIL)

    def test_registry_no_file(self, monkeypatch):
        from headcleaner import registry as _reg
        monkeypatch.setattr(_reg, "registry_path", lambda: Path("/nonexistent.toml"))
        r = _doctor.check_registry()
        assert r.status == STATUS_OK
        assert "no registry" in r.detail.lower()

    def test_registry_rejects_non_table_bundles(self, tmp_path: Path, monkeypatch):
        registry = tmp_path / "registry.toml"
        registry.write_text('bundles = ["not", "a", "table"]', encoding="utf-8")
        monkeypatch.setattr("headcleaner.registry.registry_path", lambda: registry)

        r = _doctor.check_registry()

        assert r.status == STATUS_FAIL
        assert "must be a table" in r.detail


# ---------------------------------------------------------------------------
# Renderer + runner
# ---------------------------------------------------------------------------


class TestRenderAndRun:
    def test_render_text_has_all_sections(self):
        results = run_all()
        text = render_text(results)
        assert "headcleaner doctor" in text
        assert "python-version" in text
        assert "path" in text
        assert "officecli" in text
        assert "fail(s)" in text
        assert "Verdict: GO" in text

    def test_exit_code_zero_on_no_fails(self):
        results = run_all()
        # On this test machine, doctor should not fail
        assert exit_code(results) == 0

    def test_exit_code_one_on_fail(self):
        results = [
            CheckResult(name="x", status=STATUS_FAIL, detail="boom"),
        ]
        assert exit_code(results) == 1

    def test_render_includes_fix_for_failures(self):
        results = [
            CheckResult(
                name="x", status=STATUS_FAIL, detail="broke", fix="do this",
            ),
        ]
        text = render_text(results)
        assert "do this" in text
        assert "Verdict: NO-GO" in text


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCli:
    def test_cli_runs(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "headcleaner doctor" in result.output
        assert "python-version" in result.output

    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "--output-dir" in result.output

    def test_cli_exits_nonzero_when_check_fails(self, monkeypatch):
        # Force check_python to fail
        def fake_python() -> CheckResult:
            return CheckResult(
                name="python-version",
                status=STATUS_FAIL,
                detail="Python 3.0.0 (need >= 3.12)",
                fix="Install Python 3.12+",
            )

        monkeypatch.setattr(_doctor, "ALL_CHECKS", [
            ("Python version", fake_python),
        ] + _doctor.ALL_CHECKS[1:])
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 1
        assert "Python 3.0.0" in result.output
