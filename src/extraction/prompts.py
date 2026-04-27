import json

SCHEMA_DESCRIPTION = """
{
    "battery_model": "string - Battery model name/number",
    "manufacturer": "string - Manufacturer name",
    "chemistry": "string - Battery chemistry type (Li-ion, LiFePO4, Li-Polymer, LiCoO2, NMC, LTO)",
    "nominal_voltage_V": "float - Nominal voltage in Volts",
    "nominal_capacity_mAh": "float - Nominal/typical capacity in milliamp-hours (mAh). Convert Ah to mAh if needed (1 Ah = 1000 mAh)",
    "min_capacity_mAh": "float - Minimum guaranteed capacity in mAh",
    "internal_resistance_mOhm": "float - Internal resistance in milliOhms",
    "charge_voltage_V": "float - Maximum charging voltage in Volts",
    "discharge_cutoff_voltage_V": "float - Discharge cut-off voltage in Volts",
    "max_charge_current_A": "float - Maximum charge current in Amperes. Convert mA to A if needed (1000 mA = 1 A)",
    "max_discharge_current_A": "float - Maximum continuous discharge current in Amperes",
    "standard_charge_current_A": "float - Standard charge current in Amperes",
    "standard_discharge_current_A": "float - Standard discharge current in Amperes",
    "operating_temp_min_C": "float - Minimum operating/working temperature in Celsius",
    "operating_temp_max_C": "float - Maximum operating/working temperature in Celsius",
    "storage_temp_min_C": "float - Minimum storage temperature in Celsius",
    "storage_temp_max_C": "float - Maximum storage temperature in Celsius",
    "weight_g": "float - Battery weight in grams. Convert kg to g if needed",
    "energy_Wh": "float - Energy in Watt-hours",
    "cycle_life": "integer - Number of charge/discharge cycles (typically at >=80% capacity retention)",
    "self_discharge_rate_percent_per_month": "float - Self-discharge rate in percent per month"
}
""".strip()

SYSTEM_PROMPT = """You are an expert battery engineer and data extraction specialist. 
Your task is to extract structured technical specifications from battery datasheet text.

IMPORTANT RULES:
1. Extract ONLY information that is explicitly stated in the datasheet text.
2. Do NOT infer, calculate, or guess values that are not clearly stated.
3. If a value is not found in the text, set it to null.
4. Convert all values to the units specified in the schema (mAh, V, A, C, g, Wh, mOhm).
5. For capacity: If stated in Ah, convert to mAh (multiply by 1000).
6. For current: If stated in mA, convert to A (divide by 1000).
7. For C-rate currents: Calculate actual current = C-rate x nominal capacity. For example, 0.2C for a 500mAh battery = 0.1A.
8. Return ONLY valid JSON matching the schema. No explanations, no markdown formatting.
9. For chemistry: if the datasheet explicitly states LiFePO4, LFP, or iron phosphate, use "LiFePO4". A nominal voltage around 3.2V and charge voltage around 3.65V are strong indicators of LiFePO4.
"""


def build_zero_shot_prompt(datasheet_text: str) -> list:
    user_content = f"""Extract the battery specifications from the following datasheet text.

Output the result as a JSON object with the following schema:
{SCHEMA_DESCRIPTION}

Set any field to null if the information is not found in the datasheet.

DATASHEET TEXT:
\"\"\"
{datasheet_text}
\"\"\"

Return ONLY the JSON object. No other text."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


FEW_SHOT_EXAMPLE_INPUT = """Lithium-ion Battery DATA SHEET
Battery Model: ABC1234
Manufacturer: ExampleBatt Corp.

1.0 Basic Characteristics
1.1 Battery Type: ABC1234
1.2 Nominal Voltage: 3.7V
1.3 Nominal Capacity: 2000mAh
1.4 Internal resistance: <=80mOhm
1.5 Weight: 45g

2.0 Battery Characteristics
Charge: CC at 0.5C (1000mA) to 4.2V, then CV until 0.05C cutoff
Standard Discharge: 0.2C (400mA)
Max Discharge: 2C (4000mA) continuous
Discharge cut-off Voltage: 2.75V

3.0 Temperature
Working temperature: -20C to 60C
Storage temperature: -10C to 45C

4.0 Cycle Life
>=500 cycles at 80% capacity retention

5.0 Self-discharge: <=3%/month"""

FEW_SHOT_EXAMPLE_OUTPUT = json.dumps({
    "battery_model": "ABC1234",
    "manufacturer": "ExampleBatt Corp.",
    "chemistry": "Li-ion",
    "nominal_voltage_V": 3.7,
    "nominal_capacity_mAh": 2000.0,
    "min_capacity_mAh": None,
    "internal_resistance_mOhm": 80.0,
    "charge_voltage_V": 4.2,
    "discharge_cutoff_voltage_V": 2.75,
    "max_charge_current_A": 1.0,
    "max_discharge_current_A": 4.0,
    "standard_charge_current_A": 1.0,
    "standard_discharge_current_A": 0.4,
    "operating_temp_min_C": -20.0,
    "operating_temp_max_C": 60.0,
    "storage_temp_min_C": -10.0,
    "storage_temp_max_C": 45.0,
    "weight_g": 45.0,
    "energy_Wh": None,
    "cycle_life": 500,
    "self_discharge_rate_percent_per_month": 3.0
}, indent=2)


def build_few_shot_prompt(datasheet_text: str) -> list:
    user_example = f"""Extract the battery specifications from the following datasheet text.

Output the result as a JSON object with the following schema:
{SCHEMA_DESCRIPTION}

Set any field to null if the information is not found in the datasheet.

DATASHEET TEXT:
\"\"\"
{FEW_SHOT_EXAMPLE_INPUT}
\"\"\"

Return ONLY the JSON object. No other text."""

    user_actual = f"""Extract the battery specifications from the following datasheet text.

Output the result as a JSON object with the same schema as before.

Set any field to null if the information is not found in the datasheet.

DATASHEET TEXT:
\"\"\"
{datasheet_text}
\"\"\"

Return ONLY the JSON object. No other text."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_example},
        {"role": "assistant", "content": FEW_SHOT_EXAMPLE_OUTPUT},
        {"role": "user", "content": user_actual},
    ]
