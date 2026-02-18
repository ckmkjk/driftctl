"""Handoff module for driftctl.

Generates a structured prompt block that can be pasted into the next
AI-agent session to give it full project context.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from driftctl.state import ComponentStatus, load_state

console = Console()


def generate_handoff(project_root: Path) -> str:
    """Build a structured handoff prompt from the current project state.

    The prompt includes project identity, component status, recent session
    history, active guardrails, and next-step suggestions.

    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)

    lines: list[str] = []
    lines.append("# PROJECT HANDOFF")
    lines.append("")

    # -- Identity -----------------------------------------------------------
    lines.append("## Identity")
    lines.append(f"- Project: {state.project}")
    lines.append(f"- Agent: {state.agent.value}")
    lines.append(f"- Stack: {state.stack}")
    lines.append(f"- Test command: {state.test_command}")
    lines.append(f"- Last updated: {state.last_updated}")
    lines.append("")

    # -- Components ---------------------------------------------------------
    lines.append("## Components")
    if state.components:
        for name, comp in state.components.items():
            dep = f" (depends on {comp.depends_on})" if comp.depends_on else ""
            lines.append(f"- {name}: {comp.status.value}{dep}")
    else:
        lines.append("- No components tracked yet.")
    lines.append("")

    # -- Recent sessions ----------------------------------------------------
    lines.append("## Recent Sessions")
    if state.sessions:
        recent = state.sessions[-3:]  # last 3 sessions
        for session in recent:
            commits = ", ".join(session.commits) if session.commits else "none"
            lines.append(f"- [{session.date}] {session.summary} (commits: {commits})")
    else:
        lines.append("- No sessions recorded yet.")
    lines.append("")

    # -- Guardrails ---------------------------------------------------------
    lines.append("## Guardrails")
    if state.guardrails:
        for rule in state.guardrails:
            lines.append(f"- {rule}")
    else:
        lines.append("- No guardrails configured.")
    lines.append("")

    # -- Suggested next steps -----------------------------------------------
    lines.append("## Suggested Next Steps")
    pending = [
        name for name, comp in state.components.items()
        if comp.status == ComponentStatus.PENDING
    ]
    in_progress = [
        name for name, comp in state.components.items()
        if comp.status == ComponentStatus.IN_PROGRESS
    ]
    blocked = [
        name for name, comp in state.components.items()
        if comp.status == ComponentStatus.BLOCKED
    ]

    if in_progress:
        lines.append(f"- Continue work on: {', '.join(in_progress)}")
    if blocked:
        lines.append(f"- Unblock: {', '.join(blocked)}")
    if pending:
        lines.append(f"- Start next: {', '.join(pending[:3])}")
    if not (in_progress or blocked or pending):
        lines.append("- All components complete.")
    lines.append("")

    return "\n".join(lines)


def print_handoff(handoff_text: str) -> None:
    """Pretty-print the handoff block to the terminal."""
    console.print(handoff_text)
