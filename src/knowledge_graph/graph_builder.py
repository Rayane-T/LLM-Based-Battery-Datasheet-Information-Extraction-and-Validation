import json
import logging
import os
import re
import sys
from rdflib import Graph, Literal, URIRef, RDF, RDFS, XSD

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.knowledge_graph.ontology import BATT, INST, UNIT, create_ontology, FIELD_TO_SPEC

logger = logging.getLogger(__name__)


def sanitize_uri(name: str) -> str:
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    return sanitized


def add_battery_to_graph(graph: Graph, spec_data: dict, source_filename: str) -> URIRef:
    model_name = spec_data.get("battery_model", "Unknown")
    battery_id = sanitize_uri(model_name)
    battery_uri = INST[f"battery_{battery_id}"]

    graph.add((battery_uri, RDF.type, BATT.Battery))
    graph.add((battery_uri, BATT.batteryModel, Literal(model_name)))
    graph.add((battery_uri, RDFS.label, Literal(f"Battery: {model_name}")))
    graph.add((battery_uri, RDFS.comment, Literal(f"Source: {source_filename}")))

    manufacturer = spec_data.get("manufacturer")
    if manufacturer:
        mfr_uri = INST[f"manufacturer_{sanitize_uri(manufacturer)}"]
        graph.add((mfr_uri, RDF.type, BATT.Manufacturer))
        graph.add((mfr_uri, BATT.manufacturerName, Literal(manufacturer)))
        graph.add((battery_uri, BATT.hasManufacturer, mfr_uri))

    chemistry = spec_data.get("chemistry")
    if chemistry:
        chem_uri = INST[sanitize_uri(chemistry)]
        graph.add((chem_uri, RDF.type, BATT.Chemistry))
        graph.add((chem_uri, BATT.chemistryType, Literal(chemistry)))
        graph.add((battery_uri, BATT.hasChemistry, chem_uri))

    for field_name, mapping in FIELD_TO_SPEC.items():
        value = spec_data.get(field_name)
        if value is None:
            continue

        spec_id = f"{battery_id}_{sanitize_uri(mapping['name'])}"
        spec_uri = INST[f"spec_{spec_id}"]
        spec_class = getattr(BATT, mapping["class"])

        graph.add((spec_uri, RDF.type, spec_class))
        graph.add((spec_uri, BATT.specName, Literal(mapping["name"])))

        if isinstance(value, int):
            graph.add((spec_uri, BATT.hasValue, Literal(value, datatype=XSD.integer)))
        else:
            graph.add((spec_uri, BATT.hasValue, Literal(float(value), datatype=XSD.float)))

        graph.add((spec_uri, BATT.hasUnit, UNIT[mapping["unit"]]))
        graph.add((battery_uri, BATT.hasSpecification, spec_uri))

    return battery_uri


def build_knowledge_graph(extraction_results: dict) -> Graph:
    graph = create_ontology()
    for filename, spec_data in extraction_results.items():
        if spec_data is None or (isinstance(spec_data, dict) and "error" in spec_data):
            continue
        add_battery_to_graph(graph, spec_data, filename)
    return graph


def save_graph(graph: Graph, output_path: str, format: str = "turtle") -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    graph.serialize(destination=output_path, format=format)
    return output_path


def load_graph(filepath: str, format: str = "turtle") -> Graph:
    graph = Graph()
    graph.bind("batt", BATT)
    graph.bind("inst", INST)
    graph.bind("unit", UNIT)
    graph.parse(filepath, format=format)
    return graph
