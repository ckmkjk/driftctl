# DRIFTCTL BUILD INSTRUCTIONS
# READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE

## IDENTITY
You are building `driftctl` — a Python CLI tool that gives AI coding agents 
persistent project state, guard rails, and drift detection across sessions.
You are the agent. You are building the tool that makes agents like you 
more reliable. Act accordingly.

## ABSOLUTE RULES — NEVER VIOLATE THESE
1. Never modify more than one module at a time
2. Never skip writing tests before marking something complete
3. Never assume a file exists — always check first with Read
4. Never install a dependency not in the approved list below
5. Never move to the next component until current one passes tests
6. If you are uncertain about a decision — STOP and write 
   ESCALATION.md with your question. Do not guess.
7. Commit after every working component. Not after every file. 
   After every WORKING component.
8. Never refactor and add features in the same commit

## APPROVED DEPENDENCIES ONLY
- click
- rich
- pydantic
- gitpython
- pytest (testing only)
No other packages without human approval.

## PROJECT STRUCTURE — BUILD EXACTLY THIS, NOTHING MORE
driftctl/
├── driftctl/
│   ├── __init__.py
│   ├── cli.py
│   ├── state.py
│   ├── validator.py
│   ├── guard.py
│   ├── drift.py
│   ├── handoff.py
│   └── checkpoint.py
├── tests/
│   ├── test_state.py
│   ├── test_validator.py
│   ├── test_guard.py
│   ├── test_drift.py
│   └── test_handoff.py
├── pyproject.toml
└── README.md

## BUILD ORDER — DO NOT DEVIATE
Phase 1: Foundation
  Step 1 → pyproject.toml (package config, entry point)
  Step 2 → driftctl/__init__.py (version only)
  Step 3 → driftctl/state.py (state engine + pydantic schema)
  Step 4 → tests/test_state.py (write and pass before moving on)
  Step 5 → driftctl/cli.py (wire up click, stub all 6 commands)
  
Phase 2: Core Commands
  Step 6 → driftctl/validator.py + tests
  Step 7 → driftctl/guard.py + tests
  Step 8 → driftctl/drift.py + tests
  
Phase 3: Session Commands
  Step 9 → driftctl/handoff.py + tests
  Step 10 → driftctl/checkpoint.py + tests

Phase 4: Polish
  Step 11 → Wire all commands fully in cli.py
  Step 12 → README.md with install + usage instructions
  Step 13 → Full integration test — run all 6 commands end to end

## STATE FILE SPEC — implement exactly this schema
Location: .driftctl/state.yaml in project root
Fields:
  version: string
  project: string
  agent: string (claude-code | cursor | copilot | other)
  stack: string
  test_command: string
  last_updated: ISO datetime
  components: dict of component objects
    each component has:
      status: pending | in_progress | complete | blocked
      output_schema: filepath string or null
      contract_hash: md5 hash of output schema or null
      depends_on: component name or null
  sessions: list of session objects
    each session has:
      date: ISO date
      summary: string
      commits: list of strings
  guardrails: list of strings

## THE 6 CLI COMMANDS — implement these exactly
driftctl init     → creates .driftctl/state.yaml, asks 4 questions
driftctl validate → env check + git check + test suite + contract check
driftctl status   → human readable + JSON output of state.yaml
driftctl handoff  → generates structured prompt block for next session
driftctl drift    → compares current codebase against state contracts
driftctl guard    → manage guardrail rules (add/list/test subcommands)
driftctl checkpoint → save/rollback named state snapshots

## OUTPUT QUALITY REQUIREMENTS
- Every function needs a docstring
- Every module needs a module-level docstring  
- rich console for all terminal output (colors, tables, icons)
- All errors must be caught and displayed cleanly — no raw tracebacks
- Exit codes: 0 = success, 1 = validation failure, 2 = error

## PROGRESS TRACKING
After completing each step, update PROGRESS.md:
  - Step number and name
  - Status: complete
  - Tests passing: yes/no
  - Notes on any decisions made

## ESCALATION PROTOCOL
If you hit any of these — STOP and write ESCALATION.md:
  - Ambiguity about what a command should do
  - A dependency you think is needed but isn't approved
  - A test that you cannot make pass after 2 attempts
  - Any architectural decision not covered in this document

## HOW TO START
1. Read this entire file — done
2. Check if pyproject.toml exists — if yes read it, if no create it
3. Run: git init (if not already initialized)
4. Begin Step 1
```

---

**Then paste this as your first message to Claude Code:**
```
Read BUILD.md in full. Confirm you understand all rules, 
the build order, and the escalation protocol before 
writing any code. Then begin Phase 1 Step 1.