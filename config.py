import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "documents")
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, "outputs")
EVALUATION_DIR = os.path.join(PROJECT_ROOT, "evaluation")

os.makedirs(OUTPUTS_DIR, exist_ok=True)

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

ONTOLOGY_NAMESPACE = "http://battery-ontology.org/schema#"
INSTANCE_NAMESPACE = "http://battery-ontology.org/instance#"

VOLTAGE_RANGES = {
    "LiFePO4": {"min": 2.0, "max": 3.8},
    "Li-ion": {"min": 2.5, "max": 4.35},
    "Li-Polymer": {"min": 2.5, "max": 4.35},
    "LiCoO2": {"min": 2.5, "max": 4.35},
    "NMC": {"min": 2.5, "max": 4.35},
    "LTO": {"min": 1.0, "max": 2.9},
}

TEMPERATURE_BOUNDS = {
    "operating_min": -60,
    "operating_max": 85,
    "storage_min": -40,
    "storage_max": 60,
}
