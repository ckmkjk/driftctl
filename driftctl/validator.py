"""Validator module for driftctl.

Implements the ``driftctl validate`` command logic — environment checks,
git status, test-suite execution, and contract-hash verification.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from driftctl.state import ComponentStatus, compute_contract_hash, load_state

console = Console()


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Aggregated result of all validation checks."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True when every check passed."""
        return len(self.failed) == 0


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_state_file(project_root: Path) -> tuple[bool, str]:
    """Verify that .driftctl/state.yaml exists and is loadable.

    Returns (passed, message).
    """
    try:
        load_state(project_root)
        return True, "State file is valid"
    except FileNotFoundError:
        return False, "State file not found — run driftctl init"
    except Exception as exc:
        return False, f"State file is corrupt: {exc}"


def check_git(project_root: Path) -> tuple[bool, str]:
    """Verify that the project root is inside a git repository.

    Returns (passed, message).
    """
    git_dir = project_root / ".git"
    if git_dir.is_dir():
        return True, "Git repository detected"
    return False, "Not a git repository"


def check_test_command(project_root: Path) -> tuple[bool, str]:
    """Run the configured test command and report pass/fail.

    Returns (passed, message).
    """
    try:
        state = load_state(project_root)
    except FileNotFoundError:
        return False, "Cannot run tests — no state file"

    if not state.test_command:
        return False, "No test command configured"

    try:
        result = subprocess.run(
            state.test_command,
            shell=True,
            cwd=str(project_root),
            capture_output=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, "Test suite passed"
        return False, f"Test suite failed (exit code {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, "Test suite timed out (300s)"
    except Exception as exc:
        return False, f"Test suite error: {exc}"


def check_contracts(project_root: Path) -> tuple[bool, str]:
    """Verify that contract hashes still match their output-schema files.

    Returns (passed, message).
    """
    try:
        state = load_state(project_root)
    except FileNotFoundError:
        return False, "Cannot check contracts — no state file"

    mismatches: list[str] = []
    checked = 0

    for name, comp in state.components.items():
        if comp.output_schema and comp.contract_hash:
            checked += 1
            current_hash = compute_contract_hash(Path(comp.output_schema))
            if current_hash is None:
                mismatches.append(f"{name}: schema file missing ({comp.output_schema})")
            elif current_hash != comp.contract_hash:
                mismatches.append(f"{name}: hash mismatch")

    if mismatches:
        detail = "; ".join(mismatches)
        return False, f"Contract drift detected — {detail}"
    if checked == 0:
        return True, "No contracts to verify"
    return True, f"All {checked} contract(s) valid"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_all_checks(project_root: Path, *, run_tests: bool = True) -> ValidationResult:
    """Execute every validation check and return an aggregated result.

    Set *run_tests* to False to skip the (potentially slow) test-suite
    execution — useful for unit-testing the validator itself.
    """
    result = ValidationResult()

    checks = [
        check_state_file(project_root),
        check_git(project_root),
    ]
    if run_tests:
        checks.append(check_test_command(project_root))
    checks.append(check_contracts(project_root))

    for passed, message in checks:
        if passed:
            result.passed.append(message)
        else:
            result.failed.append(message)

    return result


def print_result(result: ValidationResult) -> None:
    """Pretty-print a ValidationResult to the terminal."""
    for msg in result.passed:
        console.print(f"  [green]✓[/green] {msg}")
    for msg in result.failed:
        console.print(f"  [red]✗[/red] {msg}")

    if result.ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print(f"\n[bold red]{len(result.failed)} check(s) failed.[/bold red]")
