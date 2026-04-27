import logging
import sys
import os

from rdflib import Graph

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.knowledge_graph.ontology import BATT, INST, UNIT

logger = logging.getLogger(__name__)


def query_all_batteries(graph: Graph) -> list:
    query = """
    PREFIX batt: <http://battery-ontology.org/schema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?battery ?model ?manufacturer ?chemistry
    WHERE {
        ?battery a batt:Battery .
        ?battery batt:batteryModel ?model .
        OPTIONAL {
            ?battery batt:hasManufacturer ?mfr .
            ?mfr batt:manufacturerName ?manufacturer .
        }
        OPTIONAL {
            ?battery batt:hasChemistry ?chem .
            ?chem batt:chemistryType ?chemistry .
        }
    }
    ORDER BY ?model
    """
    results = []
    for row in graph.query(query):
        results.append({
            "battery": str(row.battery),
            "model": str(row.model),
            "manufacturer": str(row.manufacturer) if row.manufacturer else None,
            "chemistry": str(row.chemistry) if row.chemistry else None,
        })
    return results


def query_battery_specs(graph: Graph, model_name: str) -> list:
    query = """
    PREFIX batt: <http://battery-ontology.org/schema#>

    SELECT ?specName ?value ?unitSymbol ?specType
    WHERE {
        ?battery a batt:Battery .
        ?battery batt:batteryModel ?model .
        FILTER(STR(?model) = "%s")
        ?battery batt:hasSpecification ?spec .
        ?spec batt:specName ?specName .
        ?spec batt:hasValue ?value .
        ?spec batt:hasUnit ?unit .
        ?unit batt:unitSymbol ?unitSymbol .
        ?spec a ?specType .
        FILTER(?specType != <http://battery-ontology.org/schema#Specification>)
    }
    ORDER BY ?specName
    """ % model_name

    results = []
    for row in graph.query(query):
        results.append({
            "spec_name": str(row.specName),
            "value": float(row.value),
            "unit": str(row.unitSymbol),
            "type": str(row.specType).split("#")[-1],
        })
    return results


def query_batteries_by_voltage_range(graph: Graph, min_v: float, max_v: float) -> list:
    query = """
    PREFIX batt: <http://battery-ontology.org/schema#>

    SELECT ?model ?voltage
    WHERE {
        ?battery a batt:Battery .
        ?battery batt:batteryModel ?model .
        ?battery batt:hasSpecification ?spec .
        ?spec batt:specName "Nominal Voltage" .
        ?spec batt:hasValue ?voltage .
        FILTER(?voltage >= %f && ?voltage <= %f)
    }
    ORDER BY ?voltage
    """ % (min_v, max_v)

    results = []
    for row in graph.query(query):
        results.append({
            "model": str(row.model),
            "voltage": float(row.voltage),
        })
    return results


def query_batteries_by_chemistry(graph: Graph, chemistry: str) -> list:
    query = """
    PREFIX batt: <http://battery-ontology.org/schema#>

    SELECT ?model ?manufacturer
    WHERE {
        ?battery a batt:Battery .
        ?battery batt:batteryModel ?model .
        ?battery batt:hasChemistry ?chem .
        ?chem batt:chemistryType ?chemistry .
        FILTER(STR(?chemistry) = "%s")
        OPTIONAL {
            ?battery batt:hasManufacturer ?mfr .
            ?mfr batt:manufacturerName ?manufacturer .
        }
    }
    """ % chemistry

    results = []
    for row in graph.query(query):
        results.append({
            "model": str(row.model),
            "manufacturer": str(row.manufacturer) if row.manufacturer else None,
        })
    return results


def query_graph_statistics(graph: Graph) -> dict:
    stats = {
        "total_triples": len(graph),
    }

    q = """
    PREFIX batt: <http://battery-ontology.org/schema#>
    SELECT (COUNT(?b) AS ?cnt) WHERE { ?b a batt:Battery }
    """
    for row in graph.query(q):
        stats["battery_count"] = int(row.cnt)

    q = """
    PREFIX batt: <http://battery-ontology.org/schema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT (COUNT(?s) AS ?cnt) WHERE { ?s a ?type . ?type rdfs:subClassOf batt:Specification }
    """
    for row in graph.query(q):
        stats["specification_count"] = int(row.cnt)

    q = """
    PREFIX batt: <http://battery-ontology.org/schema#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?type (COUNT(?s) AS ?cnt)
    WHERE {
        ?s a ?type .
        ?type rdfs:subClassOf batt:Specification .
    }
    GROUP BY ?type
    """
    stats["specs_by_type"] = {}
    for row in graph.query(q):
        type_name = str(row.type).split("#")[-1]
        stats["specs_by_type"][type_name] = int(row.cnt)

    return stats


def print_graph_summary(graph: Graph) -> None:
    stats = query_graph_statistics(graph)
    batteries = query_all_batteries(graph)

    print(f"\n{'='*60}")
    print(f"Knowledge Graph Summary")
    print(f"{'='*60}")
    print(f"Total triples: {stats['total_triples']}")
    print(f"Batteries: {stats.get('battery_count', 0)}")
    print(f"Specifications: {stats.get('specification_count', 0)}")

    if stats.get("specs_by_type"):
        print(f"\nSpecs by type:")
        for type_name, count in stats["specs_by_type"].items():
            print(f"  {type_name}: {count}")

    print(f"\nBatteries in graph:")
    for b in batteries:
        chem = f" ({b['chemistry']})" if b['chemistry'] else ""
        mfr = f" by {b['manufacturer']}" if b['manufacturer'] else ""
        print(f"  - {b['model']}{chem}{mfr}")

    print()
