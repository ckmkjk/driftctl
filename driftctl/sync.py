"""Sync module for driftctl.

Writes current project state into CLAUDE.md in the project root so that
Claude Code automatically reads it at session start — zero copy-paste.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from driftctl.state import load_state

console = Console()

CLAUDE_MD = "CLAUDE.md"
HEADER_MARKER = "# DRIFTCTL MANAGED — DO NOT EDIT MANUALLY"


def generate_claude_md(project_root: Path) -> str:
    """Build the CLAUDE.md content from the current project state.

    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)
    timestamp = datetime.now(timezone.utc).isoformat()

    lines: list[str] = []

    # -- Header -------------------------------------------------------------
    lines.append(HEADER_MARKER)
    lines.append(f"# Last synced: {timestamp}")
    lines.append("# To update run: driftctl sync")
    lines.append("")

    # -- Project identity ---------------------------------------------------
    lines.append("## Project")
    lines.append(f"- Name: {state.project}")
    lines.append(f"- Agent: {state.agent.value}")
    lines.append(f"- Stack: {state.stack}")
    lines.append(f"- Test command: {state.test_command}")
    lines.append("")

    # -- Guardrails ---------------------------------------------------------
    lines.append("## Guardrails — follow these at all times")
    if state.guardrails:
        for i, rule in enumerate(state.guardrails, 1):
            lines.append(f"{i}. {rule}")
    else:
        lines.append("No guardrails configured yet.")
    lines.append("")

    # -- Component status ---------------------------------------------------
    lines.append("## Component Status")
    if state.components:
        lines.append("| Component | Status | Depends On |")
        lines.append("|-----------|--------|------------|")
        for name, comp in state.components.items():
            dep = comp.depends_on or "—"
            lines.append(f"| {name} | {comp.status.value} | {dep} |")
    else:
        lines.append("No components tracked yet.")
    lines.append("")

    # -- Last session -------------------------------------------------------
    lines.append("## Last Session")
    if state.sessions:
        last = state.sessions[-1]
        commits = ", ".join(last.commits) if last.commits else "none"
        lines.append(f"- Date: {last.date}")
        lines.append(f"- Summary: {last.summary}")
        lines.append(f"- Commits: {commits}")
    else:
        lines.append("No sessions recorded yet.")
    lines.append("")

    # -- Agent instructions -------------------------------------------------
    lines.append("## Agent Instructions")
    lines.append("1. Read this file fully before writing any code")
    lines.append("2. Run `driftctl validate` — if it fails stop and fix it")
    lines.append("3. Never violate the guardrails listed above")
    lines.append("4. Commit after each working component passes tests")
    lines.append("5. Write ESCALATION.md if uncertain — never guess")
    lines.append("6. Run `driftctl handoff` at end of session")
    lines.append("")

    return "\n".join(lines)


def compute_diff(existing: str, new: str) -> str | None:
    """Return a human-readable diff between existing and new content.

    Returns None if the content is identical.
    """
    if existing.strip() == new.strip():
        return None

    old_lines = existing.strip().splitlines()
    new_lines = new.strip().splitlines()

    diff_lines: list[str] = []
    diff_lines.append("[dim]--- existing CLAUDE.md[/dim]")
    diff_lines.append("[dim]+++ new CLAUDE.md[/dim]")

    # Simple line-by-line comparison
    max_len = max(len(old_lines), len(new_lines))
    for i in range(max_len):
        old = old_lines[i] if i < len(old_lines) else ""
        new = new_lines[i] if i < len(new_lines) else ""
        if old != new:
            if old:
                diff_lines.append(f"[red]- {old}[/red]")
            if new:
                diff_lines.append(f"[green]+ {new}[/green]")

    return "\n".join(diff_lines)


def write_claude_md(project_root: Path, content: str) -> Path:
    """Write content to CLAUDE.md in the project root.

    Returns the path to the written file.
    """
    path = project_root / CLAUDE_MD
    path.write_text(content, encoding="utf-8")
    return path


def sync(
    project_root: Path,
    *,
    force: bool = False,
    preview: bool = False,
) -> str:
    """Sync project state to CLAUDE.md.

    Args:
        project_root: Path to the project root directory.
        force: Skip confirmation when CLAUDE.md already exists.
        preview: Show what would be written without writing.

    Returns the generated CLAUDE.md content.

    Raises:
        FileNotFoundError: If the state file does not exist.
    """
    content = generate_claude_md(project_root)
    claude_path = project_root / CLAUDE_MD

    if preview:
        console.print("[bold]Preview — CLAUDE.md would contain:[/bold]\n")
        console.print(content)
        return content

    if claude_path.is_file() and not force:
        existing = claude_path.read_text(encoding="utf-8")
        diff = compute_diff(existing, content)
        if diff is None:
            console.print("[dim]CLAUDE.md is already up to date.[/dim]")
            return content
        console.print("[bold]Changes to CLAUDE.md:[/bold]\n")
        console.print(diff)
        console.print()
        if not _confirm_overwrite():
            console.print("[yellow]Sync cancelled.[/yellow]")
            raise SystemExit(0)

    write_claude_md(project_root, content)
    console.print(f"[green]✓[/green] CLAUDE.md synced at {claude_path}")
    return content


def _confirm_overwrite() -> bool:
    """Ask the user to confirm overwriting CLAUDE.md.

    Returns True if the user confirms.
    """
    import click

    return click.confirm("Overwrite CLAUDE.md?", default=True)
