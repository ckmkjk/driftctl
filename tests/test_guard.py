"""Tests for driftctl.guard — guardrail rule management and testing."""

from pathlib import Path

import pytest

from driftctl.state import AgentType, init_state
from driftctl.guard import (
    GuardResult,
    add_rule,
    list_rules,
    remove_rule,
    check_rules,
    _check_single_rule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a minimal project with state file."""
    init_state(tmp_path, "guardtest", AgentType.OTHER, "python", "pytest")
    return tmp_path


# ---------------------------------------------------------------------------
# GuardResult
# ---------------------------------------------------------------------------


class TestGuardResult:
    """GuardResult dataclass behaviour."""

    def test_ok_when_no_failures(self):
        """Result is ok when failed list is empty."""
        r = GuardResult(passed=["a"])
        assert r.ok is True

    def test_not_ok_when_failures(self):
        """Result is not ok when there are failures."""
        r = GuardResult(failed=["x"])
        assert r.ok is False

    def test_empty_is_ok(self):
        """An empty result is considered ok."""
        r = GuardResult()
        assert r.ok is True


# ---------------------------------------------------------------------------
# Rule management
# ---------------------------------------------------------------------------


class TestAddRule:
    """add_rule behaviour."""

    def test_adds_rule(self, project):
        """Rule is added to guardrails."""
        rules = add_rule(project, "no force push")
        assert "no force push" in rules

    def test_no_duplicates(self, project):
        """Same rule is not added twice."""
        add_rule(project, "no force push")
        rules = add_rule(project, "no force push")
        assert rules.count("no force push") == 1

    def test_strips_whitespace(self, project):
        """Leading/trailing whitespace is stripped."""
        rules = add_rule(project, "  spaces  ")
        assert "spaces" in rules

    def test_empty_rule_ignored(self, project):
        """Empty string is not added."""
        rules = add_rule(project, "")
        assert len(rules) == 0

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            add_rule(tmp_path, "rule")


class TestRemoveRule:
    """remove_rule behaviour."""

    def test_removes_rule(self, project):
        """Rule is removed from guardrails."""
        add_rule(project, "delete me")
        rules = remove_rule(project, "delete me")
        assert "delete me" not in rules

    def test_missing_rule_is_noop(self, project):
        """Removing a nonexistent rule doesn't error."""
        rules = remove_rule(project, "not there")
        assert len(rules) == 0


class TestListRules:
    """list_rules behaviour."""

    def test_empty(self, project):
        """Returns empty list when no rules."""
        assert list_rules(project) == []

    def test_returns_rules(self, project):
        """Returns all added rules."""
        add_rule(project, "rule1")
        add_rule(project, "rule2")
        rules = list_rules(project)
        assert rules == ["rule1", "rule2"]


# ---------------------------------------------------------------------------
# Rule testing — individual rules
# ---------------------------------------------------------------------------


class TestSingleRule:
    """_check_single_rule for each rule type."""

    def test_cmd_pass(self, project):
        """cmd: rule passes when command exits 0."""
        passed, msg = _check_single_rule(project, "cmd:python -c \"exit(0)\"")
        assert passed is True

    def test_cmd_fail(self, project):
        """cmd: rule fails when command exits non-zero."""
        passed, msg = _check_single_rule(project, "cmd:python -c \"exit(1)\"")
        assert passed is False

    def test_no_file_pass(self, project):
        """no-file: passes when no matching files."""
        passed, msg = _check_single_rule(project, "no-file:*.secret")
        assert passed is True

    def test_no_file_fail(self, project):
        """no-file: fails when matching files exist."""
        (project / "creds.secret").write_text("oops")
        passed, msg = _check_single_rule(project, "no-file:*.secret")
        assert passed is False

    def test_require_file_pass(self, project):
        """require-file: passes when file exists."""
        (project / "README.md").write_text("hi")
        passed, msg = _check_single_rule(project, "require-file:README.md")
        assert passed is True

    def test_require_file_fail(self, project):
        """require-file: fails when file is missing."""
        passed, msg = _check_single_rule(project, "require-file:MISSING.txt")
        assert passed is False

    def test_manual_rule(self, project):
        """Descriptive rules always pass."""
        passed, msg = _check_single_rule(project, "never skip tests")
        assert passed is True
        assert "manual" in msg.lower()


# ---------------------------------------------------------------------------
# check_rules integration
# ---------------------------------------------------------------------------


class TestTestRules:
    """check_rules runs all guardrails."""

    def test_no_rules(self, project):
        """No rules means ok."""
        result = check_rules(project)
        assert result.ok is True
        assert len(result.passed) == 0

    def test_all_pass(self, project):
        """All passing rules give ok result."""
        (project / "README.md").write_text("hi")
        add_rule(project, "require-file:README.md")
        add_rule(project, "no-file:*.secret")
        result = check_rules(project)
        assert result.ok is True
        assert len(result.passed) == 2

    def test_mixed_results(self, project):
        """Mix of passing and failing rules."""
        add_rule(project, "require-file:README.md")  # will fail
        add_rule(project, "no-file:*.secret")  # will pass
        result = check_rules(project)
        assert result.ok is False
        assert len(result.passed) == 1
        assert len(result.failed) == 1
