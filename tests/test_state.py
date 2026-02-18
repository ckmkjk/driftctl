"""Tests for driftctl.state — state engine and Pydantic schema."""

import hashlib
from pathlib import Path

import pytest
import yaml

from driftctl.state import (
    AgentType,
    Component,
    ComponentStatus,
    ProjectState,
    Session,
    add_component,
    add_session,
    compute_contract_hash,
    init_state,
    load_state,
    save_state,
)


# ---------------------------------------------------------------------------
# Schema / model tests
# ---------------------------------------------------------------------------


class TestComponentStatus:
    """ComponentStatus enum values match the spec."""

    def test_values(self):
        """All four statuses exist with correct string values."""
        assert ComponentStatus.PENDING == "pending"
        assert ComponentStatus.IN_PROGRESS == "in_progress"
        assert ComponentStatus.COMPLETE == "complete"
        assert ComponentStatus.BLOCKED == "blocked"


class TestAgentType:
    """AgentType enum values match the spec."""

    def test_values(self):
        """All four agent types exist with correct string values."""
        assert AgentType.CLAUDE_CODE == "claude-code"
        assert AgentType.CURSOR == "cursor"
        assert AgentType.COPILOT == "copilot"
        assert AgentType.OTHER == "other"


class TestComponent:
    """Component model defaults and validation."""

    def test_defaults(self):
        """A bare Component gets sensible defaults."""
        c = Component()
        assert c.status == ComponentStatus.PENDING
        assert c.output_schema is None
        assert c.contract_hash is None
        assert c.depends_on is None

    def test_explicit_values(self):
        """Component accepts explicit field values."""
        c = Component(
            status=ComponentStatus.COMPLETE,
            output_schema="schema.json",
            contract_hash="abc123",
            depends_on="other_component",
        )
        assert c.status == ComponentStatus.COMPLETE
        assert c.output_schema == "schema.json"
        assert c.contract_hash == "abc123"
        assert c.depends_on == "other_component"


class TestSession:
    """Session model."""

    def test_required_fields(self):
        """Session requires date and summary."""
        s = Session(date="2026-02-18", summary="Initial setup")
        assert s.date == "2026-02-18"
        assert s.summary == "Initial setup"
        assert s.commits == []

    def test_with_commits(self):
        """Session accepts a list of commit hashes."""
        s = Session(date="2026-02-18", summary="Work", commits=["abc123", "def456"])
        assert len(s.commits) == 2


class TestProjectState:
    """ProjectState root model."""

    def test_defaults(self):
        """A bare ProjectState gets all defaults."""
        ps = ProjectState()
        assert ps.version == "0.1.0"
        assert ps.project == ""
        assert ps.agent == AgentType.OTHER
        assert ps.stack == ""
        assert ps.test_command == ""
        assert ps.last_updated  # non-empty ISO string
        assert ps.components == {}
        assert ps.sessions == []
        assert ps.guardrails == []

    def test_round_trip_dict(self):
        """model_dump / model_validate round-trips cleanly."""
        ps = ProjectState(project="myapp", agent=AgentType.CLAUDE_CODE, stack="python")
        data = ps.model_dump(mode="json")
        restored = ProjectState.model_validate(data)
        assert restored.project == "myapp"
        assert restored.agent == AgentType.CLAUDE_CODE
        assert restored.stack == "python"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestComputeContractHash:
    """compute_contract_hash helper."""

    def test_existing_file(self, tmp_path):
        """Returns MD5 hex digest for an existing file."""
        f = tmp_path / "schema.json"
        content = b'{"type": "object"}'
        f.write_bytes(content)
        expected = hashlib.md5(content).hexdigest()
        assert compute_contract_hash(f) == expected

    def test_missing_file(self, tmp_path):
        """Returns None when file does not exist."""
        assert compute_contract_hash(tmp_path / "nope.json") is None


# ---------------------------------------------------------------------------
# State engine — init / save / load
# ---------------------------------------------------------------------------


class TestInitState:
    """init_state creates .driftctl/state.yaml."""

    def test_creates_file(self, tmp_path):
        """State file is created on disk."""
        init_state(tmp_path, "myapp", AgentType.CLAUDE_CODE, "python", "pytest")
        state_file = tmp_path / ".driftctl" / "state.yaml"
        assert state_file.is_file()

    def test_returns_state(self, tmp_path):
        """Returns a valid ProjectState."""
        state = init_state(tmp_path, "myapp", AgentType.CURSOR, "node", "npm test")
        assert state.project == "myapp"
        assert state.agent == AgentType.CURSOR
        assert state.stack == "node"
        assert state.test_command == "npm test"

    def test_yaml_readable(self, tmp_path):
        """The written file is valid YAML matching the schema."""
        init_state(tmp_path, "proj", AgentType.OTHER, "go", "go test ./...")
        raw = yaml.safe_load(
            (tmp_path / ".driftctl" / "state.yaml").read_text(encoding="utf-8")
        )
        assert raw["project"] == "proj"
        assert raw["agent"] == "other"
        assert raw["stack"] == "go"


