"""CLI entry point for driftctl.

Provides the top-level ``driftctl`` command group and all six
sub-commands: init, validate, status, handoff, drift, guard, and checkpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

from driftctl import __version__
from driftctl.state import AgentType, init_state, load_state

console = Console()


def _handle_missing_state() -> None:
    """Print error and exit when state file is missing."""
    console.print("[red]✗[/red] No .driftctl/state.yaml found. Run [bold]driftctl init[/bold] first.")
    raise SystemExit(2)


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
    try:
        state = init_state(root, project, AgentType(agent), stack, test_command)
    except Exception as exc:
        console.print(f"[red]✗[/red] Failed to initialise: {exc}")
        raise SystemExit(2)
    console.print(f"[green]✓[/green] Initialised driftctl for [bold]{state.project}[/bold]")
    console.print(f"  State file: {root / '.driftctl' / 'state.yaml'}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--skip-tests", is_flag=True, help="Skip running the test suite.")
def validate(skip_tests: bool) -> None:
    """Run environment, git, test-suite, and contract checks."""
    from driftctl.validator import print_result, run_all_checks

    root = Path.cwd()
    try:
        result = run_all_checks(root, run_tests=not skip_tests)
    except Exception as exc:
        console.print(f"[red]✗[/red] Validation error: {exc}")
        raise SystemExit(2)

    print_result(result)
    if not result.ok:
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
        _handle_missing_state()

    if as_json:
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
# handoff
# ---------------------------------------------------------------------------

@cli.command()
def handoff() -> None:
    """Generate a structured prompt block for the next session."""
    from driftctl.handoff import generate_handoff, print_handoff

    root = Path.cwd()
    try:
        text = generate_handoff(root)
    except FileNotFoundError:
        _handle_missing_state()

    print_handoff(text)


# ---------------------------------------------------------------------------
# kickoff
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--component", default=None, help="Focus context on a specific component.")
@click.option("--no-history", is_flag=True, help="Exclude session history from output.")
def kickoff(component: str | None, no_history: bool) -> None:
    """Generate a ready-to-paste context block for starting an agent session."""
    from driftctl.handoff import generate_kickoff, print_kickoff, save_kickoff

    root = Path.cwd()
    try:
        text = generate_kickoff(
            root, component=component, include_history=not no_history
        )
    except FileNotFoundError:
        _handle_missing_state()
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise SystemExit(2)

    save_kickoff(root, text)
    print_kickoff(text)


# ---------------------------------------------------------------------------
# drift
# ---------------------------------------------------------------------------

@cli.command()
def drift() -> None:
    """Compare current codebase against state contracts."""
    from driftctl.drift import detect_drift
    from driftctl.drift import print_result as print_drift_result

    root = Path.cwd()
    try:
        result = detect_drift(root)
    except FileNotFoundError:
        _handle_missing_state()

    print_drift_result(result)
    if not result.ok:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# guard
# ---------------------------------------------------------------------------

@cli.group()
def guard() -> None:
    """Manage guardrail rules."""


@guard.command()
@click.argument("rule")
def add(rule: str) -> None:
    """Add a guardrail rule."""
    from driftctl.guard import add_rule

    root = Path.cwd()
    try:
        rules = add_rule(root, rule)
    except FileNotFoundError:
        _handle_missing_state()

    console.print(f"[green]✓[/green] Guardrail added. Total: {len(rules)}")


@guard.command(name="list")
def list_rules() -> None:
    """List all guardrail rules."""
    from driftctl.guard import list_rules as get_rules
    from driftctl.guard import print_rules

    root = Path.cwd()
    try:
        rules = get_rules(root)
    except FileNotFoundError:
        _handle_missing_state()

    print_rules(rules)


@guard.command(name="test")
def guard_test() -> None:
    """Test guardrail rules against the codebase."""
    from driftctl.guard import check_rules
    from driftctl.guard import print_result as print_guard_result

    root = Path.cwd()
    try:
        result = check_rules(root)
    except FileNotFoundError:
        _handle_missing_state()

    print_guard_result(result)
    if not result.ok:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# checkpoint
# ---------------------------------------------------------------------------

@cli.group()
def checkpoint() -> None:
    """Save and rollback named state snapshots."""


@checkpoint.command()
@click.argument("name")
def save(name: str) -> None:
    """Save a named checkpoint."""
    from driftctl.checkpoint import save_checkpoint

    root = Path.cwd()
    try:
        path = save_checkpoint(root, name)
    except FileNotFoundError:
        _handle_missing_state()
    except ValueError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise SystemExit(2)

    console.print(f"[green]✓[/green] Checkpoint saved: [bold]{name}[/bold]")


@checkpoint.command()
@click.argument("name")
def rollback(name: str) -> None:
    """Rollback to a named checkpoint."""
    from driftctl.checkpoint import rollback_checkpoint

    root = Path.cwd()
    try:
        rollback_checkpoint(root, name)
    except FileNotFoundError:
        console.print(f"[red]✗[/red] Checkpoint not found: {name}")
        raise SystemExit(2)

    console.print(f"[green]✓[/green] Rolled back to checkpoint: [bold]{name}[/bold]")


@checkpoint.command(name="list")
def list_checkpoints_cmd() -> None:
    """List all saved checkpoints."""
    from driftctl.checkpoint import list_checkpoints, print_checkpoints

    root = Path.cwd()
    names = list_checkpoints(root)
    print_checkpoints(names)


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--force", is_flag=True, help="Skip confirmation, always overwrite.")
@click.option("--preview", is_flag=True, help="Show what would be written without writing.")
def sync(force: bool, preview: bool) -> None:
    """Write current project state into CLAUDE.md for automatic session context."""
    from driftctl.sync import sync as run_sync

    root = Path.cwd()
    try:
        run_sync(root, force=force, preview=preview)
    except FileNotFoundError:
        _handle_missing_state()
