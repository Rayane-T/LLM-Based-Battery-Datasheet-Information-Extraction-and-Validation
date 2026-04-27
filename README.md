# LLM-Based Battery Datasheet Information Extraction and Validation

An intelligent pipeline that extracts, structures, and validates battery specifications from PDF datasheets using Large Language Models (LLMs) and knowledge graphs.

## Overview

Battery datasheets contain critical technical specifications (voltage, capacity, discharge rate, temperature ranges, etc.) but are often in unstructured PDF formats. This project provides a three-level pipeline:

| Level | Component | Description |
|-------|-----------|-------------|
| **1** | LLM Extraction | Extract structured specs from PDFs using zero-shot and few-shot prompting |
| **2** | Knowledge Graph | Build an OWL ontology and populate an RDF knowledge graph |
| **3** | Hallucination Detection | Validate extracted values against physics constraints and ontology rules |

## Architecture

```
documents/*.pdf → PDF Parser → Raw Text
                                   ↓
                              LLM Extractor (zero-shot / few-shot)
                                   ↓
                              Structured JSON (BatterySpecification)
                                   ↓
                    ┌──────────────┼──────────────┐
                    ↓              ↓              ↓
               Evaluation    Knowledge Graph  Validation
              (vs ground      (RDF/OWL)     (hallucination
               truth)                        detection)
```

## Project Structure

```
├── main.py                      # CLI entry point
├── config.py                    # Configuration (API keys, paths, settings)
├── requirements.txt             # Python dependencies
├── documents/                   # Battery PDF datasheets
│   ├── 16340-battery-datasheet.pdf
│   ├── 3.7V9059156.pdf
│   ├── CATL-86Ah-3.2V-LiFePO4-Prismatic-Battery-Cell-SpecificationDatasheet.pdf
│   └── lir2450_EEMB.pdf
├── src/
│   ├── extraction/
│   │   ├── pdf_parser.py        # PyMuPDF-based PDF text extraction
│   │   ├── llm_extractor.py     # LLM API integration & extraction
│   │   ├── prompts.py           # Zero-shot & few-shot prompt templates
│   │   └── schemas.py           # Pydantic models for battery specs
│   ├── knowledge_graph/
│   │   ├── ontology.py          # OWL ontology definition
│   │   ├── graph_builder.py     # RDF triple generation
│   │   └── query.py             # SPARQL query utilities
│   └── validation/
│       ├── rules.py             # Physics & consistency validation rules
│       ├── validator.py         # Hallucination detection engine
│       └── report.py            # Validation report generation
├── evaluation/
│   ├── ground_truth.json        # Manual ground-truth annotations
│   ├── metrics.py               # Precision, recall, F1, accuracy
│   └── compare.py               # Comparison & strategy evaluation
└── outputs/                     # Generated outputs (JSON, TTL, reports)
```

## Setup

### Prerequisites

- Python 3.9+
- An OpenAI API key (for LLM extraction)

### Installation

```bash
# Clone the repository
git clone https://github.com/Rayane-T/LLM-Based-Battery-Datasheet-Information-Extraction-and-Validation.git
cd LLM-Based-Battery-Datasheet-Information-Extraction-and-Validation

# Install dependencies
pip install -r requirements.txt

# Set up your API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

## Usage

### Full Pipeline

```bash
# Run the complete pipeline (extraction + evaluation + KG + validation)
python main.py --all

# Run with a specific model
python main.py --all --model gpt-4o

# Run with only one prompting strategy
python main.py --all --strategy few_shot
```

### Individual Steps

```bash
# Step 1-2: Extract text and run LLM extraction
python main.py --extract

# Step 3: Evaluate extraction results against ground truth
python main.py --evaluate

# Step 4: Build knowledge graph
python main.py --kg

# Step 5: Run hallucination detection
python main.py --validate
```

### Testing Individual Modules

```bash
# Test PDF parser
python src/extraction/pdf_parser.py

# Test knowledge graph construction (uses ground truth)
python src/knowledge_graph/query.py