class TestSaveAndLoad:
    """save_state and load_state round-trip."""

    def test_round_trip(self, tmp_path):
        """Save then load returns equivalent state."""
        original = ProjectState(
            project="roundtrip",
            agent=AgentType.COPILOT,
            stack="rust",
            test_command="cargo test",
            guardrails=["no force push"],
        )
        save_state(tmp_path, original)
        loaded = load_state(tmp_path)
        assert loaded.project == "roundtrip"
        assert loaded.agent == AgentType.COPILOT
        assert loaded.stack == "rust"
        assert loaded.test_command == "cargo test"
        assert loaded.guardrails == ["no force push"]

    def test_load_missing_raises(self, tmp_path):
        """load_state raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            load_state(tmp_path)

    def test_save_updates_timestamp(self, tmp_path):
        """Each save refreshes last_updated."""
        state = ProjectState(project="ts")
        first_ts = state.last_updated
        save_state(tmp_path, state)
        assert state.last_updated != first_ts  # updated by save_state

    def test_save_creates_directory(self, tmp_path):
        """save_state creates .driftctl/ if missing."""
        state = ProjectState(project="mkdir")
        save_state(tmp_path, state)
        assert (tmp_path / ".driftctl").is_dir()


# ---------------------------------------------------------------------------
# Mutation helpers
# ---------------------------------------------------------------------------


class TestAddComponent:
    """add_component helper."""

    def test_adds_component(self):
        """Component appears in state.components."""
        state = ProjectState()
        add_component(state, "api")
        assert "api" in state.components
        assert state.components["api"].status == ComponentStatus.PENDING

    def test_with_status(self):
        """Component accepts an explicit status."""
        state = ProjectState()
        add_component(state, "db", status=ComponentStatus.COMPLETE)
        assert state.components["db"].status == ComponentStatus.COMPLETE

    def test_with_depends_on(self):
        """Component records its dependency."""
        state = ProjectState()
        add_component(state, "frontend", depends_on="api")
        assert state.components["frontend"].depends_on == "api"

    def test_with_output_schema_existing_file(self, tmp_path):
        """contract_hash is computed when output_schema file exists."""
        schema = tmp_path / "schema.json"
        schema.write_bytes(b'{"key": "value"}')
        state = ProjectState()
        add_component(state, "comp", output_schema=str(schema))
        assert state.components["comp"].contract_hash is not None

    def test_with_output_schema_missing_file(self):
        """contract_hash is None when output_schema file doesn't exist."""
        state = ProjectState()
        add_component(state, "comp", output_schema="/nonexistent/schema.json")
        assert state.components["comp"].contract_hash is None

    def test_overwrite_component(self):
        """Adding a component with the same name overwrites it."""
        state = ProjectState()
        add_component(state, "api", status=ComponentStatus.PENDING)
        add_component(state, "api", status=ComponentStatus.COMPLETE)
        assert state.components["api"].status == ComponentStatus.COMPLETE


class TestAddSession:
    """add_session helper."""

    def test_appends_session(self):
        """Session is appended to the list."""
        state = ProjectState()
        add_session(state, "Did some work")
        assert len(state.sessions) == 1
        assert state.sessions[0].summary == "Did some work"
        assert state.sessions[0].date  # non-empty

    def test_with_commits(self):
        """Session records commit hashes."""
        state = ProjectState()
        add_session(state, "Commit work", commits=["aaa", "bbb"])
        assert state.sessions[0].commits == ["aaa", "bbb"]

    def test_multiple_sessions(self):
        """Multiple sessions accumulate."""
        state = ProjectState()
        add_session(state, "Session 1")
        add_session(state, "Session 2")
        assert len(state.sessions) == 2


# ---------------------------------------------------------------------------
# Full integration: init → mutate → save → load
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    """End-to-end: init, add components/sessions, save, reload."""

    def test_full_workflow(self, tmp_path):
        """State survives a full create-mutate-save-load cycle."""
        state = init_state(tmp_path, "fulltest", AgentType.CLAUDE_CODE, "python", "pytest")

        add_component(state, "state_engine", status=ComponentStatus.COMPLETE)
        add_component(state, "cli", status=ComponentStatus.PENDING, depends_on="state_engine")
        add_session(state, "Built the state engine", commits=["abc123"])
        state.guardrails.append("never skip tests")

        save_state(tmp_path, state)
        loaded = load_state(tmp_path)

        assert loaded.project == "fulltest"
        assert loaded.agent == AgentType.CLAUDE_CODE
        assert len(loaded.components) == 2
        assert loaded.components["state_engine"].status == ComponentStatus.COMPLETE
        assert loaded.components["cli"].depends_on == "state_engine"
        assert len(loaded.sessions) == 1
        assert loaded.sessions[0].commits == ["abc123"]
        assert "never skip tests" in loaded.guardrails
