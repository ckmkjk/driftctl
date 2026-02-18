"""Tests for driftctl.validator — validation checks."""

from pathlib import Path

import pytest

from driftctl.state import (
    AgentType,
    ComponentStatus,
    add_component,
    init_state,
    load_state,
    save_state,
)
from driftctl.validator import (
    ValidationResult,
    check_contracts,
    check_git,
    check_state_file,
    check_test_command,
    run_all_checks,
)


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------


class TestValidationResult:
    """ValidationResult dataclass behaviour."""

    def test_ok_when_no_failures(self):
        """Result is ok when failed list is empty."""
        r = ValidationResult(passed=["a", "b"])
        assert r.ok is True

    def test_not_ok_when_failures(self):
        """Result is not ok when there are failures."""
        r = ValidationResult(passed=["a"], failed=["x"])
        assert r.ok is False

    def test_empty_is_ok(self):
        """An empty result (no checks) is considered ok."""
        r = ValidationResult()
        assert r.ok is True


# ---------------------------------------------------------------------------
# check_state_file
# ---------------------------------------------------------------------------


class TestCheckStateFile:
    """check_state_file validator."""

    def test_valid_state(self, tmp_path):
        """Passes when a valid state file exists."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")
        passed, msg = check_state_file(tmp_path)
        assert passed is True

    def test_missing_state(self, tmp_path):
        """Fails when no state file exists."""
        passed, msg = check_state_file(tmp_path)
        assert passed is False
        assert "not found" in msg.lower()


# ---------------------------------------------------------------------------
# check_git
# ---------------------------------------------------------------------------


class TestCheckGit:
    """check_git validator."""

    def test_git_repo(self, tmp_path):
        """Passes when .git directory exists."""
        (tmp_path / ".git").mkdir()
        passed, msg = check_git(tmp_path)
        assert passed is True

    def test_no_git(self, tmp_path):
        """Fails when .git directory is missing."""
        passed, msg = check_git(tmp_path)
        assert passed is False


# ---------------------------------------------------------------------------
# check_test_command
# ---------------------------------------------------------------------------


class TestCheckTestCommand:
    """check_test_command validator."""

    def test_no_state_file(self, tmp_path):
        """Fails when state file is missing."""
        passed, msg = check_test_command(tmp_path)
        assert passed is False

    def test_empty_test_command(self, tmp_path):
        """Fails when test_command is empty."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "")
        passed, msg = check_test_command(tmp_path)
        assert passed is False
        assert "no test command" in msg.lower()

    def test_passing_command(self, tmp_path):
        """Passes when test command exits 0."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "python -c \"exit(0)\"")
        passed, msg = check_test_command(tmp_path)
        assert passed is True

    def test_failing_command(self, tmp_path):
        """Fails when test command exits non-zero."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "python -c \"exit(1)\"")
        passed, msg = check_test_command(tmp_path)
        assert passed is False
        assert "failed" in msg.lower()


# ---------------------------------------------------------------------------
# check_contracts
# ---------------------------------------------------------------------------


class TestCheckContracts:
    """check_contracts validator."""

    def test_no_state_file(self, tmp_path):
        """Fails when state file is missing."""
        passed, msg = check_contracts(tmp_path)
        assert passed is False

    def test_no_contracts(self, tmp_path):
        """Passes when no components have contracts."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")
        passed, msg = check_contracts(tmp_path)
        assert passed is True
        assert "no contracts" in msg.lower()

    def test_valid_contract(self, tmp_path):
        """Passes when contract hash matches the file."""
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object"}')

        state = init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema_file))
        save_state(tmp_path, state)

        passed, msg = check_contracts(tmp_path)
        assert passed is True
        assert "1 contract" in msg.lower()

    def test_drifted_contract(self, tmp_path):
        """Fails when file content changes after hash was recorded."""
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object"}')

        state = init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema_file))
        save_state(tmp_path, state)

        # Modify the schema file after saving
        schema_file.write_text('{"type": "array"}')

        passed, msg = check_contracts(tmp_path)
        assert passed is False
        assert "drift" in msg.lower()

    def test_missing_schema_file(self, tmp_path):
        """Fails when schema file is deleted after hash was recorded."""
        schema_file = tmp_path / "schema.json"
        schema_file.write_text('{"type": "object"}')

        state = init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema_file))
        save_state(tmp_path, state)

        # Delete the schema file
        schema_file.unlink()

        passed, msg = check_contracts(tmp_path)
        assert passed is False
        assert "missing" in msg.lower()


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------


class TestRunAllChecks:
    """run_all_checks integration."""

    def test_all_pass(self, tmp_path):
        """All checks pass with a proper setup (tests skipped)."""
        (tmp_path / ".git").mkdir()
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")

        result = run_all_checks(tmp_path, run_tests=False)
        assert result.ok is True
        assert len(result.passed) >= 2  # state + git + contracts

    def test_missing_git_fails(self, tmp_path):
        """Fails when git is missing."""
        init_state(tmp_path, "proj", AgentType.OTHER, "python", "pytest")

        result = run_all_checks(tmp_path, run_tests=False)
        assert result.ok is False
        assert any("git" in msg.lower() for msg in result.failed)

    def test_no_state_fails(self, tmp_path):
        """Fails when state file is missing."""
        (tmp_path / ".git").mkdir()

        result = run_all_checks(tmp_path, run_tests=False)
        assert result.ok is False
