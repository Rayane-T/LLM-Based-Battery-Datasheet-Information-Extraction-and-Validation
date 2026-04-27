"""
Validation report generation with rich formatting.

Produces human-readable reports of validation results,
highlighting hallucinations and inconsistencies.
"""

import json
import os
import sys
from typing import Dict, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.validation.rules import ValidationIssue, Severity
from src.validation.validator import validate_all, get_validation_summary

console = Console()

# Severity styling
SEVERITY_STYLE = {
    Severity.INFO: ("ℹ️", "blue"),
    Severity.WARNING: ("⚠️", "yellow"),
    Severity.ERROR: ("❌", "red"),
    Severity.HALLUCINATION: ("🔮", "bold magenta"),
}


def print_validation_report(
    all_issues: Dict[str, List[ValidationIssue]],
    title: str = "Validation Report",
) -> None:
    """Print a formatted validation report for all files."""
    summary = get_validation_summary(all_issues)

    console.print(f"\n{'='*70}")
    console.print(f"[bold cyan]🔍 {title}[/bold cyan]")
    console.print(f"{'='*70}\n")

    # Overall summary
    summary_text = Text()
    summary_text.append(f"  Files analyzed: {summary['total_files']}\n", style="bold")
    summary_text.append(f"  Files clean:    {summary['files_clean']}\n", style="green")
    summary_text.append(f"  Files flagged:  {summary['files_with_issues']}\n",
                        style="yellow" if summary['files_with_issues'] > 0 else "green")
    summary_text.append(f"  Total issues:   {summary['total_issues']}\n\n",
                        style="red" if summary['total_issues'] > 0 else "green")

    for sev in Severity:
        count = summary["by_severity"][sev.value]
        icon, color = SEVERITY_STYLE[sev]
        if count > 0:
            summary_text.append(f"  {icon} {sev.value}: {count}\n", style=color)

    console.print(Panel(summary_text, title="📋 Summary", border_style="cyan"))

    # Per-file details
    for filename, issues in all_issues.items():
        if not issues:
            console.print(f"\n[green]✅ {filename}: No issues found[/green]")
            continue

        table = Table(
            title=f"🔍 Issues: {filename}",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Sev", width=4)
        table.add_column("Field", style="white", min_width=30)
        table.add_column("Value", style="yellow", min_width=10)
        table.add_column("Message", style="white", min_width=40)
        table.add_column("Expected", style="dim", min_width=15)

        for issue in sorted(issues, key=lambda x: list(Severity).index(x.severity)):
            icon, color = SEVERITY_STYLE[issue.severity]
            table.add_row(
                icon,
                issue.field,
                str(issue.value),
                issue.message,
                issue.expected_range or "—",
                style=color if issue.severity in (Severity.ERROR, Severity.HALLUCINATION) else None,
            )

        console.print(table)
    console.print()


def save_validation_report(
    all_issues: Dict[str, List[ValidationIssue]],
    output_path: str,
) -> str:
    """Save validation results to a JSON file."""
    output = {}
    for filename, issues in all_issues.items():
        output[filename] = [
            {
                "field": issue.field,
                "value": issue.value,
                "rule": issue.rule_name,
                "severity": issue.severity.value,
                "message": issue.message,
                "expected_range": issue.expected_range,
            }
            for issue in issues
        ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return output_path


if __name__ == "__main__":
    # Test with ground truth data
    gt_path = os.path.join(os.path.dirname(__file__), "..", "..", "evaluation", "ground_truth.json")
    with open(gt_path) as f:
        gt_data = json.load(f)

    all_issues = validate_all(gt_data)
    print_validation_report(all_issues, "Ground Truth Validation")
