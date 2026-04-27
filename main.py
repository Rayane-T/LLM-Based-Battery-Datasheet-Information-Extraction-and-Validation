"""
Main CLI entry point for the Battery Datasheet Extraction Pipeline.

Orchestrates the full pipeline:
1. Parse PDFs → extract text
2. Run LLM extraction (zero-shot + few-shot)
3. Evaluate against ground truth
4. Build knowledge graph
5. Run validation / hallucination detection
6. Output results
"""

import argparse
import json
import logging
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add project root to path
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

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def step_extract_text():
    """Step 1: Extract text from all PDF datasheets."""
    console.print(Panel("[bold]Step 1: PDF Text Extraction[/bold]", style="cyan"))

    documents = extract_all_documents(DOCUMENTS_DIR)
    console.print(f"  Extracted text from {len(documents)} datasheets\n")

    for doc in documents:
        console.print(f"  📄 {doc.filename} — {doc.num_pages} pages, {len(doc.cleaned_text)} chars")

    return documents


def step_llm_extraction(documents, strategies=None, model=None):
    """Step 2: Run LLM-based extraction."""
    console.print(Panel("[bold]Step 2: LLM-Based Extraction[/bold]", style="cyan"))

    if strategies is None:
        strategies = ["zero_shot", "few_shot"]

    all_results = {}

    for strategy in strategies:
        console.print(f"\n  🤖 Running {strategy} extraction...")

        results = extract_all_datasheets(documents, strategy=strategy, model=model)

        # Save results
        output_path = save_results(results, OUTPUTS_DIR, strategy)
        console.print(f"  💾 Results saved to: {output_path}")

        # Summary
        for filename, spec in results:
            if spec:
                console.print(
                    f"    ✅ {filename}: {spec.filled_fields_count()}/{spec.total_fields_count()} fields"
                )
            else:
                console.print(f"    ❌ {filename}: extraction failed")

        all_results[strategy] = results

    return all_results


def step_evaluate(strategies=None):
    """Step 3: Evaluate extraction results against ground truth."""
    console.print(Panel("[bold]Step 3: Evaluation[/bold]", style="cyan"))

    if strategies is None:
        strategies = ["zero_shot", "few_shot"]

    ground_truths = load_ground_truth()

    for strategy in strategies:
        pred_path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
        if not os.path.exists(pred_path):
            console.print(f"  ⚠️  No predictions found for {strategy}, skipping")
            continue

        predictions = load_predictions(pred_path)
        print_full_evaluation(predictions, ground_truths, strategy_name=strategy)


def step_knowledge_graph(strategy="few_shot"):
    """Step 4: Build and query the knowledge graph."""
    console.print(Panel("[bold]Step 4: Knowledge Graph Construction[/bold]", style="cyan"))

    # Load extraction results
    pred_path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
    if not os.path.exists(pred_path):
        console.print(f"  ⚠️  No extraction results found for {strategy}")
        console.print("  Using ground truth data instead...")
        with open(os.path.join(EVALUATION_DIR, "ground_truth.json")) as f:
            data = json.load(f)
    else:
        with open(pred_path) as f:
            data = json.load(f)

    # Build graph
    graph = build_knowledge_graph(data)

    # Save graph
    ttl_path = os.path.join(OUTPUTS_DIR, "battery_kg.ttl")
    save_graph(graph, ttl_path)
    console.print(f"  💾 Knowledge graph saved to: {ttl_path}")

    # Print summary
    print_graph_summary(graph)

    # Run example queries
    console.print("[bold cyan]Example SPARQL Queries:[/bold cyan]")

    batteries = query_all_batteries(graph)
    for b in batteries:
        model = b["model"]
        console.print(f"\n  [bold]Specifications for {model}:[/bold]")
        specs = query_battery_specs(graph, model)
        for s in specs:
            console.print(f"    {s['spec_name']}: {s['value']} {s['unit']}")

    return graph


def step_validate(strategy="few_shot"):
    """Step 5: Run hallucination detection and validation."""
    console.print(Panel("[bold]Step 5: Hallucination Detection & Validation[/bold]", style="cyan"))

    # Load extraction results
    pred_path = os.path.join(OUTPUTS_DIR, f"extraction_{strategy}.json")
    if not os.path.exists(pred_path):
        console.print(f"  ⚠️  No extraction results found for {strategy}")
        console.print("  Using ground truth data instead...")
        with open(os.path.join(EVALUATION_DIR, "ground_truth.json")) as f:
            data = json.load(f)
    else:
        with open(pred_path) as f:
            data = json.load(f)

    # Validate
    all_issues = validate_all(data)

    # Print report
    print_validation_report(all_issues, f"Validation Report ({strategy})")

    # Save report
    report_path = os.path.join(OUTPUTS_DIR, f"validation_report_{strategy}.json")
    save_validation_report(all_issues, report_path)
    console.print(f"  💾 Validation report saved to: {report_path}")

    return all_issues


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Battery Datasheet Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --all                    Run full pipeline
  python main.py --extract                Extract text + run LLM extraction  
  python main.py --evaluate               Evaluate existing results
  python main.py --kg                     Build knowledge graph
  python main.py --validate               Run validation only
  python main.py --extract --model gpt-4o Use specific model
        """,
    )

    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--extract", action="store_true", help="Run PDF + LLM extraction")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate against ground truth")
    parser.add_argument("--kg", action="store_true", help="Build knowledge graph")
    parser.add_argument("--validate", action="store_true", help="Run validation/hallucination detection")
    parser.add_argument(
        "--strategy",
        choices=["zero_shot", "few_shot", "both"],
        default="both",
        help="Prompting strategy (default: both)",
    )
    parser.add_argument("--model", type=str, default=None, help="LLM model name")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which strategies to run
    strategies = (
        ["zero_shot", "few_shot"] if args.strategy == "both"
        else [args.strategy]
    )

    # Banner
    console.print(Panel(
        "[bold white]🔋 Battery Datasheet Extraction Pipeline[/bold white]\n"
        "[dim]LLM-based extraction, knowledge graph, and hallucination detection[/dim]",
        style="bold cyan",
    ))

    if args.all or (not any([args.extract, args.evaluate, args.kg, args.validate])):
        # Run everything
        if not args.all:
            console.print("[dim]No specific step selected, running full pipeline...[/dim]\n")

        documents = step_extract_text()
        step_llm_extraction(documents, strategies=strategies, model=args.model)
        step_evaluate(strategies=strategies)

        # Use the best strategy for KG and validation
        preferred = "few_shot" if "few_shot" in strategies else strategies[0]
        step_knowledge_graph(strategy=preferred)
        step_validate(strategy=preferred)
    else:
        if args.extract:
            documents = step_extract_text()
            step_llm_extraction(documents, strategies=strategies, model=args.model)

        if args.evaluate:
            step_evaluate(strategies=strategies)

        if args.kg:
            preferred = "few_shot" if "few_shot" in strategies else strategies[0]
            step_knowledge_graph(strategy=preferred)

        if args.validate:
            preferred = "few_shot" if "few_shot" in strategies else strategies[0]
            step_validate(strategy=preferred)

    console.print("\n[bold green]✅ Pipeline complete![/bold green]\n")


if __name__ == "__main__":
    main()
