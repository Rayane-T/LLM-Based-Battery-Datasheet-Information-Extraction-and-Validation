"""
Validation rules for battery specification values.

Defines physical constraints, chemistry-specific bounds, and
cross-field consistency rules to detect hallucinated or invalid values.
"""

import sys
import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config import VOLTAGE_RANGES, TEMPERATURE_BOUNDS


class Severity(str, Enum):
    """Severity level for validation issues."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    HALLUCINATION = "HALLUCINATION"


@dataclass
class ValidationIssue:
    """A single validation issue found in extracted data."""
    field: str
    value: object
    rule_name: str
    severity: Severity
    message: str
    expected_range: Optional[str] = None


# ═══ RULE FUNCTIONS ══════════════════════════════════════════════════

def check_positive_value(spec: dict, field: str, label: str) -> List[ValidationIssue]:
    """Check that a value is positive (if present)."""
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
    """Check that voltages are within plausible ranges for the chemistry."""
    issues = []
    chemistry = spec.get("chemistry")
    nominal_v = spec.get("nominal_voltage_V")
    charge_v = spec.get("charge_voltage_V")
    cutoff_v = spec.get("discharge_cutoff_voltage_V")

    # Determine voltage bounds based on chemistry
    bounds = None
    if chemistry:
        for chem_key, chem_bounds in VOLTAGE_RANGES.items():
            if chem_key.lower() in chemistry.lower() or chemistry.lower() in chem_key.lower():
                bounds = chem_bounds
                break

    if bounds is None:
        # Use generic wide bounds
        bounds = {"min": 1.0, "max": 5.0}

    # Check nominal voltage
    if nominal_v is not None:
        if nominal_v < bounds["min"] or nominal_v > bounds["max"]:
            issues.append(ValidationIssue(
                field="nominal_voltage_V",
                value=nominal_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=(
                    f"Nominal voltage {nominal_v}V is outside plausible range "
                    f"for {chemistry or 'unknown'} chemistry"
                ),
                expected_range=f"{bounds['min']}-{bounds['max']} V",
            ))

    # Check charge voltage
    if charge_v is not None:
        charge_max = bounds["max"] + 0.15  # Small margin for charge voltage
        if charge_v < bounds["min"] or charge_v > charge_max:
            issues.append(ValidationIssue(
                field="charge_voltage_V",
                value=charge_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=(
                    f"Charge voltage {charge_v}V is outside plausible range "
                    f"for {chemistry or 'unknown'} chemistry"
                ),
                expected_range=f"{bounds['min']}-{charge_max} V",
            ))

    # Check cutoff voltage
    if cutoff_v is not None:
        if cutoff_v < 0 or cutoff_v > bounds["max"]:
            issues.append(ValidationIssue(
                field="discharge_cutoff_voltage_V",
                value=cutoff_v,
                rule_name="voltage_range",
                severity=Severity.HALLUCINATION,
                message=f"Discharge cutoff voltage {cutoff_v}V is implausible",
                expected_range=f"0-{bounds['max']} V",
            ))

    return issues


def check_voltage_ordering(spec: dict) -> List[ValidationIssue]:
    """Check that discharge_cutoff < nominal < charge voltage."""
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
                message=(
                    f"Discharge cutoff ({cutoff_v}V) should be less than "
                    f"nominal voltage ({nominal_v}V)"
                ),
            ))

    if nominal_v is not None and charge_v is not None:
        if nominal_v >= charge_v:
            issues.append(ValidationIssue(
                field="nominal_voltage_V",
                value=nominal_v,
                rule_name="voltage_ordering",
                severity=Severity.WARNING,
                message=(
                    f"Nominal voltage ({nominal_v}V) should typically be less than "
                    f"charge voltage ({charge_v}V)"
                ),
            ))

    if cutoff_v is not None and charge_v is not None:
        if cutoff_v >= charge_v:
            issues.append(ValidationIssue(
                field="discharge_cutoff_voltage_V",
                value=cutoff_v,
                rule_name="voltage_ordering",
                severity=Severity.ERROR,
                message=(
                    f"Discharge cutoff ({cutoff_v}V) must be less than "
                    f"charge voltage ({charge_v}V)"
                ),
            ))

    return issues


def check_temperature_bounds(spec: dict) -> List[ValidationIssue]:
    """Check that temperature values are physically plausible."""
    issues = []

    temp_fields = [
        ("operating_temp_min_C", "Min operating temp", TEMPERATURE_BOUNDS["operating_min"]),
        ("operating_temp_max_C", "Max operating temp", TEMPERATURE_BOUNDS["operating_max"]),
        ("storage_temp_min_C", "Min storage temp", TEMPERATURE_BOUNDS["storage_min"]),
        ("storage_temp_max_C", "Max storage temp", TEMPERATURE_BOUNDS["storage_max"]),
    ]

    for field, label, extreme in temp_fields:
        value = spec.get(field)
        if value is None:
            continue

        # Check absolute physical bounds
        if value < -100 or value > 200:
            issues.append(ValidationIssue(
                field=field,
                value=value,
                rule_name="temperature_bounds",
                severity=Severity.HALLUCINATION,
                message=f"{label} ({value}°C) is physically implausible",
                expected_range="-100 to 200 °C",
            ))

    # Check min < max ordering
    op_min = spec.get("operating_temp_min_C")
    op_max = spec.get("operating_temp_max_C")
    if op_min is not None and op_max is not None and op_min >= op_max:
        issues.append(ValidationIssue(
            field="operating_temp_min_C",
            value=op_min,
            rule_name="temperature_ordering",
            severity=Severity.ERROR,
            message=(
                f"Min operating temp ({op_min}°C) must be less than "
                f"max operating temp ({op_max}°C)"
            ),
        ))

    st_min = spec.get("storage_temp_min_C")
    st_max = spec.get("storage_temp_max_C")
    if st_min is not None and st_max is not None and st_min >= st_max:
        issues.append(ValidationIssue(
            field="storage_temp_min_C",
            value=st_min,
            rule_name="temperature_ordering",
            severity=Severity.ERROR,
            message=(
                f"Min storage temp ({st_min}°C) must be less than "
                f"max storage temp ({st_max}°C)"
            ),
        ))

    return issues


def check_capacity_consistency(spec: dict) -> List[ValidationIssue]:
    """Check capacity-related consistency."""
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
                message=(
                    f"Minimum capacity ({min_cap} mAh) cannot exceed "
                    f"nominal capacity ({nom_cap} mAh)"
                ),
            ))

    # Check energy vs voltage*capacity consistency
    energy = spec.get("energy_Wh")
    if energy is not None and nom_cap is not None:
        nominal_v = spec.get("nominal_voltage_V")
        if nominal_v is not None:
            expected_energy = nominal_v * nom_cap / 1000  # mAh to Ah
            ratio = energy / expected_energy if expected_energy > 0 else 999
            if ratio < 0.5 or ratio > 2.0:
                issues.append(ValidationIssue(
                    field="energy_Wh",
                    value=energy,
                    rule_name="energy_consistency",
                    severity=Severity.WARNING,
                    message=(
                        f"Energy ({energy} Wh) seems inconsistent with "
                        f"voltage ({nominal_v}V) × capacity ({nom_cap} mAh) "
                        f"= {expected_energy:.1f} Wh expected"
                    ),
                ))

    return issues


def check_current_plausibility(spec: dict) -> List[ValidationIssue]:
    """Check that current values are plausible relative to capacity."""
    issues = []
    nom_cap = spec.get("nominal_capacity_mAh")

    if nom_cap is None:
        return issues

    current_fields = [
        ("max_charge_current_A", "Max charge current", 10.0),  # 10C max reasonable
        ("max_discharge_current_A", "Max discharge current", 30.0),  # 30C max reasonable
        ("standard_charge_current_A", "Standard charge current", 2.0),  # 2C max
        ("standard_discharge_current_A", "Standard discharge current", 5.0),  # 5C max
    ]

    for field, label, max_c_rate in current_fields:
        value = spec.get(field)
        if value is None:
            continue

        c_rate = value / (nom_cap / 1000)  # Convert mAh to Ah
        if c_rate > max_c_rate:
            issues.append(ValidationIssue(
                field=field,
                value=value,
                rule_name="current_plausibility",
                severity=Severity.WARNING,
                message=(
                    f"{label} ({value}A = {c_rate:.1f}C) exceeds typical maximum "
                    f"of {max_c_rate}C for this capacity"
                ),
                expected_range=f"≤ {max_c_rate * nom_cap / 1000:.2f} A ({max_c_rate}C)",
            ))

    # Standard should not exceed max
    std_charge = spec.get("standard_charge_current_A")
    max_charge = spec.get("max_charge_current_A")
    if std_charge is not None and max_charge is not None:
        if std_charge > max_charge:
            issues.append(ValidationIssue(
                field="standard_charge_current_A",
                value=std_charge,
                rule_name="current_ordering",
                severity=Severity.ERROR,
                message=(
                    f"Standard charge current ({std_charge}A) exceeds "
                    f"max charge current ({max_charge}A)"
                ),
            ))

    return issues


def check_cycle_life(spec: dict) -> List[ValidationIssue]:
    """Check that cycle life is within plausible range."""
    issues = []
    cycle_life = spec.get("cycle_life")

    if cycle_life is not None:
        if cycle_life <= 0:
            issues.append(ValidationIssue(
                field="cycle_life",
                value=cycle_life,
                rule_name="cycle_life_range",
                severity=Severity.ERROR,
                message=f"Cycle life must be positive, got {cycle_life}",
            ))
        elif cycle_life > 20000:
            issues.append(ValidationIssue(
                field="cycle_life",
                value=cycle_life,
                rule_name="cycle_life_range",
                severity=Severity.HALLUCINATION,
                message=f"Cycle life ({cycle_life}) seems implausibly high",
                expected_range="100-20000 cycles",
            ))

    return issues


def check_self_discharge(spec: dict) -> List[ValidationIssue]:
    """Check self-discharge rate is within plausible range."""
    issues = []
    sd_rate = spec.get("self_discharge_rate_percent_per_month")

    if sd_rate is not None:
        if sd_rate < 0:
            issues.append(ValidationIssue(
                field="self_discharge_rate_percent_per_month",
                value=sd_rate,
                rule_name="self_discharge_range",
                severity=Severity.ERROR,
                message=f"Self-discharge rate cannot be negative: {sd_rate}%",
            ))
        elif sd_rate > 30:
            issues.append(ValidationIssue(
                field="self_discharge_rate_percent_per_month",
                value=sd_rate,
                rule_name="self_discharge_range",
                severity=Severity.HALLUCINATION,
                message=f"Self-discharge rate ({sd_rate}%/month) seems implausibly high",
                expected_range="0-30 %/month",
            ))

    return issues


# ═══ ALL RULES ═══════════════════════════════════════════════════════

ALL_RULES: List[Callable] = [
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
