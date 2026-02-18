"""State engine for driftctl.

Manages the .driftctl/state.yaml file — loading, saving, creating,
and updating project state used by all other driftctl commands.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ComponentStatus(str, Enum):
    """Valid statuses for a tracked component."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class AgentType(str, Enum):
    """Recognised AI coding agents."""

    CLAUDE_CODE = "claude-code"
    CURSOR = "cursor"
    COPILOT = "copilot"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------

class Component(BaseModel):
    """A single tracked component inside the project state."""

    status: ComponentStatus = ComponentStatus.PENDING
    output_schema: Optional[str] = None
    contract_hash: Optional[str] = None
    depends_on: Optional[str] = None


class Session(BaseModel):
    """Record of one agent working session."""

    date: str
    summary: str
    commits: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    """Root schema for .driftctl/state.yaml — the single source of truth."""

    version: str = "0.1.0"
    project: str = ""
    agent: AgentType = AgentType.OTHER
    stack: str = ""
    test_command: str = ""
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    components: dict[str, Component] = Field(default_factory=dict)
    sessions: list[Session] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = ".driftctl"
STATE_FILE = "state.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_path(project_root: Path) -> Path:
    """Return the full path to the state file for a given project root."""
    return project_root / STATE_DIR / STATE_FILE


def compute_contract_hash(filepath: Path) -> Optional[str]:
    """Compute the MD5 hash of a file's contents.

    Returns None if the file does not exist.
    """
    if not filepath.is_file():
        return None
    return hashlib.md5(filepath.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# State engine — public API
# ---------------------------------------------------------------------------

def init_state(
    project_root: Path,
    project: str,
    agent: AgentType,
    stack: str,
    test_command: str,
) -> ProjectState:
    """Create a new state file at *project_root*/.driftctl/state.yaml.

    Overwrites any existing state file.  Returns the newly created state.
    """
    state = ProjectState(
        project=project,
        agent=agent,
        stack=stack,
        test_command=test_command,
    )
    save_state(project_root, state)
    return state


def load_state(project_root: Path) -> ProjectState:
    """Load and validate the state file from disk.

    Raises FileNotFoundError if the state file does not exist.
    """
    path = _state_path(project_root)
    if not path.is_file():
        raise FileNotFoundError(f"State file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ProjectState.model_validate(raw)


def save_state(project_root: Path, state: ProjectState) -> Path:
    """Write *state* to disk, updating the last_updated timestamp.

    Creates the .driftctl directory if it does not exist.
    Returns the path to the written file.
    """
    state.last_updated = datetime.now(timezone.utc).isoformat()

    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = state.model_dump(mode="json")
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
    return path


def add_component(
    state: ProjectState,
    name: str,
    status: ComponentStatus = ComponentStatus.PENDING,
    output_schema: Optional[str] = None,
    depends_on: Optional[str] = None,
) -> ProjectState:
    """Add or update a component in the state.

    If *output_schema* points to an existing file its MD5 hash is computed
    automatically.
    """
    contract_hash = None
    if output_schema:
        contract_hash = compute_contract_hash(Path(output_schema))

    state.components[name] = Component(
        status=status,
        output_schema=output_schema,
        contract_hash=contract_hash,
        depends_on=depends_on,
    )
    return state


def add_session(
    state: ProjectState,
    summary: str,
    commits: list[str] | None = None,
) -> ProjectState:
    """Append a new session record to the state."""
    session = Session(
        date=datetime.now(timezone.utc).date().isoformat(),
        summary=summary,
        commits=commits or [],
    )
    state.sessions.append(session)
    return state
