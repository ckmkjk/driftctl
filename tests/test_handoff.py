"""Tests for driftctl.handoff — structured handoff prompt generation."""

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
from driftctl.handoff import generate_handoff


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a minimal project with state file."""
    init_state(tmp_path, "handofftest", AgentType.CLAUDE_CODE, "python", "pytest")
    return tmp_path


# ---------------------------------------------------------------------------
# generate_handoff
# ---------------------------------------------------------------------------


class TestGenerateHandoff:
    """generate_handoff output content."""

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            generate_handoff(tmp_path)

    def test_contains_header(self, project):
        """Output starts with PROJECT HANDOFF header."""
        text = generate_handoff(project)
        assert "# PROJECT HANDOFF" in text

    def test_contains_identity(self, project):
        """Output includes project identity fields."""
        text = generate_handoff(project)
        assert "handofftest" in text
        assert "claude-code" in text
        assert "python" in text
        assert "pytest" in text

    def test_no_components(self, project):
        """Output mentions no components when none exist."""
        text = generate_handoff(project)
        assert "No components tracked" in text

    def test_with_components(self, project):
        """Output lists components with their status."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        add_component(state, "api", status=ComponentStatus.COMPLETE)
        add_component(state, "frontend", status=ComponentStatus.PENDING, depends_on="api")
        save_state(project, state)

        text = generate_handoff(project)
        assert "api: complete" in text
        assert "frontend: pending" in text
        assert "depends on api" in text

    def test_no_sessions(self, project):
        """Output mentions no sessions when none exist."""
        text = generate_handoff(project)
        assert "No sessions recorded" in text

    def test_with_sessions(self, project):
        """Output lists recent sessions."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        add_session(state, "Built state engine", commits=["abc123"])
        save_state(project, state)

        text = generate_handoff(project)
        assert "Built state engine" in text
        assert "abc123" in text

    def test_sessions_limited_to_3(self, project):
        """Only the last 3 sessions are shown."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        for i in range(5):
            add_session(state, f"Session {i}")
        save_state(project, state)

        text = generate_handoff(project)
        assert "Session 0" not in text
        assert "Session 1" not in text
        assert "Session 2" in text
        assert "Session 3" in text
        assert "Session 4" in text

    def test_no_guardrails(self, project):
        """Output mentions no guardrails when none exist."""
        text = generate_handoff(project)
        assert "No guardrails configured" in text

    def test_with_guardrails(self, project):
        """Output lists guardrails."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        state.guardrails.append("never skip tests")
        save_state(project, state)

        text = generate_handoff(project)
        assert "never skip tests" in text

    def test_suggested_next_steps_pending(self, project):
        """Suggests starting pending components."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        add_component(state, "api", status=ComponentStatus.PENDING)
        save_state(project, state)

        text = generate_handoff(project)
        assert "Start next" in text
        assert "api" in text

    def test_suggested_next_steps_in_progress(self, project):
        """Suggests continuing in-progress components."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        add_component(state, "api", status=ComponentStatus.IN_PROGRESS)
        save_state(project, state)

        text = generate_handoff(project)
        assert "Continue work on" in text

    def test_suggested_next_steps_all_complete(self, project):
        """Reports all complete when nothing is pending."""
        state = init_state(project, "proj", AgentType.CLAUDE_CODE, "python", "pytest")
        add_component(state, "api", status=ComponentStatus.COMPLETE)
        save_state(project, state)

        text = generate_handoff(project)
        assert "All components complete" in text
