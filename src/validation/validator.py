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
    issues = []

    for field, label in POSITIVE_VALUE_CHECKS:
        issues.extend(check_positive_value(spec_data, field, label))

    for rule_fn in ALL_RULES:
        try:
            issues.extend(rule_fn(spec_data))
        except Exception as e:
            logger.error(f"rule failed: {e}")

    return issues

def validate_all(extraction_results: dict) -> Dict[str, List[ValidationIssue]]:
    all_issues = {}
    for filename, spec_data in extraction_results.items():
        if spec_data is None or "error" in spec_data:
            continue
        issues = validate_specification(spec_data)
        all_issues[filename] = issues
    return all_issues

def get_validation_summary(all_issues: Dict[str, List[ValidationIssue]]) -> dict:
    summary = {
        "total_files": len(all_issues),
        "total_issues": 0,
        "by_severity": {s.value: 0 for s in Severity},
    }

    for filename, issues in all_issues.items():
        summary["total_issues"] += len(issues)
        for issue in issues:
            summary["by_severity"][issue.severity.value] += 1

    return summary
