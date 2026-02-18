# ESCALATION — Unapproved Dependency Needed

## Step
Phase 1, Step 3 — driftctl/state.py

## Issue
The state file spec requires `.driftctl/state.yaml` (YAML format). Parsing and writing YAML requires `pyyaml` (or `ruamel.yaml`), which is **not** in the approved dependency list.

## Approved Dependencies
- click, rich, pydantic, gitpython, pytest

## Options
1. **Add `pyyaml` to approved dependencies** — standard, lightweight, widely used. This is the straightforward solution.
2. **Use JSON instead of YAML** — rename `state.yaml` to `state.json`. Pydantic has native JSON support. But this deviates from the spec.
3. **Use `pyyaml` via gitpython's transitive dependency** — gitpython does not guarantee pyyaml is available, so this is unreliable.

## Recommendation
Option 1: approve `pyyaml`. It's the most standard YAML library in Python and the spec explicitly calls for YAML.

## Resolution
**Resolved.** User approved `pyyaml`. Added to pyproject.toml dependencies.
