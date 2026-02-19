# DRIFTCTL V1.1 BUILD INSTRUCTIONS
# READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE

## IDENTITY
You are extending driftctl — a Python CLI tool that gives AI coding agents
persistent project state, guard rails, and drift detection across sessions.
V1 is complete and working. You are adding two new commands to eliminate
manual copy paste between Claude.ai and Claude Code sessions.

## ABSOLUTE RULES — SAME AS V1, NEVER VIOLATE
1. Never modify more than one module at a time
2. Never skip writing tests before marking something complete
3. Never assume a file exists — always check first with Read
4. Only approved dependencies — see list below
5. Never move to the next command until current one passes tests
6. If uncertain about a decision — STOP and write ESCALATION.md
7. Commit after every working command. Not after every file.
8. Never refactor and add features in the same commit
9. Do not pause between steps for confirmation — continue autonomously
10. Only stop if ESCALATION.md is needed

## APPROVED DEPENDENCIES
Existing: click, rich, pydantic, gitpython, pyyaml, pytest
New allowed: jinja2 (for template rendering only)
No other packages without writing ESCALATION.md first

## EXISTING CODEBASE — READ THESE BEFORE WRITING ANYTHING
- driftctl/cli.py — existing commands, add new ones here
- driftctl/state.py — state engine, read/write state.yaml
- driftctl/handoff.py — existing handoff logic, kickoff extends this
- driftctl/__init__.py — version number
- tests/ — all existing tests must still pass

## WHAT YOU ARE BUILDING — TWO COMMANDS ONLY

### COMMAND 1: driftctl kickoff
Purpose: Generate one ready-to-paste context block for starting
any agent session. Eliminates manual assembly of state + guardrails
+ session context.

What it outputs to terminal:
A single formatted block the user copies and pastes as their
first message to Claude Code or any agent. Block contains:
  - Project name, stack, agent
  - Current component statuses
  - All active guardrails
  - Last session summary if exists
  - Current task queue if exists
  - Instruction to agent: read this, confirm understanding,
    then ask what to work on

Output format: Rich panel with copyable text inside.
Also write the block to .driftctl/kickoff_latest.md so
user can also open and copy from file.

Command signature:
  driftctl kickoff

Optional flags:
  --component [name]  focus context on specific component only
  --no-history        exclude session history from output

### COMMAND 2: driftctl sync
Purpose: Write current project state directly into CLAUDE.md
in the project root. Claude Code reads CLAUDE.md automatically
at session start. Zero copy paste required.

What it writes to CLAUDE.md:
  - Auto-generated header warning not to edit manually
  - Project identity block (name, agent, stack)
  - Current guardrails as numbered rules
  - Component status table
  - Last session summary
  - Standard agent instructions:
      * Read this file fully before writing any code
      * Run driftctl validate before starting work
      * Run driftctl handoff at end of session
      * Write ESCALATION.md if uncertain, never guess
      * Commit after each working component

Behavior:
  - If CLAUDE.md exists: show diff of what will change, 
    overwrite after confirmation
  - If CLAUDE.md does not exist: create it silently
  - Always append timestamp of last sync at bottom

Command signature:
  driftctl sync

Optional flags:
  --force             skip confirmation, always overwrite
  --preview           show what would be written without writing

## BUILD ORDER — STRICTLY SEQUENTIAL

Phase 1: kickoff command
  Step 1 → Read all existing code listed above, confirm understanding
  Step 2 → Add kickoff() function to driftctl/handoff.py
  Step 3 → Wire kickoff command in driftctl/cli.py
  Step 4 → Write tests/test_kickoff.py — all tests pass
  Step 5 → Commit: "add driftctl kickoff command"

Phase 2: sync command  
  Step 6 → Create driftctl/sync.py with sync logic and
            CLAUDE.md template
  Step 7 → Wire sync command in driftctl/cli.py
  Step 8 → Write tests/test_sync.py — all tests pass
  Step 9 → Commit: "add driftctl sync command"

Phase 3: Integration
  Step 10 → Run full test suite — all 105 + new tests pass
  Step 11 → Test kickoff on real project (AlphaEngineV4)
  Step 12 → Test sync on real project (AlphaEngineV4),
             verify CLAUDE.md is written correctly
  Step 13 → Update README.md with new commands and workflow
  Step 14 → Final commit: "v1.1 complete — kickoff and sync"

## CLAUDE.md TEMPLATE — implement exactly this structure
---
# DRIFTCTL MANAGED — DO NOT EDIT MANUALLY
# Last synced: {timestamp}
# To update run: driftctl sync

## Project
- Name: {project_name}
- Agent: {agent}
- Stack: {stack}
- Test command: {test_command}

## Guardrails — follow these at all times
{numbered list of guardrails}

## Component Status
{table of components with status}

## Last Session
{last session summary or "No sessions recorded yet"}

## Agent Instructions
1. Read this file fully before writing any code
2. Run `driftctl validate` — if it fails stop and fix it
3. Never violate the guardrails listed above
4. Commit after each working component passes tests
5. Write ESCALATION.md if uncertain — never guess
6. Run `driftctl handoff` at end of session
---

## PROGRESS TRACKING
Update PROGRESS.md after each step:
  - Step number and name
  - Status: complete
  - Tests passing: yes/no
  - Notes on decisions made

## ESCALATION PROTOCOL
Stop and write ESCALATION.md if you hit:
  - Ambiguity about command behavior
  - Dependency needed not in approved list
  - Test you cannot pass after 2 attempts
  - Architectural decision not covered here

## SUCCESS CRITERIA
Build is complete when:
  - driftctl kickoff runs and outputs a formatted context block
  - driftctl sync runs and writes a valid CLAUDE.md
  - All existing 105 tests still pass
  - New tests cover both commands
  - README updated with new workflow
  - Tested on AlphaEngineV4 as real project