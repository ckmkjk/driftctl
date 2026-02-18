"""CLI entry point for driftctl.

Provides the top-level ``driftctl`` command group and stubs for all six
sub-commands: init, validate, status, handoff, drift, guard, and checkpoint.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console

from driftctl import __version__
from driftctl.state import AgentType, init_state, load_state

console = Console()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=__version__, prog_name="driftctl")
def cli() -> None:
    """driftctl — persistent project state, guard rails, and drift detection for AI coding agents."""


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--project", prompt="Project name", help="Name of the project.")
@click.option(
    "--agent",
    prompt="Agent",
    type=click.Choice([a.value for a in AgentType], case_sensitive=False),
    help="AI coding agent in use.",
)
@click.option("--stack", prompt="Tech stack", help="Primary tech stack.")
@click.option("--test-command", prompt="Test command", help="Command to run tests.")
def init(project: str, agent: str, stack: str, test_command: str) -> None:
    """Initialise a new .driftctl/state.yaml for this project."""
    root = Path.cwd()
    state = init_state(root, project, AgentType(agent), stack, test_command)
    console.print(f"[green]✓[/green] Initialised driftctl for [bold]{state.project}[/bold]")
    console.print(f"  State file: {root / '.driftctl' / 'state.yaml'}")


# ---------------------------------------------------------------------------
# validate (stub)
# ---------------------------------------------------------------------------

@cli.command()
def validate() -> None:
    """Run environment, git, test-suite, and contract checks."""
    console.print("[yellow]⚠[/yellow] validate is not yet implemented.")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def status(as_json: bool) -> None:
    """Show current project state."""
    root = Path.cwd()
    try:
        state = load_state(root)
    except FileNotFoundError:
        console.print("[red]✗[/red] No .driftctl/state.yaml found. Run [bold]driftctl init[/bold] first.")
        raise SystemExit(2)

    if as_json:
        import json

        click.echo(json.dumps(state.model_dump(mode="json"), indent=2))
    else:
        console.print(f"[bold]{state.project}[/bold]  agent={state.agent.value}  stack={state.stack}")
        console.print(f"  version:      {state.version}")
        console.print(f"  test command: {state.test_command}")
        console.print(f"  last updated: {state.last_updated}")
        console.print(f"  components:   {len(state.components)}")
        console.print(f"  sessions:     {len(state.sessions)}")
        console.print(f"  guardrails:   {len(state.guardrails)}")


# ---------------------------------------------------------------------------
# handoff (stub)
# ---------------------------------------------------------------------------

@cli.command()
def handoff() -> None:
    """Generate a structured prompt block for the next session."""
    console.print("[yellow]⚠[/yellow] handoff is not yet implemented.")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# drift (stub)
# ---------------------------------------------------------------------------

@cli.command()
def drift() -> None:
    """Compare current codebase against state contracts."""
    console.print("[yellow]⚠[/yellow] drift is not yet implemented.")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# guard (stub)
# ---------------------------------------------------------------------------

@cli.group()
def guard() -> None:
    """Manage guardrail rules."""


@guard.command()
def add() -> None:
    """Add a guardrail rule."""
    console.print("[yellow]⚠[/yellow] guard add is not yet implemented.")
    raise SystemExit(1)


@guard.command(name="list")
def list_rules() -> None:
    """List all guardrail rules."""
    console.print("[yellow]⚠[/yellow] guard list is not yet implemented.")
    raise SystemExit(1)


@guard.command()
def test() -> None:
    """Test guardrail rules against the codebase."""
    console.print("[yellow]⚠[/yellow] guard test is not yet implemented.")
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# checkpoint (stub)
# ---------------------------------------------------------------------------

@cli.group()
def checkpoint() -> None:
    """Save and rollback named state snapshots."""


@checkpoint.command()
@click.argument("name")
def save(name: str) -> None:
    """Save a named checkpoint."""
    console.print(f"[yellow]⚠[/yellow] checkpoint save '{name}' is not yet implemented.")
    raise SystemExit(1)


@checkpoint.command()
@click.argument("name")
def rollback(name: str) -> None:
    """Rollback to a named checkpoint."""
    console.print(f"[yellow]⚠[/yellow] checkpoint rollback '{name}' is not yet implemented.")
    raise SystemExit(1)
