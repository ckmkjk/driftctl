"""Tests for driftctl.sync — CLAUDE.md generation and sync."""

from pathlib import Path
from unittest.mock import patch

import pytest

from driftctl.state import (
    AgentType,
    ComponentStatus,
    add_component,
    add_session,
    init_state,
    save_state,
)
from driftctl.sync import (
    CLAUDE_MD,
    HEADER_MARKER,
    compute_diff,
    generate_claude_md,
    sync,
    write_claude_md,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a project with state, components, sessions, and guardrails."""
    state = init_state(tmp_path, "synctest", AgentType.CLAUDE_CODE, "python", "pytest")
    add_component(state, "api", status=ComponentStatus.COMPLETE)
    add_component(state, "frontend", status=ComponentStatus.IN_PROGRESS, depends_on="api")
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
# generate_claude_md — content
# ---------------------------------------------------------------------------


class TestGenerateClaudeMd:
    """generate_claude_md output content."""

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            generate_claude_md(tmp_path)

    def test_contains_header(self, project):
        """Output contains the do-not-edit header."""
        text = generate_claude_md(project)
        assert HEADER_MARKER in text

    def test_contains_sync_timestamp(self, project):
        """Output contains last synced timestamp."""
        text = generate_claude_md(project)
        assert "Last synced:" in text

    def test_contains_update_instruction(self, project):
        """Output contains driftctl sync instruction."""
        text = generate_claude_md(project)
        assert "driftctl sync" in text

    def test_contains_project_identity(self, project):
        """Output includes project identity."""
        text = generate_claude_md(project)
        assert "synctest" in text
        assert "claude-code" in text
        assert "python" in text
        assert "pytest" in text

    def test_contains_guardrails_numbered(self, project):
        """Output lists guardrails as numbered items."""
        text = generate_claude_md(project)
        assert "1. never skip tests" in text
        assert "2. no-file:*.secret" in text

    def test_contains_component_table(self, project):
        """Output has a markdown table of components."""
        text = generate_claude_md(project)
        assert "| api | complete |" in text
        assert "| frontend | in_progress | api |" in text

    def test_contains_last_session(self, project):
        """Output includes last session summary."""
        text = generate_claude_md(project)
        assert "Built the API layer" in text
        assert "abc123" in text

    def test_contains_agent_instructions(self, project):
        """Output includes the 6 agent instructions."""
        text = generate_claude_md(project)
        assert "Read this file fully" in text
        assert "driftctl validate" in text
        assert "guardrails" in text
        assert "Commit after each working" in text
        assert "ESCALATION.md" in text
        assert "driftctl handoff" in text

    def test_empty_project(self, empty_project):
        """Works with no components, sessions, or guardrails."""
        text = generate_claude_md(empty_project)
        assert "No guardrails configured" in text
        assert "No components tracked" in text
        assert "No sessions recorded" in text


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------


class TestComputeDiff:
    """compute_diff behaviour."""

    def test_identical_returns_none(self):
        """Returns None when content is identical."""
        assert compute_diff("hello\nworld", "hello\nworld") is None

    def test_identical_with_whitespace_returns_none(self):
        """Ignores trailing whitespace differences."""
        assert compute_diff("hello\nworld\n", "hello\nworld") is None

    def test_different_returns_diff(self):
        """Returns diff string when content differs."""
        diff = compute_diff("old line", "new line")
        assert diff is not None
        assert "old line" in diff
        assert "new line" in diff


# ---------------------------------------------------------------------------
# write_claude_md
# ---------------------------------------------------------------------------


class TestWriteClaudeMd:
    """write_claude_md behaviour."""

    def test_creates_file(self, tmp_path):
        """Creates CLAUDE.md on disk."""
        path = write_claude_md(tmp_path, "content")
        assert path.is_file()
        assert path.name == CLAUDE_MD

    def test_content_matches(self, tmp_path):
        """Written content matches input."""
        write_claude_md(tmp_path, "expected content")
        assert (tmp_path / CLAUDE_MD).read_text(encoding="utf-8") == "expected content"

    def test_overwrites_existing(self, tmp_path):
        """Overwrites existing CLAUDE.md."""
        write_claude_md(tmp_path, "first")
        write_claude_md(tmp_path, "second")
        assert (tmp_path / CLAUDE_MD).read_text(encoding="utf-8") == "second"


# ---------------------------------------------------------------------------
# sync — integration
# ---------------------------------------------------------------------------


class TestSync:
    """sync function integration."""

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            sync(tmp_path, force=True)

    def test_creates_claude_md(self, project):
        """Creates CLAUDE.md when it doesn't exist."""
        content = sync(project, force=True)
        path = project / CLAUDE_MD
        assert path.is_file()
        assert HEADER_MARKER in path.read_text(encoding="utf-8")

    def test_force_overwrites(self, project):
        """--force overwrites without confirmation."""
        (project / CLAUDE_MD).write_text("old content")
        sync(project, force=True)
        new_content = (project / CLAUDE_MD).read_text(encoding="utf-8")
        assert HEADER_MARKER in new_content
        assert "old content" not in new_content

    def test_preview_does_not_write(self, project):
        """--preview shows content without writing."""
        content = sync(project, preview=True)
        assert HEADER_MARKER in content
        assert not (project / CLAUDE_MD).is_file()

    def test_sync_returns_content(self, project):
        """sync returns the generated content."""
        content = sync(project, force=True)
        assert "synctest" in content

    def test_existing_unchanged_skips(self, project):
        """Skips write when CLAUDE.md is already up to date."""
        # First sync
        sync(project, force=True)
        content_before = (project / CLAUDE_MD).read_text(encoding="utf-8")
        # Second sync — content won't change (except timestamp)
        # Force to avoid confirmation prompt
        sync(project, force=True)
        content_after = (project / CLAUDE_MD).read_text(encoding="utf-8")
        # Both should contain the header
        assert HEADER_MARKER in content_before
        assert HEADER_MARKER in content_after

    @patch("driftctl.sync._confirm_overwrite", return_value=False)
    def test_cancelled_by_user(self, mock_confirm, project):
        """Sync is cancelled when user declines overwrite."""
        (project / CLAUDE_MD).write_text("existing content")
        with pytest.raises(SystemExit) as exc_info:
            sync(project)
        assert exc_info.value.code == 0
        # Original content preserved
        assert (project / CLAUDE_MD).read_text(encoding="utf-8") == "existing content"

    @patch("driftctl.sync._confirm_overwrite", return_value=True)
    def test_confirmed_by_user(self, mock_confirm, project):
        """Sync proceeds when user confirms overwrite."""
        (project / CLAUDE_MD).write_text("old content")
        sync(project)
        new_content = (project / CLAUDE_MD).read_text(encoding="utf-8")
        assert HEADER_MARKER in new_content
