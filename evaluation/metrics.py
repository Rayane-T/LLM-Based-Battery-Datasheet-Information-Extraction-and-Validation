import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

NUMERIC_FIELDS = {
    "nominal_voltage_V",
    "nominal_capacity_mAh",
    "min_capacity_mAh",
    "internal_resistance_mOhm",
    "charge_voltage_V",
    "discharge_cutoff_voltage_V",
    "max_charge_current_A",
    "max_discharge_current_A",
    "standard_charge_current_A",
    "standard_discharge_current_A",
    "operating_temp_min_C",
    "operating_temp_max_C",
    "storage_temp_min_C",
    "storage_temp_max_C",
    "weight_g",
    "energy_Wh",
    "cycle_life",
    "self_discharge_rate_percent_per_month",
}

STRING_FIELDS = {
    "battery_model",
    "manufacturer",
    "chemistry",
}

ALL_FIELDS = NUMERIC_FIELDS | STRING_FIELDS

NUMERIC_TOLERANCE = 0.05


def values_match(predicted, ground_truth, field_name: str) -> bool:
    if predicted is None and ground_truth is None:
        return True
    if predicted is None or ground_truth is None:
        return False

    if field_name in STRING_FIELDS:
        return str(predicted).strip().lower() == str(ground_truth).strip().lower()

    if field_name in NUMERIC_FIELDS:
        try:
            pred_val = float(predicted)
            gt_val = float(ground_truth)
            if gt_val == 0:
                return pred_val == 0
            relative_error = abs(pred_val - gt_val) / abs(gt_val)
            return relative_error <= NUMERIC_TOLERANCE
        except (ValueError, TypeError):
            return str(predicted).strip() == str(ground_truth).strip()

    return str(predicted) == str(ground_truth)


def compute_field_metrics(predicted: dict, ground_truth: dict) -> dict:
    results = {}
    for field in ALL_FIELDS:
        pred_val = predicted.get(field)
        gt_val = ground_truth.get(field)
        match = values_match(pred_val, gt_val, field)
        results[field] = {
            "predicted": pred_val,
            "ground_truth": gt_val,
            "match": match,
            "pred_is_none": pred_val is None,
            "gt_is_none": gt_val is None,
        }
    return results


def compute_extraction_metrics(field_results: dict) -> dict:
    tp = 0
    fp = 0
    fn = 0
    tn = 0

    for field, result in field_results.items():
        pred_none = result["pred_is_none"]
        gt_none = result["gt_is_none"]
        match = result["match"]

        if not gt_none and not pred_none:
            if match:
                tp += 1
            else:
                fp += 1
        elif not gt_none and pred_none:
            fn += 1
        elif gt_none and not pred_none:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "total_fields": tp + fp + fn + tn,
    }


def evaluate_single(predicted: dict, ground_truth: dict) -> dict:
    field_results = compute_field_metrics(predicted, ground_truth)
    metrics = compute_extraction_metrics(field_results)
    return {
        "field_results": field_results,
        "metrics": metrics,
    }


def evaluate_batch(predictions: dict, ground_truths: dict) -> dict:
    per_file_results = {}
    all_field_results = {}

    for filename in ground_truths:
        if filename not in predictions:
            logger.warning(f"No prediction found for {filename}, skipping")
            continue

        pred = predictions[filename]
        gt = ground_truths[filename]

        if isinstance(pred, dict) and "error" in pred:
            logger.warning(f"Extraction failed for {filename}, skipping")
            continue

        evaluation = evaluate_single(pred, gt)
        per_file_results[filename] = evaluation

        for field, result in evaluation["field_results"].items():
            key = f"{filename}::{field}"
            all_field_results[key] = result

    aggregate_metrics = compute_extraction_metrics(all_field_results)

    return {
        "per_file": per_file_results,
        "aggregate": aggregate_metrics,
    }
