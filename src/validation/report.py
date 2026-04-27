import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.validation.rules import ValidationIssue, Severity
from src.validation.validator import validate_all, get_validation_summary

def print_validation_report(
    all_issues: Dict[str, List[ValidationIssue]],
    title: str = "Validation Report",
) -> None:
    print(f"\n--- {title} ---")
    summary = get_validation_summary(all_issues)
    print(f"Total files: {summary['total_files']}")
    print(f"Total issues: {summary['total_issues']}")

    for filename, issues in all_issues.items():
        if not issues:
            print(f"  {filename}: OK")
            continue
        
        print(f"\nIssues for {filename}:")
        for issue in issues:
            print(f"  [{issue.severity.value}] {issue.field}: {issue.message} (value: {issue.value})")
    print()

def save_validation_report(
    all_issues: Dict[str, List[ValidationIssue]],
    output_path: str,
) -> str:
    output = {}
    for filename, issues in all_issues.items():
        output[filename] = [
            {
                "field": issue.field,
                "value": issue.value,
                "rule": issue.rule_name,
                "severity": issue.severity.value,
                "message": issue.message,
            }
            for issue in issues
        ]

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return output_path
