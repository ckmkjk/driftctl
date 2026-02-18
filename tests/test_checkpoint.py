"""Tests for driftctl.checkpoint — state snapshot save and rollback."""

from pathlib import Path

import pytest

from driftctl.state import AgentType, add_component, init_state, load_state, save_state, ComponentStatus
from driftctl.checkpoint import (
    delete_checkpoint,
    list_checkpoints,
    rollback_checkpoint,
    save_checkpoint,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a minimal project with state file."""
    init_state(tmp_path, "cptest", AgentType.OTHER, "python", "pytest")
    return tmp_path


# ---------------------------------------------------------------------------
# save_checkpoint
# ---------------------------------------------------------------------------


class TestSaveCheckpoint:
    """save_checkpoint behaviour."""

    def test_creates_file(self, project):
        """Checkpoint file is created on disk."""
        path = save_checkpoint(project, "v1")
        assert path.is_file()
        assert path.name == "v1.yaml"

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            save_checkpoint(tmp_path, "v1")

    def test_empty_name_raises(self, project):
        """Raises ValueError for empty name."""
        with pytest.raises(ValueError):
            save_checkpoint(project, "")

    def test_path_separator_raises(self, project):
        """Raises ValueError for name with path separators."""
        with pytest.raises(ValueError):
            save_checkpoint(project, "a/b")

    def test_overwrite_existing(self, project):
        """Saving with same name overwrites."""
        save_checkpoint(project, "v1")
        # Modify state
        state = load_state(project)
        add_component(state, "new_comp")
        save_state(project, state)
        # Save again
        save_checkpoint(project, "v1")
        # Rollback and check new component is there
        rollback_checkpoint(project, "v1")
        loaded = load_state(project)
        assert "new_comp" in loaded.components


# ---------------------------------------------------------------------------
# rollback_checkpoint
# ---------------------------------------------------------------------------


class TestRollbackCheckpoint:
    """rollback_checkpoint behaviour."""

    def test_restores_state(self, project):
        """Rolling back restores the saved state."""
        save_checkpoint(project, "before")

        # Modify state
        state = load_state(project)
        state.project = "modified"
        add_component(state, "extra", status=ComponentStatus.COMPLETE)
        save_state(project, state)

        # Verify modified
        assert load_state(project).project == "modified"

        # Rollback
        rollback_checkpoint(project, "before")
        restored = load_state(project)
        assert restored.project == "cptest"
        assert "extra" not in restored.components

    def test_missing_checkpoint_raises(self, project):
        """Raises FileNotFoundError for nonexistent checkpoint."""
        with pytest.raises(FileNotFoundError):
            rollback_checkpoint(project, "nope")


# ---------------------------------------------------------------------------
# list_checkpoints
# ---------------------------------------------------------------------------


class TestListCheckpoints:
    """list_checkpoints behaviour."""

    def test_empty(self, project):
        """Returns empty list when no checkpoints."""
        assert list_checkpoints(project) == []

    def test_returns_sorted(self, project):
        """Returns checkpoint names in sorted order."""
        save_checkpoint(project, "beta")
        save_checkpoint(project, "alpha")
        save_checkpoint(project, "gamma")
        assert list_checkpoints(project) == ["alpha", "beta", "gamma"]

    def test_no_state_dir(self, tmp_path):
        """Returns empty list when .driftctl doesn't exist."""
        assert list_checkpoints(tmp_path) == []


# ---------------------------------------------------------------------------
# delete_checkpoint
# ---------------------------------------------------------------------------


class TestDeleteCheckpoint:
    """delete_checkpoint behaviour."""

    def test_deletes_existing(self, project):
        """Returns True and removes the file."""
        save_checkpoint(project, "doomed")
        assert delete_checkpoint(project, "doomed") is True
        assert "doomed" not in list_checkpoints(project)

    def test_nonexistent_returns_false(self, project):
        """Returns False when checkpoint doesn't exist."""
        assert delete_checkpoint(project, "nope") is False
