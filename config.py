"""
Central configuration for the battery datasheet extraction pipeline.
Loads API keys from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# ─── LLM Configuration ───────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ─── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "documents")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
EVALUATION_DIR = os.path.join(PROJECT_ROOT, "evaluation")

# Ensure output directory exists
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ─── Extraction Settings ─────────────────────────────────────────────
# Fields to extract from battery datasheets
EXTRACTION_FIELDS = [
    "battery_model",
    "manufacturer",
    "chemistry",
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
    "cycle_life",
    "energy_Wh",
    "self_discharge_rate_percent_per_month",
]

# ─── Knowledge Graph Settings ────────────────────────────────────────
ONTOLOGY_NAMESPACE = "http://battery-ontology.org/schema#"
INSTANCE_NAMESPACE = "http://battery-ontology.org/instance#"

# ─── Validation Settings ─────────────────────────────────────────────
# Physical plausibility bounds per chemistry type
VOLTAGE_RANGES = {
    "LiFePO4": {"min": 2.0, "max": 3.8},
    "Li-ion": {"min": 2.5, "max": 4.35},
    "Li-Polymer": {"min": 2.5, "max": 4.35},
    "LiCoO2": {"min": 2.5, "max": 4.35},
    "NMC": {"min": 2.5, "max": 4.35},
    "LTO": {"min": 1.0, "max": 2.9},
}

TEMPERATURE_BOUNDS = {
    "operating_min": -60,  # °C
    "operating_max": 85,   # °C
    "storage_min": -40,    # °C
    "storage_max": 60,     # °C
}
