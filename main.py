import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DOCUMENTS_DIR, OUTPUTS_DIR, EVALUATION_DIR
from src.extraction.pdf_parser import extract_all_documents
from src.extraction.llm_extractor import extract_all_datasheets, save_results
from src.knowledge_graph.graph_builder import build_knowledge_graph, save_graph
from src.knowledge_graph.query import print_graph_summary, query_all_batteries, query_battery_specs
from src.validation.validator import validate_all
from src.validation.report import print_validation_report, save_validation_report
from src.validation.graph_validator import validate_graph
from evaluation.metrics import evaluate_batch
from evaluation.compare import (
    print_full_evaluation,
    compare_strategies,
    load_predictions,
    load_ground_truth,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def step_extract_text():
    print("--- Step 1: PDF Extraction ---")
    docs = extract_all_documents(DOCUMENTS_DIR)
    print(f"found {len(docs)} files")
    return docs

def step_llm_extraction(docs, strategies=None, model=None):
    print("--- Step 2: LLM Extraction ---")
    if strategies is None:
        strategies = ["few_shot"]
    
    all_results = {}
    for strategy in strategies:
        print(f"\n  Running {strategy} extraction...")
        results = extract_all_datasheets(docs, strategy=strategy, model=model)
        save_results(results, OUTPUTS_DIR, strategy)
        all_results[strategy] = results
    return all_results

def step_evaluate(strategies=None):
    print("--- Step 3: Evaluation ---")
    if strategies is None:
        strategies = ["few_shot"]
    
    gt = load_ground_truth()
    for strategy in strategies:
        path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
        if os.path.exists(path):
            preds = load_predictions(path)
            print_full_evaluation(preds, gt, strategy_name=strategy)

    # Compare strategies side-by-side if both are available
    if len(strategies) >= 2:
        zs_path = os.path.join(OUTPUTS_DIR, "extraction_zero_shot.json")
        fs_path = os.path.join(OUTPUTS_DIR, "extraction_few_shot.json")
        if os.path.exists(zs_path) and os.path.exists(fs_path):
            zs_preds = load_predictions(zs_path)
            fs_preds = load_predictions(fs_path)
            # Only compare if both have valid results
            zs_valid = any(v for v in zs_preds.values() if isinstance(v, dict) and "error" not in v)
            fs_valid = any(v for v in fs_preds.values() if isinstance(v, dict) and "error" not in v)
            if zs_valid and fs_valid:
                compare_strategies(zs_preds, fs_preds, gt)
            else:
                print("\n  Skipping strategy comparison: one or both strategies have no valid results.")

def step_kg(strategy="few_shot"):
    print("--- Step 4: Knowledge Graph ---")
    path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
    if not os.path.exists(path):
        with open(os.path.join(EVALUATION_DIR, "ground_truth.json")) as f:
            data = json.load(f)
    else:
        with open(path) as f:
            data = json.load(f)

    graph = build_knowledge_graph(data)
    ttl = os.path.join(OUTPUTS_DIR, "battery_kg.ttl")
    save_graph(graph, ttl)
    
    print_graph_summary(graph)

    batteries = query_all_batteries(graph)
    for b in batteries:
        model = b["model"]
        print(f"\nSpecs for {model}:")
        specs = query_battery_specs(graph, model)
        for s in specs:
            print(f"  {s['spec_name']}: {s['value']} {s['unit']}")
    
    return graph

def step_validate(strategy="few_shot"):
    print("--- Step 5: Rule-Based Validation ---")
    path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
    if not os.path.exists(path):
        with open(os.path.join(EVALUATION_DIR, "ground_truth.json")) as f:
            data = json.load(f)
    else:
        with open(path) as f:
            data = json.load(f)

    issues = validate_all(data)
    print_validation_report(issues, f"Rule-Based Report ({strategy})")
    
    report_path = os.path.join(OUTPUTS_DIR, f"validation_report_{strategy}.json")
    save_validation_report(issues, report_path)

def step_graph_validate(graph):
    """Step 6: Run SPARQL-based validation on the knowledge graph."""
    print("--- Step 6: Graph-Based Validation (SPARQL) ---")
    issues = validate_graph(graph)
    
    if not issues:
        print("  No issues detected via SPARQL validation.")
    else:
        print(f"  Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"    [{issue.severity.value}] {issue.field}: {issue.message}")

    # Save graph validation report
    report_path = os.path.join(OUTPUTS_DIR, "validation_report_graph.json")
    report_data = [
        {
            "field": issue.field,
            "value": issue.value,
            "rule": issue.rule_name,
            "severity": issue.severity.value,
            "message": issue.message,
        }
        for issue in issues
    ]
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"  Graph validation report saved to: {report_path}")

    return issues

def main():
    parser = argparse.ArgumentParser(description="Battery Extraction Pipeline")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--kg", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--strategy", choices=["zero_shot", "few_shot", "both"], default="both")
    parser.add_argument("--model", type=str, default=None)
    
    args = parser.parse_args()

    strategies = ["zero_shot", "few_shot"] if args.strategy == "both" else [args.strategy]

    if args.all or not any([args.extract, args.evaluate, args.kg, args.validate]):
        docs = step_extract_text()
        step_llm_extraction(docs, strategies=strategies, model=args.model)
        step_evaluate(strategies=strategies)

        preferred = "few_shot" if "few_shot" in strategies else strategies[0]
        graph = step_kg(strategy=preferred)
        step_validate(strategy=preferred)
        step_graph_validate(graph)
    else:
        if args.extract:
            docs = step_extract_text()
            step_llm_extraction(docs, strategies=strategies, model=args.model)
        if args.evaluate:
            step_evaluate(strategies=strategies)
        if args.kg:
            preferred = "few_shot" if "few_shot" in strategies else strategies[0]
            graph = step_kg(strategy=preferred)
            step_graph_validate(graph)
        if args.validate:
            preferred = "few_shot" if "few_shot" in strategies else strategies[0]
            step_validate(strategy=preferred)

    print("\ndone.")

if __name__ == "__main__":
    main()
