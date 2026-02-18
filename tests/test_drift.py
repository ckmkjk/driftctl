"""Tests for driftctl.drift — drift detection."""

from pathlib import Path

import pytest

from driftctl.state import AgentType, add_component, init_state, save_state
from driftctl.drift import DriftResult, detect_drift


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project(tmp_path):
    """Create a minimal project with state file."""
    init_state(tmp_path, "drifttest", AgentType.OTHER, "python", "pytest")
    return tmp_path


# ---------------------------------------------------------------------------
# DriftResult
# ---------------------------------------------------------------------------


class TestDriftResult:
    """DriftResult dataclass behaviour."""

    def test_ok_when_empty(self):
        """Empty result is ok."""
        r = DriftResult()
        assert r.ok is True

    def test_ok_when_clean(self):
        """Clean results are ok."""
        r = DriftResult(clean=["a"])
        assert r.ok is True

    def test_not_ok_when_drifted(self):
        """Drifted results are not ok."""
        r = DriftResult(drifted=["a"])
        assert r.ok is False

    def test_not_ok_when_missing(self):
        """Missing schema files are not ok."""
        r = DriftResult(missing=["a"])
        assert r.ok is False

    def test_no_contract_still_ok(self):
        """Components without contracts don't cause failure."""
        r = DriftResult(no_contract=["a"])
        assert r.ok is True


# ---------------------------------------------------------------------------
# detect_drift
# ---------------------------------------------------------------------------


class TestDetectDrift:
    """detect_drift against various codebase states."""

    def test_no_components(self, project):
        """No components means no drift."""
        result = detect_drift(project)
        assert result.ok is True
        assert len(result.clean) == 0
        assert len(result.no_contract) == 0

    def test_no_state_raises(self, tmp_path):
        """Raises FileNotFoundError when no state file."""
        with pytest.raises(FileNotFoundError):
            detect_drift(tmp_path)

    def test_component_no_contract(self, project):
        """Component without output_schema is categorised as no_contract."""
        state = init_state(project, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api")
        save_state(project, state)

        result = detect_drift(project)
        assert result.ok is True
        assert "api" in result.no_contract

    def test_clean_component(self, project):
        """Component with matching hash is clean."""
        schema = project / "schema.json"
        schema.write_text('{"type": "object"}')

        state = init_state(project, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema))
        save_state(project, state)

        result = detect_drift(project)
        assert result.ok is True
        assert "api" in result.clean

    def test_drifted_component(self, project):
        """Component with changed file content is drifted."""
        schema = project / "schema.json"
        schema.write_text('{"type": "object"}')

        state = init_state(project, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema))
        save_state(project, state)

        # Modify the file
        schema.write_text('{"type": "array"}')

        result = detect_drift(project)
        assert result.ok is False
        assert "api" in result.drifted

    def test_missing_schema_file(self, project):
        """Component with deleted schema file is missing."""
        schema = project / "schema.json"
        schema.write_text('{"type": "object"}')

        state = init_state(project, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "api", output_schema=str(schema))
        save_state(project, state)

        # Delete the file
        schema.unlink()

        result = detect_drift(project)
        assert result.ok is False
        assert "api" in result.missing

    def test_mixed_components(self, project):
        """Multiple components with different states."""
        schema_a = project / "a.json"
        schema_a.write_text("aaa")
        schema_b = project / "b.json"
        schema_b.write_text("bbb")

        state = init_state(project, "proj", AgentType.OTHER, "python", "pytest")
        add_component(state, "clean_comp", output_schema=str(schema_a))
        add_component(state, "no_contract_comp")
        add_component(state, "drift_comp", output_schema=str(schema_b))
        save_state(project, state)

        # Drift one file
        schema_b.write_text("changed")

        result = detect_drift(project)
        assert result.ok is False
        assert "clean_comp" in result.clean
        assert "no_contract_comp" in result.no_contract
        assert "drift_comp" in result.drifted
