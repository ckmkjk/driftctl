"""Handoff module for driftctl.

Generates structured prompt blocks that can be pasted into AI-agent
sessions to give them full project context.  Includes both the
end-of-session ``handoff`` and the start-of-session ``kickoff``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from driftctl.state import STATE_DIR, ComponentStatus, load_state

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


# ---------------------------------------------------------------------------
# Kickoff — start-of-session context block
# ---------------------------------------------------------------------------

KICKOFF_FILE = "kickoff_latest.md"


def generate_kickoff(
    project_root: Path,
    *,
    component: Optional[str] = None,
    include_history: bool = True,
) -> str:
    """Build a ready-to-paste context block for starting an agent session.

    The block contains project identity, component statuses, guardrails,
    last session summary, and an instruction for the receiving agent.

    Args:
        project_root: Path to the project root directory.
        component: If provided, focus context on this single component.
        include_history: If False, exclude session history from output.

    Raises:
        FileNotFoundError: If the state file does not exist.
        ValueError: If *component* is specified but does not exist in state.
    """
    state = load_state(project_root)

    lines: list[str] = []
    lines.append("# SESSION KICKOFF")
    lines.append("")

    # -- Identity -----------------------------------------------------------
    lines.append("## Project")
    lines.append(f"- Name: {state.project}")
    lines.append(f"- Agent: {state.agent.value}")
    lines.append(f"- Stack: {state.stack}")
    lines.append(f"- Test command: {state.test_command}")
    lines.append("")

    # -- Components ---------------------------------------------------------
    lines.append("## Component Status")
    if component:
        if component not in state.components:
            raise ValueError(f"Component not found: {component}")
        comp = state.components[component]
        dep = f" (depends on {comp.depends_on})" if comp.depends_on else ""
        lines.append(f"- {component}: {comp.status.value}{dep}")
    elif state.components:
        for name, comp in state.components.items():
            dep = f" (depends on {comp.depends_on})" if comp.depends_on else ""
            lines.append(f"- {name}: {comp.status.value}{dep}")
    else:
        lines.append("- No components tracked yet.")
    lines.append("")

    # -- Guardrails ---------------------------------------------------------
    lines.append("## Guardrails")
    if state.guardrails:
        for i, rule in enumerate(state.guardrails, 1):
            lines.append(f"{i}. {rule}")
    else:
        lines.append("- No guardrails configured.")
    lines.append("")

    # -- Last session -------------------------------------------------------
    if include_history:
        lines.append("## Last Session")
        if state.sessions:
            last = state.sessions[-1]
            commits = ", ".join(last.commits) if last.commits else "none"
            lines.append(f"- Date: {last.date}")
            lines.append(f"- Summary: {last.summary}")
            lines.append(f"- Commits: {commits}")
        else:
            lines.append("- No sessions recorded yet.")
        lines.append("")

    # -- Task queue (pending / in-progress) ---------------------------------
    lines.append("## Task Queue")
    if component:
        # Scoped to the single component
        filtered = {component: state.components[component]}
    else:
        filtered = state.components
    in_progress = [
        name for name, c in filtered.items()
        if c.status == ComponentStatus.IN_PROGRESS
    ]
    pending = [
        name for name, c in filtered.items()
        if c.status == ComponentStatus.PENDING
    ]
    blocked = [
        name for name, c in filtered.items()
        if c.status == ComponentStatus.BLOCKED
    ]
    if in_progress:
        lines.append(f"- In progress: {', '.join(in_progress)}")
    if pending:
        lines.append(f"- Pending: {', '.join(pending)}")
    if blocked:
        lines.append(f"- Blocked: {', '.join(blocked)}")
    if not (in_progress or pending or blocked):
        lines.append("- All components complete.")
    lines.append("")

    # -- Agent instruction --------------------------------------------------
    lines.append("## Instructions")
    lines.append("Read the above context. Confirm you understand the project,")
    lines.append("the component statuses, and the guardrails. Then ask what")
    lines.append("to work on next.")
    lines.append("")

    return "\n".join(lines)


def save_kickoff(project_root: Path, kickoff_text: str) -> Path:
    """Write the kickoff block to .driftctl/kickoff_latest.md.

    Returns the path to the written file.
    """
    path = project_root / STATE_DIR / KICKOFF_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(kickoff_text, encoding="utf-8")
    return path


def print_kickoff(kickoff_text: str) -> None:
    """Display the kickoff block in a Rich panel for easy copying."""
    console.print(Panel(kickoff_text, title="SESSION KICKOFF", border_style="blue"))
    console.print(
        "\n[dim]Copied to .driftctl/kickoff_latest.md — "
        "paste the above block as your first message to the agent.[/dim]"
    )
