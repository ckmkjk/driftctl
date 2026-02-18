"""Guard module for driftctl.

Manages guardrail rules — simple string-based rules that are stored in
the project state and can be tested against the codebase via shell commands
or file-content checks.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from driftctl.state import load_state, save_state

console = Console()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class GuardResult:
    """Result of running guardrail tests."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when every guardrail test passed."""
        return len(self.failed) == 0


# ---------------------------------------------------------------------------
# Rule management
# ---------------------------------------------------------------------------

def add_rule(project_root: Path, rule: str) -> list[str]:
    """Add a guardrail rule to the project state.

    Returns the updated list of guardrails.
    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)
    rule = rule.strip()
    if rule and rule not in state.guardrails:
        state.guardrails.append(rule)
        save_state(project_root, state)
    return list(state.guardrails)


def remove_rule(project_root: Path, rule: str) -> list[str]:
    """Remove a guardrail rule from the project state.

    Returns the updated list of guardrails.
    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)
    rule = rule.strip()
    if rule in state.guardrails:
        state.guardrails.remove(rule)
        save_state(project_root, state)
    return list(state.guardrails)


def list_rules(project_root: Path) -> list[str]:
    """Return all guardrail rules from the project state.

    Raises FileNotFoundError if the state file does not exist.
    """
    state = load_state(project_root)
    return list(state.guardrails)


# ---------------------------------------------------------------------------
# Rule testing
# ---------------------------------------------------------------------------

def _check_single_rule(project_root: Path, rule: str) -> tuple[bool, str]:
    """Test a single guardrail rule against the codebase.

    Rules are interpreted as follows:
    - If the rule starts with ``cmd:`` the remainder is executed as a shell
      command; exit-code 0 means pass.
    - If the rule starts with ``no-file:`` it checks that the glob pattern
      does not match any files.
    - If the rule starts with ``require-file:`` it checks that the path exists.
    - Otherwise the rule is treated as a descriptive/manual rule and always
      passes with a note.

    Returns (passed, message).
    """
    if rule.startswith("cmd:"):
        cmd = rule[4:].strip()
        try:
            result = subprocess.run(
                cmd, shell=True, cwd=str(project_root),
                capture_output=True, timeout=60,
            )
            if result.returncode == 0:
                return True, f"cmd passed: {cmd}"
            return False, f"cmd failed (exit {result.returncode}): {cmd}"
        except subprocess.TimeoutExpired:
            return False, f"cmd timed out: {cmd}"
        except Exception as exc:
            return False, f"cmd error: {exc}"

    if rule.startswith("no-file:"):
        pattern = rule[8:].strip()
        matches = list(project_root.glob(pattern))
        if matches:
            return False, f"Forbidden file(s) found: {', '.join(str(m.relative_to(project_root)) for m in matches)}"
        return True, f"No forbidden files matching '{pattern}'"

    if rule.startswith("require-file:"):
        filepath = rule[13:].strip()
        target = project_root / filepath
        if target.exists():
            return True, f"Required file exists: {filepath}"
        return False, f"Required file missing: {filepath}"

    # Descriptive / manual rule — always passes
    return True, f"Manual rule (not testable): {rule}"


def check_rules(project_root: Path) -> GuardResult:
    """Test all guardrail rules and return an aggregated result.

    Raises FileNotFoundError if the state file does not exist.
    """
    rules = list_rules(project_root)
    result = GuardResult()

    for rule in rules:
        passed, message = _check_single_rule(project_root, rule)
        if passed:
            result.passed.append(message)
        else:
            result.failed.append(message)

    return result


def print_rules(rules: list[str]) -> None:
    """Pretty-print the list of guardrails to the terminal."""
    if not rules:
        console.print("  [dim]No guardrails configured.[/dim]")
        return
    for i, rule in enumerate(rules, 1):
        console.print(f"  {i}. {rule}")


def print_result(result: GuardResult) -> None:
    """Pretty-print a GuardResult to the terminal."""
    for msg in result.passed:
        console.print(f"  [green]✓[/green] {msg}")
    for msg in result.failed:
        console.print(f"  [red]✗[/red] {msg}")

    if result.ok:
        console.print("\n[bold green]All guardrails passed.[/bold green]")
    else:
        console.print(f"\n[bold red]{len(result.failed)} guardrail(s) failed.[/bold red]")
