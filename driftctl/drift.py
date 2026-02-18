"""Drift detection module for driftctl.

Compares the current codebase against the contracts recorded in the project
state — output-schema files and their MD5 hashes — and reports any drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from driftctl.state import ComponentStatus, compute_contract_hash, load_state

console = Console()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class DriftResult:
    """Aggregated result of drift detection across all components."""

    clean: list[str] = field(default_factory=list)
    drifted: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    no_contract: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when no drift or missing files were detected."""
        return len(self.drifted) == 0 and len(self.missing) == 0


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------

def detect_drift(project_root: Path) -> DriftResult:
    """Compare every component's contract hash against the current file.

    Categories:
    - **clean**: hash matches — no drift.
    - **drifted**: file exists but hash has changed.
    - **missing**: schema file referenced but not found on disk.
    - **no_contract**: component has no output_schema or contract_hash set.

    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)
    result = DriftResult()

    for name, comp in state.components.items():
        if not comp.output_schema or not comp.contract_hash:
            result.no_contract.append(name)
            continue

        current_hash = compute_contract_hash(Path(comp.output_schema))

        if current_hash is None:
            result.missing.append(name)
        elif current_hash == comp.contract_hash:
            result.clean.append(name)
        else:
            result.drifted.append(name)

    return result


def print_result(result: DriftResult) -> None:
    """Pretty-print a DriftResult to the terminal."""
    for name in result.clean:
        console.print(f"  [green]✓[/green] {name} — no drift")
    for name in result.no_contract:
        console.print(f"  [dim]–[/dim] {name} — no contract")
    for name in result.missing:
        console.print(f"  [red]✗[/red] {name} — schema file missing")
    for name in result.drifted:
        console.print(f"  [red]✗[/red] {name} — DRIFTED")

    if result.ok:
        console.print("\n[bold green]No drift detected.[/bold green]")
    else:
        total = len(result.drifted) + len(result.missing)
        console.print(f"\n[bold red]{total} component(s) have drift.[/bold red]")
