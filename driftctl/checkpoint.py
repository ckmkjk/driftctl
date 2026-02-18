"""Checkpoint module for driftctl.

Save and rollback named state snapshots so agents can recover from
bad sessions or branch experiments.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from driftctl.state import STATE_DIR, STATE_FILE, load_state, save_state

console = Console()

CHECKPOINT_DIR = "checkpoints"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _checkpoints_path(project_root: Path) -> Path:
    """Return the path to the checkpoints directory."""
    return project_root / STATE_DIR / CHECKPOINT_DIR


def _checkpoint_file(project_root: Path, name: str) -> Path:
    """Return the path to a specific named checkpoint."""
    return _checkpoints_path(project_root) / f"{name}.yaml"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_checkpoint(project_root: Path, name: str) -> Path:
    """Save the current state as a named checkpoint.

    Copies the current state.yaml to .driftctl/checkpoints/<name>.yaml.
    Overwrites if a checkpoint with the same name already exists.

    Raises FileNotFoundError if the state file does not exist.
    Raises ValueError if the name is empty or contains path separators.
    """
    name = name.strip()
    if not name:
        raise ValueError("Checkpoint name cannot be empty")
    if "/" in name or "\\" in name:
        raise ValueError("Checkpoint name cannot contain path separators")

    # Verify state file exists and is valid
    load_state(project_root)

    src = project_root / STATE_DIR / STATE_FILE
    dest = _checkpoint_file(project_root, name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dest))
    return dest


def rollback_checkpoint(project_root: Path, name: str) -> None:
    """Restore state from a named checkpoint.

    Copies .driftctl/checkpoints/<name>.yaml back to state.yaml.

    Raises FileNotFoundError if the checkpoint does not exist.
    """
    src = _checkpoint_file(project_root, name.strip())
    if not src.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {name}")

    dest = project_root / STATE_DIR / STATE_FILE
    shutil.copy2(str(src), str(dest))


def list_checkpoints(project_root: Path) -> list[str]:
    """Return a sorted list of checkpoint names.

    Returns an empty list if no checkpoints exist.
    """
    cp_dir = _checkpoints_path(project_root)
    if not cp_dir.is_dir():
        return []
    return sorted(p.stem for p in cp_dir.glob("*.yaml"))


def delete_checkpoint(project_root: Path, name: str) -> bool:
    """Delete a named checkpoint.

    Returns True if the checkpoint was deleted, False if it did not exist.
    """
    path = _checkpoint_file(project_root, name.strip())
    if path.is_file():
        path.unlink()
        return True
    return False


def print_checkpoints(names: list[str]) -> None:
    """Pretty-print the list of checkpoints to the terminal."""
    if not names:
        console.print("  [dim]No checkpoints saved.[/dim]")
        return
    for name in names:
        console.print(f"  [blue]●[/blue] {name}")
