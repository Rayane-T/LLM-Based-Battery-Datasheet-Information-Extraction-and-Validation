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
from evaluation.metrics import evaluate_batch
from evaluation.compare import (
    print_full_evaluation,
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
    
    batteries = query_all_batteries(graph)
    for b in batteries:
        model = b["model"]
        print(f"\nSpecs for {model}:")
        specs = query_battery_specs(graph, model)
        for s in specs:
            print(f"  {s['spec_name']}: {s['value']} {s['unit']}")

def step_validate(strategy="few_shot"):
    print("--- Step 5: Validation ---")
    path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
    if not os.path.exists(path):
        with open(os.path.join(EVALUATION_DIR, "ground_truth.json")) as f:
            data = json.load(f)
    else:
        with open(path) as f:
            data = json.load(f)

    issues = validate_all(data)
    print_validation_report(issues, f"Report ({strategy})")
    
    report_path = os.path.join(OUTPUTS_DIR, f"validation_report_{strategy}.json")
    save_validation_report(issues, report_path)

def main():
    parser = argparse.ArgumentParser(description="Battery Extraction Pipeline")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--kg", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--strategy", default="few_shot")
    parser.add_argument("--model", type=str, default=None)
    
    args = parser.parse_args()

    if args.all or not any([args.extract, args.evaluate, args.kg, args.validate]):
        docs = step_extract_text()
        step_llm_extraction(docs, strategies=[args.strategy], model=args.model)
        step_evaluate(strategies=[args.strategy])
        step_kg(strategy=args.strategy)
        step_validate(strategy=args.strategy)
    else:
        if args.extract:
            docs = step_extract_text()
            step_llm_extraction(docs, strategies=[args.strategy], model=args.model)
        if args.evaluate:
            step_evaluate(strategies=[args.strategy])
        if args.kg:
            step_kg(strategy=args.strategy)
        if args.validate:
            step_validate(strategy=args.strategy)

    print("\ndone.")

if __name__ == "__main__":
    main()