# Test validation rules (uses ground truth)
python src/validation/report.py
```

## Datasheets

The project includes 4 battery datasheets covering different chemistries and form factors:

| Battery | Manufacturer | Chemistry | Voltage | Capacity |
|---------|-------------|-----------|---------|----------|
| 16340 | DNK Power | LiFePO4 | 3.2V | 500 mAh |
| PL-9059156 | BatterySpace | Li-Polymer | 3.7V | 10,000 mAh |
| FFH3DS (86Ah) | CATL | LiFePO4 | 3.2V | 86,000 mAh |
| LIR2450 | EEMB | Li-ion | 3.6V | 120 mAh |

## Level 1: LLM-Based Extraction

### Approach

Two prompting strategies are compared:

- **Zero-shot**: The LLM receives only the schema definition and datasheet text
- **Few-shot**: Includes a manually crafted example of (datasheet → JSON) before the actual extraction

### Extracted Fields (20 total)

Battery model, manufacturer, chemistry, nominal voltage, capacity, internal resistance, charge/discharge voltages, charge/discharge currents, temperature ranges, weight, energy, cycle life, self-discharge rate.

### Evaluation Metrics

- **Precision**: Fraction of extracted values that are correct
- **Recall**: Fraction of ground-truth values that were extracted
- **F1 Score**: Harmonic mean of precision and recall
- **Accuracy**: Overall correct predictions (including true negatives)

Numeric values use a 5% tolerance for matching.

## Level 2: Knowledge Graph

### Ontology Design

The battery ontology uses OWL and includes:

- **Classes**: `Battery`, `ElectricalSpecification`, `PhysicalSpecification`, `ThermalSpecification`, `LifecycleSpecification`, `Unit`, `Manufacturer`, `Chemistry`
- **Object Properties**: `hasSpecification`, `hasManufacturer`, `hasChemistry`, `hasUnit`
- **Datatype Properties**: `batteryModel`, `hasValue`, `specName`, `unitSymbol`, etc.

### SPARQL Queries

```sparql
# Find all LiFePO4 batteries
SELECT ?model WHERE {
    ?b a batt:Battery ; batt:batteryModel ?model ;
       batt:hasChemistry ?c .
    ?c batt:chemistryType "LiFePO4" .
}

# Get specs for a specific battery
SELECT ?specName ?value ?unit WHERE {
    ?b batt:batteryModel "LIR2450" ;
       batt:hasSpecification ?s .
    ?s batt:specName ?specName ; batt:hasValue ?value ;
       batt:hasUnit ?u . ?u batt:unitSymbol ?unit .
}
```

## Level 3: Hallucination Detection

### Validation Rules

| Rule | Type | Description |
|------|------|-------------|
| Voltage Range | Chemistry-specific | Checks if voltages match the battery chemistry |
| Voltage Ordering | Cross-field | Ensures cutoff < nominal < charge voltage |
| Temperature Bounds | Physical | Checks operating/storage temps are realistic |
| Temperature Ordering | Cross-field | Ensures min < max temperatures |
| Capacity Consistency | Cross-field | Min capacity ≤ nominal; energy ≈ V × Ah |
| Current Plausibility | Physics | Checks C-rates are within typical bounds |
| Current Ordering | Cross-field | Standard ≤ maximum current |
| Cycle Life | Range | 0 < cycle_life < 20,000 |
| Self-Discharge | Range | 0 ≤ rate ≤ 30%/month |

### Severity Levels

- ℹ️ **INFO**: Informational note
- ⚠️ **WARNING**: Potentially incorrect value
- ❌ **ERROR**: Inconsistent value (violates constraints)
- 🔮 **HALLUCINATION**: Value not supported by physics or ontology

## Configuration

Key settings in `config.py` and `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model to use for extraction |
| `LLM_TEMPERATURE` | `0.0` | Sampling temperature (0 = deterministic) |
| `LLM_MAX_TOKENS` | `4096` | Maximum response tokens |

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.