"""Tests for driftctl kickoff — start-of-session context block generation."""

from pathlib import Path

import pytest

from driftctl.state import (
    AgentType,
    ComponentStatus,
    add_component,
    add_session,
    init_state,
    save_state,
)
from driftctl.handoff import generate_kickoff, save_kickoff, KICKOFF_FILE
from driftctl.state import STATE_DIR


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a project with state, components, sessions, and guardrails."""
    state = init_state(tmp_path, "kicktest", AgentType.CLAUDE_CODE, "python", "pytest")
    add_component(state, "api", status=ComponentStatus.COMPLETE)
    add_component(state, "frontend", status=ComponentStatus.IN_PROGRESS, depends_on="api")
    add_component(state, "docs", status=ComponentStatus.PENDING)
    add_session(state, "Built the API layer", commits=["abc123"])
    state.guardrails.append("never skip tests")
    state.guardrails.append("no-file:*.secret")
    save_state(tmp_path, state)
    return tmp_path


@pytest.fixture()
def empty_project(tmp_path):
    """Create a minimal project with no components or sessions."""
    init_state(tmp_path, "emptyproj", AgentType.OTHER, "node", "npm test")
    return tmp_path


# ---------------------------------------------------------------------------
# generate_kickoff — content
# ---------------------------------------------------------------------------


class TestGenerateKickoff:
    """generate_kickoff output content."""

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            generate_kickoff(tmp_path)

    def test_contains_header(self, project):
        """Output starts with SESSION KICKOFF header."""
        text = generate_kickoff(project)
        assert "# SESSION KICKOFF" in text

    def test_contains_identity(self, project):
        """Output includes project identity fields."""
        text = generate_kickoff(project)
        assert "kicktest" in text
        assert "claude-code" in text
        assert "python" in text
        assert "pytest" in text

    def test_contains_components(self, project):
        """Output lists all components with statuses."""
        text = generate_kickoff(project)
        assert "api: complete" in text
        assert "frontend: in_progress" in text
        assert "docs: pending" in text

    def test_contains_dependency(self, project):
        """Output shows component dependencies."""
        text = generate_kickoff(project)
        assert "depends on api" in text

    def test_contains_guardrails_numbered(self, project):
        """Output lists guardrails as numbered items."""
        text = generate_kickoff(project)
        assert "1. never skip tests" in text
        assert "2. no-file:*.secret" in text

    def test_contains_last_session(self, project):
        """Output includes last session summary."""
        text = generate_kickoff(project)
        assert "Built the API layer" in text
        assert "abc123" in text

    def test_contains_task_queue(self, project):
        """Output lists in-progress and pending tasks."""
        text = generate_kickoff(project)
        assert "In progress" in text
        assert "frontend" in text
        assert "Pending" in text
        assert "docs" in text

    def test_contains_instructions(self, project):
        """Output ends with agent instructions."""
        text = generate_kickoff(project)
        assert "Instructions" in text
        assert "Confirm you understand" in text

    def test_empty_project(self, empty_project):
        """Works with no components, sessions, or guardrails."""
        text = generate_kickoff(empty_project)
        assert "No components tracked" in text
        assert "No sessions recorded" in text
        assert "No guardrails configured" in text
        assert "All components complete" in text


# ---------------------------------------------------------------------------
# generate_kickoff — flags
# ---------------------------------------------------------------------------


class TestKickoffFlags:
    """generate_kickoff optional parameters."""

    def test_component_filter(self, project):
        """--component filters to a single component."""
        text = generate_kickoff(project, component="api")
        assert "api: complete" in text
        assert "frontend" not in text
        assert "docs" not in text

    def test_component_not_found(self, project):
        """--component raises ValueError for unknown component."""
        with pytest.raises(ValueError, match="not found"):
            generate_kickoff(project, component="nonexistent")

    def test_no_history(self, project):
        """--no-history excludes session section."""
        text = generate_kickoff(project, include_history=False)
        assert "Last Session" not in text
        assert "Built the API layer" not in text

    def test_with_history(self, project):
        """History is included by default."""
        text = generate_kickoff(project, include_history=True)
        assert "Last Session" in text


# ---------------------------------------------------------------------------
# save_kickoff
# ---------------------------------------------------------------------------


class TestSaveKickoff:
    """save_kickoff writes to .driftctl/kickoff_latest.md."""

    def test_creates_file(self, project):
        """Kickoff file is created on disk."""
        text = generate_kickoff(project)
        path = save_kickoff(project, text)
        assert path.is_file()
        assert path.name == KICKOFF_FILE

    def test_content_matches(self, project):
        """Written content matches the generated text."""
        text = generate_kickoff(project)
        path = save_kickoff(project, text)
        assert path.read_text(encoding="utf-8") == text

    def test_overwrites_existing(self, project):
        """Saving again overwrites the previous file."""
        save_kickoff(project, "first")
        path = save_kickoff(project, "second")
        assert path.read_text(encoding="utf-8") == "second"

    def test_creates_directory(self, tmp_path):
        """Creates .driftctl directory if it doesn't exist."""
        path = save_kickoff(tmp_path, "content")
        assert (tmp_path / STATE_DIR).is_dir()
