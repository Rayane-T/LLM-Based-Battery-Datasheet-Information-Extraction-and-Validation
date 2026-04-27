import sys
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import VOLTAGE_RANGES, TEMPERATURE_BOUNDS

class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    HALLUCINATION = "HALLUCINATION"

@dataclass
class ValidationIssue:
    field: str
    value: object
    rule_name: str
    severity: Severity
    message: str
    expected_range: Optional[str] = None

def check_positive_value(spec: dict, field: str, label: str) -> List[ValidationIssue]:
    issues = []
    value = spec.get(field)
    if value is not None and value <= 0:
        issues.append(ValidationIssue(
            field=field,
            value=value,
            rule_name="positive_value",
            severity=Severity.ERROR,
            message=f"{label} must be positive, got {value}",
            expected_range="> 0",
        ))
    return issues

def check_voltage_range(spec: dict) -> List[ValidationIssue]:
    issues = []
    chemistry = spec.get("chemistry")
    nominal_v = spec.get("nominal_voltage_V")
    charge_v = spec.get("charge_voltage_V")
    cutoff_v = spec.get("discharge_cutoff_voltage_V")

    bounds = None
    if chemistry:
        for chem_key, chem_bounds in VOLTAGE_RANGES.items():
            if chem_key.lower() in chemistry.lower() or chemistry.lower() in chem_key.lower():
                bounds = chem_bounds
                break

    if bounds is None:
        bounds = {"min": 1.0, "max": 5.0}

    if nominal_v is not None:
        if nominal_v < bounds["min"] or nominal_v > bounds["max"]:
            issues.append(ValidationIssue(
                field="nominal_voltage_V",
                value=nominal_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=f"voltage {nominal_v}V is out of range for {chemistry}",
                expected_range=f"{bounds['min']}-{bounds['max']} V",
            ))

    if charge_v is not None:
        charge_max = bounds["max"] + 0.15
        if charge_v < bounds["min"] or charge_v > charge_max:
            issues.append(ValidationIssue(
                field="charge_voltage_V",
                value=charge_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=f"charge voltage {charge_v}V is out of range",
                expected_range=f"{bounds['min']}-{charge_max} V",
            ))

    if cutoff_v is not None:
        if cutoff_v < 0 or cutoff_v > bounds["max"]:
            issues.append(ValidationIssue(
                field="discharge_cutoff_voltage_V",
                value=cutoff_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=f"cutoff voltage {cutoff_v}V is out of range",
                expected_range=f"0-{bounds['max']} V",
            ))

    return issues

def check_voltage_ordering(spec: dict) -> List[ValidationIssue]:
    issues = []
    cutoff_v = spec.get("discharge_cutoff_voltage_V")
    nominal_v = spec.get("nominal_voltage_V")
    charge_v = spec.get("charge_voltage_V")

    if cutoff_v is not None and nominal_v is not None:
        if cutoff_v >= nominal_v:
            issues.append(ValidationIssue(
                field="discharge_cutoff_voltage_V",
                value=cutoff_v,
                rule_name="voltage_ordering",
                severity=Severity.ERROR,
                message="cutoff should be < nominal",
            ))

    if nominal_v is not None and charge_v is not None:
        if nominal_v >= charge_v:
            issues.append(ValidationIssue(
                field="nominal_voltage_V",
                value=nominal_v,
                rule_name="voltage_ordering",
                severity=Severity.WARNING,
                message="nominal should be < charge",
            ))

    return issues

def check_temperature_bounds(spec: dict) -> List[ValidationIssue]:
    issues = []
    temp_fields = [
        ("operating_temp_min_C", "Min operating temp", TEMPERATURE_BOUNDS["operating_min"]),
        ("operating_temp_max_C", "Max operating temp", TEMPERATURE_BOUNDS["operating_max"]),
    ]

    for field, label, extreme in temp_fields:
        value = spec.get(field)
        if value is None: continue
        if value < -100 or value > 200:
            issues.append(ValidationIssue(
                field=field,
                value=value,
                rule_name="temperature_bounds",
                severity=Severity.HALLUCINATION,
                message="temperature is physically impossible",
            ))

    op_min = spec.get("operating_temp_min_C")
    op_max = spec.get("operating_temp_max_C")
    if op_min is not None and op_max is not None and op_min >= op_max:
        issues.append(ValidationIssue(
            field="operating_temp_min_C",
            value=op_min,
            rule_name="temperature_ordering",
            severity=Severity.ERROR,
            message="min temp >= max temp",
        ))

    return issues

def check_capacity_consistency(spec: dict) -> List[ValidationIssue]:
    issues = []
    nom_cap = spec.get("nominal_capacity_mAh")
    min_cap = spec.get("min_capacity_mAh")

    if nom_cap is not None and min_cap is not None:
        if min_cap > nom_cap:
            issues.append(ValidationIssue(
                field="min_capacity_mAh",
                value=min_cap,
                rule_name="capacity_consistency",
                severity=Severity.ERROR,
                message="min capacity > nominal capacity",
            ))
    return issues

def check_current_plausibility(spec: dict) -> List[ValidationIssue]:
    issues = []
    nom_cap = spec.get("nominal_capacity_mAh")
    if nom_cap is None: return issues

    current_fields = [
        ("max_charge_current_A", "Max charge current", 10.0),
        ("max_discharge_current_A", "Max discharge current", 30.0),
    ]

    for field, label, max_c_rate in current_fields:
        value = spec.get(field)
        if value is None: continue
        c_rate = value / (nom_cap / 1000)
        if c_rate > max_c_rate:
            issues.append(ValidationIssue(
                field=field,
                value=value,
                rule_name="current_plausibility",
                severity=Severity.WARNING,
                message=f"current {value}A is too high for capacity",
            ))
    return issues

def check_cycle_life(spec: dict) -> List[ValidationIssue]:
    issues = []
    cycle_life = spec.get("cycle_life")
    if cycle_life is not None:
        if cycle_life <= 0:
            issues.append(ValidationIssue(
                field="cycle_life",
                value=cycle_life,
                rule_name="cycle_life_range",
                severity=Severity.ERROR,
                message="cycle life must be positive",
            ))
    return issues

def check_self_discharge(spec: dict) -> List[ValidationIssue]:
    issues = []
    sd_rate = spec.get("self_discharge_rate_percent_per_month")
    if sd_rate is not None:
        if sd_rate < 0 or sd_rate > 30:
            issues.append(ValidationIssue(
                field="self_discharge_rate_percent_per_month",
                value=sd_rate,
                rule_name="self_discharge_range",
                severity=Severity.HALLUCINATION,
                message="self discharge rate is out of range",
            ))
    return issues

ALL_RULES = [
    check_voltage_range,
    check_voltage_ordering,
    check_temperature_bounds,
    check_capacity_consistency,
    check_current_plausibility,
    check_cycle_life,
    check_self_discharge,
]

POSITIVE_VALUE_CHECKS = [
    ("nominal_capacity_mAh", "Nominal capacity"),
    ("min_capacity_mAh", "Minimum capacity"),
    ("internal_resistance_mOhm", "Internal resistance"),
    ("weight_g", "Weight"),
    ("energy_Wh", "Energy"),
]
