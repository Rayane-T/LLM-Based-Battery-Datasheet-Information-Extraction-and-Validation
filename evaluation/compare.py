import json
import os
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.metrics import (
    evaluate_single,
    evaluate_batch,
    ALL_FIELDS,
)

console = Console()


def format_value(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.4g}"
    return str(value)


def print_field_comparison(filename: str, evaluation: dict) -> None:
    table = Table(
        title=f"Field Comparison: {filename}",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Field", style="white", min_width=35)
    table.add_column("Predicted", style="yellow", min_width=15)
    table.add_column("Ground Truth", style="green", min_width=15)
    table.add_column("Match", min_width=5)

    field_results = evaluation["field_results"]

    for field in sorted(ALL_FIELDS):
        if field not in field_results:
            continue

        result = field_results[field]
        pred = format_value(result["predicted"])
        gt = format_value(result["ground_truth"])
        match = result["match"]

        match_icon = "OK" if match else "X"
        row_style = None if match else "dim red"

        table.add_row(field, pred, gt, match_icon, style=row_style)

    console.print(table)


def print_metrics_summary(metrics: dict, title: str = "Metrics Summary") -> None:
    text = Text()
    text.append(f"  Precision:  ", style="bold")
    text.append(f"{metrics['precision']:.2%}\n", style="green" if metrics['precision'] >= 0.8 else "yellow")
    text.append(f"  Recall:     ", style="bold")
    text.append(f"{metrics['recall']:.2%}\n", style="green" if metrics['recall'] >= 0.8 else "yellow")
    text.append(f"  F1 Score:   ", style="bold")
    text.append(f"{metrics['f1_score']:.2%}\n", style="green" if metrics['f1_score'] >= 0.8 else "yellow")
    text.append(f"  Accuracy:   ", style="bold")
    text.append(f"{metrics['accuracy']:.2%}\n\n", style="green" if metrics['accuracy'] >= 0.8 else "yellow")
    text.append(f"  TP: {metrics['true_positives']}  FP: {metrics['false_positives']}  "
                f"FN: {metrics['false_negatives']}  TN: {metrics['true_negatives']}")

    console.print(Panel(text, title=title, border_style="cyan"))


def print_full_evaluation(
    predictions: dict,
    ground_truths: dict,
    strategy_name: str = "Extraction",
) -> dict:
    console.print(f"\n{'='*70}")
    console.print(f"[bold cyan]Evaluation Report: {strategy_name}[/bold cyan]")
    console.print(f"{'='*70}\n")

    results = evaluate_batch(predictions, ground_truths)

    for filename, evaluation in results["per_file"].items():
        print_field_comparison(filename, evaluation)
        print_metrics_summary(
            evaluation["metrics"],
            title=f"Metrics: {filename}",
        )
        console.print()

    print_metrics_summary(
        results["aggregate"],
        title=f"AGGREGATE Metrics ({strategy_name})",
    )

    return results


def compare_strategies(
    zero_shot_predictions: dict,
    few_shot_predictions: dict,
    ground_truths: dict,
) -> None:
    console.print(f"\n{'='*70}")
    console.print("[bold magenta]Strategy Comparison: Zero-Shot vs Few-Shot[/bold magenta]")
    console.print(f"{'='*70}\n")

    zs_results = evaluate_batch(zero_shot_predictions, ground_truths)
    fs_results = evaluate_batch(few_shot_predictions, ground_truths)

    table = Table(
        title="Strategy Comparison",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Metric", style="white")
    table.add_column("Zero-Shot", style="yellow")
    table.add_column("Few-Shot", style="green")
    table.add_column("Winner", style="bold")

    metrics_to_compare = ["precision", "recall", "f1_score", "accuracy"]

    for metric in metrics_to_compare:
        zs_val = zs_results["aggregate"][metric]
        fs_val = fs_results["aggregate"][metric]

        if zs_val > fs_val:
            winner = "Zero-Shot"
        elif fs_val > zs_val:
            winner = "Few-Shot"
        else:
            winner = "Tie"

        table.add_row(
            metric.replace("_", " ").title(),
            f"{zs_val:.2%}",
            f"{fs_val:.2%}",
            winner,
        )

    console.print(table)


def load_predictions(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)


def load_ground_truth(filepath: str = None) -> dict:
    if filepath is None:
        filepath = os.path.join(
            os.path.dirname(__file__),
            "ground_truth.json",
        )
    with open(filepath, "r") as f:
        return json.load(f)
