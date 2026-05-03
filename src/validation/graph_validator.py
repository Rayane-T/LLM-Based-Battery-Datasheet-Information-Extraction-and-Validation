"""
Graph-based validation using SPARQL queries on the RDF knowledge graph.

Implements Level 3 requirement: "Use ontology constraints and graph-based
validation rules to verify extracted values."
"""

import logging
import os
import sys
from typing import List

from rdflib import Graph

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.validation.rules import ValidationIssue, Severity

logger = logging.getLogger(__name__)

PREFIXES = """
PREFIX batt: <http://battery-ontology.org/schema#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


def check_chemistry_voltage_consistency_sparql(graph: Graph) -> List[ValidationIssue]:
    """Detect chemistry/voltage mismatches using SPARQL and ontology knowledge.
    
    A battery with nominal voltage ~3.2V and charge voltage ~3.65V is
    characteristic of LiFePO4, not Li-ion. This rule catches such mismatches.
    """
    issues = []

    query = PREFIXES + """
    SELECT ?model ?chemistry ?nomV ?chargeV WHERE {
        ?b a batt:Battery ; batt:batteryModel ?model .
        ?b batt:hasChemistry ?c . ?c batt:chemistryType ?chemistry .
        ?b batt:hasSpecification ?s1 .
        ?s1 batt:specName "Nominal Voltage" ; batt:hasValue ?nomV .
        ?b batt:hasSpecification ?s2 .
        ?s2 batt:specName "Charge Voltage" ; batt:hasValue ?chargeV .
        FILTER(
            ?chemistry != "LiFePO4"
            && xsd:float(?nomV) >= 3.0 && xsd:float(?nomV) <= 3.4
            && xsd:float(?chargeV) >= 3.5 && xsd:float(?chargeV) <= 3.75
        )
    }
    """
    for row in graph.query(query):
        issues.append(ValidationIssue(
            field="chemistry",
            value=str(row.chemistry),
            rule_name="sparql_chemistry_voltage_mismatch",
            severity=Severity.HALLUCINATION,
            message=(
                f"[SPARQL] {row.model}: chemistry '{row.chemistry}' is inconsistent "
                f"with voltage profile (nominal={row.nomV}V, charge={row.chargeV}V) "
                f"— this profile is characteristic of LiFePO4"
            ),
        ))

    return issues


def check_voltage_ordering_sparql(graph: Graph) -> List[ValidationIssue]:
    """Detect voltage ordering violations: cutoff < nominal < charge."""
    issues = []

    # cutoff >= nominal
    query = PREFIXES + """
    SELECT ?model ?cutoffV ?nomV WHERE {
        ?b a batt:Battery ; batt:batteryModel ?model .
        ?b batt:hasSpecification ?s1 .
        ?s1 batt:specName "Discharge Cutoff Voltage" ; batt:hasValue ?cutoffV .
        ?b batt:hasSpecification ?s2 .
        ?s2 batt:specName "Nominal Voltage" ; batt:hasValue ?nomV .
        FILTER(xsd:float(?cutoffV) >= xsd:float(?nomV))
    }
    """
    for row in graph.query(query):
        issues.append(ValidationIssue(
            field="discharge_cutoff_voltage_V",
            value=float(row.cutoffV),
            rule_name="sparql_voltage_ordering",
            severity=Severity.ERROR,
            message=f"[SPARQL] {row.model}: cutoff ({row.cutoffV}V) >= nominal ({row.nomV}V)",
        ))

    # nominal >= charge
    query = PREFIXES + """
    SELECT ?model ?nomV ?chargeV WHERE {
        ?b a batt:Battery ; batt:batteryModel ?model .
        ?b batt:hasSpecification ?s1 .
        ?s1 batt:specName "Nominal Voltage" ; batt:hasValue ?nomV .
        ?b batt:hasSpecification ?s2 .
        ?s2 batt:specName "Charge Voltage" ; batt:hasValue ?chargeV .
        FILTER(xsd:float(?nomV) >= xsd:float(?chargeV))
    }
    """
    for row in graph.query(query):
        issues.append(ValidationIssue(
            field="nominal_voltage_V",
            value=float(row.nomV),
            rule_name="sparql_voltage_ordering",
            severity=Severity.WARNING,
            message=f"[SPARQL] {row.model}: nominal ({row.nomV}V) >= charge ({row.chargeV}V)",
        ))

    return issues


def check_temperature_ordering_sparql(graph: Graph) -> List[ValidationIssue]:
    """Detect temperature ordering violations via SPARQL."""
    issues = []

    checks = [
        ("Minimum Operating Temperature", "Maximum Operating Temperature", "operating"),
        ("Minimum Storage Temperature", "Maximum Storage Temperature", "storage"),
    ]

    for min_name, max_name, label in checks:
        query = PREFIXES + """
        SELECT ?model ?minT ?maxT WHERE {
            ?b a batt:Battery ; batt:batteryModel ?model .
            ?b batt:hasSpecification ?s1 .
            ?s1 batt:specName "%s" ; batt:hasValue ?minT .
            ?b batt:hasSpecification ?s2 .
            ?s2 batt:specName "%s" ; batt:hasValue ?maxT .
            FILTER(xsd:float(?minT) >= xsd:float(?maxT))
        }
        """ % (min_name, max_name)

        for row in graph.query(query):
            issues.append(ValidationIssue(
                field=f"{label}_temp_min_C",
                value=float(row.minT),
                rule_name="sparql_temperature_ordering",
                severity=Severity.ERROR,
                message=f"[SPARQL] {row.model}: min {label} temp ({row.minT}°C) >= max ({row.maxT}°C)",
            ))

    return issues


def check_energy_consistency_sparql(graph: Graph) -> List[ValidationIssue]:
    """Check energy ≈ voltage × capacity via SPARQL + computation."""
    issues = []

    query = PREFIXES + """
    SELECT ?model ?nomV ?capacity ?energy WHERE {
        ?b a batt:Battery ; batt:batteryModel ?model .
        ?b batt:hasSpecification ?s1 .
        ?s1 batt:specName "Nominal Voltage" ; batt:hasValue ?nomV .
        ?b batt:hasSpecification ?s2 .
        ?s2 batt:specName "Nominal Capacity" ; batt:hasValue ?capacity .
        ?b batt:hasSpecification ?s3 .
        ?s3 batt:specName "Energy" ; batt:hasValue ?energy .
    }
    """
    for row in graph.query(query):
        voltage = float(row.nomV)
        capacity_ah = float(row.capacity) / 1000.0
        energy = float(row.energy)
        expected = voltage * capacity_ah

        if expected > 0:
            error = abs(energy - expected) / expected
            if error > 0.15:
                issues.append(ValidationIssue(
                    field="energy_Wh",
                    value=energy,
                    rule_name="sparql_energy_consistency",
                    severity=Severity.WARNING,
                    message=(
                        f"[SPARQL] {row.model}: energy ({energy} Wh) doesn't match "
                        f"V × Ah = {voltage} × {capacity_ah:.2f} = {expected:.2f} Wh "
                        f"(error: {error:.0%})"
                    ),
                ))

    return issues


def check_current_ordering_sparql(graph: Graph) -> List[ValidationIssue]:
    """Detect standard current > max current via SPARQL."""
    issues = []

    checks = [
        ("Standard Charge Current", "Maximum Charge Current", "charge"),
        ("Standard Discharge Current", "Maximum Discharge Current", "discharge"),
    ]

    for std_name, max_name, label in checks:
        query = PREFIXES + """
        SELECT ?model ?stdI ?maxI WHERE {
            ?b a batt:Battery ; batt:batteryModel ?model .
            ?b batt:hasSpecification ?s1 .
            ?s1 batt:specName "%s" ; batt:hasValue ?stdI .
            ?b batt:hasSpecification ?s2 .
            ?s2 batt:specName "%s" ; batt:hasValue ?maxI .
            FILTER(xsd:float(?stdI) > xsd:float(?maxI))
        }
        """ % (std_name, max_name)

        for row in graph.query(query):
            issues.append(ValidationIssue(
                field=f"standard_{label}_current_A",
                value=float(row.stdI),
                rule_name="sparql_current_ordering",
                severity=Severity.ERROR,
                message=f"[SPARQL] {row.model}: standard {label} ({row.stdI}A) > max ({row.maxI}A)",
            ))

    return issues


def check_capacity_consistency_sparql(graph: Graph) -> List[ValidationIssue]:
    """Detect min capacity > nominal capacity via SPARQL."""
    issues = []

    query = PREFIXES + """
    SELECT ?model ?minCap ?nomCap WHERE {
        ?b a batt:Battery ; batt:batteryModel ?model .
        ?b batt:hasSpecification ?s1 .
        ?s1 batt:specName "Minimum Capacity" ; batt:hasValue ?minCap .
        ?b batt:hasSpecification ?s2 .
        ?s2 batt:specName "Nominal Capacity" ; batt:hasValue ?nomCap .
        FILTER(xsd:float(?minCap) > xsd:float(?nomCap))
    }
    """
    for row in graph.query(query):
        issues.append(ValidationIssue(
            field="min_capacity_mAh",
            value=float(row.minCap),
            rule_name="sparql_capacity_consistency",
            severity=Severity.ERROR,
            message=f"[SPARQL] {row.model}: min capacity ({row.minCap} mAh) > nominal ({row.nomCap} mAh)",
        ))

    return issues


ALL_GRAPH_RULES = [
    check_chemistry_voltage_consistency_sparql,
    check_voltage_ordering_sparql,
    check_temperature_ordering_sparql,
    check_energy_consistency_sparql,
    check_current_ordering_sparql,
    check_capacity_consistency_sparql,
]


def validate_graph(graph: Graph) -> List[ValidationIssue]:
    """Run all SPARQL-based validation rules on the knowledge graph."""
    all_issues = []
    for rule_fn in ALL_GRAPH_RULES:
        try:
            issues = rule_fn(graph)
            all_issues.extend(issues)
            if issues:
                logger.info(f"  {rule_fn.__name__}: {len(issues)} issue(s)")
        except Exception as e:
            logger.error(f"  SPARQL rule {rule_fn.__name__} failed: {e}")
    return all_issues
