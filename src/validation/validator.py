"""
Hallucination detection and validation engine.

Runs all validation rules against extracted battery specifications
and classifies issues by severity.
"""

import logging
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.validation.rules import (
    ValidationIssue,
    Severity,
    ALL_RULES,
    POSITIVE_VALUE_CHECKS,
    check_positive_value,
)

logger = logging.getLogger(__name__)


def validate_specification(spec_data: dict) -> List[ValidationIssue]:
    """
    Run all validation rules against a single battery specification.
    
    Args:
        spec_data: Dictionary of battery specification values.
    
    Returns:
        List of ValidationIssue objects found.
    """
    issues = []

    # Run positive value checks
    for field, label in POSITIVE_VALUE_CHECKS:
        issues.extend(check_positive_value(spec_data, field, label))

    # Run all composite rules
    for rule_fn in ALL_RULES:
        try:
            rule_issues = rule_fn(spec_data)
            issues.extend(rule_issues)
        except Exception as e:
            logger.error(f"Rule {rule_fn.__name__} failed: {e}")

    return issues


def validate_all(extraction_results: dict) -> Dict[str, List[ValidationIssue]]:
    """
    Validate extraction results for all datasheets.
    
    Args:
        extraction_results: Dict mapping filename → spec dict.
    
    Returns:
        Dict mapping filename → list of ValidationIssues.
    """
    all_issues = {}

    for filename, spec_data in extraction_results.items():
        if spec_data is None or (isinstance(spec_data, dict) and "error" in spec_data):
            logger.warning(f"Skipping validation for {filename}: no valid data")
            continue

        issues = validate_specification(spec_data)
        all_issues[filename] = issues

        if issues:
            logger.info(f"{filename}: found {len(issues)} validation issues")
        else:
            logger.info(f"{filename}: all values passed validation ✓")

    return all_issues


def get_validation_summary(all_issues: Dict[str, List[ValidationIssue]]) -> dict:
    """
    Compute summary statistics from validation results.
    
    Args:
        all_issues: Dict mapping filename → list of issues.
    
    Returns:
        Summary dict with counts by severity and file.
    """
    summary = {
        "total_files": len(all_issues),
        "total_issues": 0,
        "files_with_issues": 0,
        "files_clean": 0,
        "by_severity": {s.value: 0 for s in Severity},
        "by_file": {},
    }

    for filename, issues in all_issues.items():
        file_summary = {
            "total": len(issues),
            "by_severity": {s.value: 0 for s in Severity},
        }

        for issue in issues:
            file_summary["by_severity"][issue.severity.value] += 1
            summary["by_severity"][issue.severity.value] += 1

        summary["by_file"][filename] = file_summary
        summary["total_issues"] += len(issues)

        if issues:
            summary["files_with_issues"] += 1
        else:
            summary["files_clean"] += 1

    return summary
