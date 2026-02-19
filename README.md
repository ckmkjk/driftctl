# driftctl

Persistent project state, guard rails, and drift detection for AI coding agents.

`driftctl` gives AI agents like Claude Code, Cursor, and Copilot a shared source of truth across sessions — so they know what was built, what changed, and what to do next.

## Install

```bash
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Quick Start

```bash
# Initialise a new project (asks 4 questions)
driftctl init

# Sync state into CLAUDE.md (zero copy-paste for Claude Code)
driftctl sync

# Or generate a kickoff block to paste into any agent
driftctl kickoff

# Check project health
driftctl validate

# View current state
driftctl status
driftctl status --json

# Detect contract drift
driftctl drift

# Generate a handoff prompt at end of session
driftctl handoff
```

## Recommended Workflow

```
Session start:  driftctl sync       (or driftctl kickoff)
During work:    driftctl validate   (check health)
                driftctl guard test (check guardrails)
Session end:    driftctl handoff    (record what happened)
```

## Commands

### `driftctl init`

Creates `.driftctl/state.yaml` in the current directory. Prompts for:

- **Project name** — what this project is called
- **Agent** — which AI agent is in use (`claude-code`, `cursor`, `copilot`, `other`)
- **Stack** — primary tech stack (e.g. `python`, `node`, `rust`)
- **Test command** — command to run tests (e.g. `pytest`, `npm test`)

### `driftctl validate`

Runs four checks and reports pass/fail:

1. State file exists and parses correctly
2. Git repository is initialised
3. Test suite passes (skip with `--skip-tests`)
4. Contract hashes match their schema files

Exit codes: `0` = all passed, `1` = check(s) failed, `2` = error.

### `driftctl status`

Displays a human-readable summary of the project state. Use `--json` for machine-readable JSON output.

### `driftctl drift`

Compares every component's recorded contract hash against the current file on disk. Reports components as clean, drifted, missing, or no-contract.

### `driftctl kickoff`

Generate a ready-to-paste context block for starting any agent session. Outputs a Rich panel with project identity, component statuses, guardrails, last session, task queue, and agent instructions. Also saves to `.driftctl/kickoff_latest.md`.

```bash
driftctl kickoff
driftctl kickoff --component api      # focus on one component
driftctl kickoff --no-history          # exclude session history
```

### `driftctl sync`

Write current project state directly into `CLAUDE.md` in the project root. Claude Code reads this file automatically at session start — zero copy-paste required.

```bash
driftctl sync               # interactive (shows diff, asks to confirm)
driftctl sync --force        # overwrite without asking
driftctl sync --preview      # show what would be written, don't write
```

### `driftctl handoff`

Generates a structured markdown prompt block containing project identity, component status, recent sessions, guardrails, and suggested next steps. Paste this into your next AI session for seamless continuity.

### `driftctl guard`

Manage guardrail rules that protect your project:

```bash
# Add rules
driftctl guard add "require-file:README.md"
driftctl guard add "no-file:*.secret"
driftctl guard add "cmd:python -m pytest --co -q"

# List all rules
driftctl guard list

# Test all rules against the codebase
driftctl guard test
```

Rule types:
- `cmd:<command>` — passes if command exits 0
- `no-file:<glob>` — passes if no files match the pattern
- `require-file:<path>` — passes if the file exists
- Plain text — treated as a manual/descriptive rule (always passes)

### `driftctl checkpoint`

Save and restore named state snapshots:

```bash
# Save current state
driftctl checkpoint save before-refactor

# List checkpoints
driftctl checkpoint list

# Rollback to a checkpoint
driftctl checkpoint rollback before-refactor
```

## State File

State is stored in `.driftctl/state.yaml` with this schema:

- `version` — schema version
- `project` — project name
- `agent` — AI agent in use
- `stack` — tech stack
- `test_command` — how to run tests
- `last_updated` — ISO timestamp
- `components` — tracked components with status, contracts, and dependencies
- `sessions` — history of agent working sessions
- `guardrails` — list of project rules

## Running Tests

```bash
pytest
```
