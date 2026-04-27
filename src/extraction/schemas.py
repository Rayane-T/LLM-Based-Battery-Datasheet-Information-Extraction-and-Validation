"""
Pydantic models for structured battery specification output.

Defines the expected schema for LLM extraction results,
ensuring type safety and validation of extracted values.
"""

from typing import Optional
from pydantic import BaseModel, Field


class BatterySpecification(BaseModel):
    """Structured battery specification extracted from a datasheet."""

    # ─── Identification ──────────────────────────────────────────────
    battery_model: Optional[str] = Field(
        None,
        description="Battery model name/number (e.g., 'LIR2450', '16340', '9059156')"
    )
    manufacturer: Optional[str] = Field(
        None,
        description="Manufacturer name (e.g., 'EEMB', 'CATL', 'DNK Power')"
    )
    chemistry: Optional[str] = Field(
        None,
        description="Battery chemistry type (e.g., 'Li-ion', 'LiFePO4', 'Li-Polymer')"
    )

    # ─── Electrical Specifications ───────────────────────────────────
    nominal_voltage_V: Optional[float] = Field(
        None,
        description="Nominal voltage in Volts (e.g., 3.7)"
    )
    nominal_capacity_mAh: Optional[float] = Field(
        None,
        description="Nominal/typical capacity in mAh (e.g., 10000)"
    )
    min_capacity_mAh: Optional[float] = Field(
        None,
        description="Minimum guaranteed capacity in mAh"
    )
    internal_resistance_mOhm: Optional[float] = Field(
        None,
        description="Internal resistance/impedance in milliOhms (mΩ)"
    )
    charge_voltage_V: Optional[float] = Field(
        None,
        description="Maximum charging voltage in Volts (e.g., 4.2)"
    )
    discharge_cutoff_voltage_V: Optional[float] = Field(
        None,
        description="Discharge cut-off voltage in Volts (e.g., 2.75)"
    )

    # ─── Current Specifications ──────────────────────────────────────
    max_charge_current_A: Optional[float] = Field(
        None,
        description="Maximum charge current in Amperes"
    )
    max_discharge_current_A: Optional[float] = Field(
        None,
        description="Maximum continuous discharge current in Amperes"
    )
    standard_charge_current_A: Optional[float] = Field(
        None,
        description="Standard (recommended) charge current in Amperes"
    )
    standard_discharge_current_A: Optional[float] = Field(
        None,
        description="Standard (recommended) discharge current in Amperes"
    )

    # ─── Temperature Specifications ──────────────────────────────────
    operating_temp_min_C: Optional[float] = Field(
        None,
        description="Minimum operating temperature in °C"
    )
    operating_temp_max_C: Optional[float] = Field(
        None,
        description="Maximum operating temperature in °C"
    )
    storage_temp_min_C: Optional[float] = Field(
        None,
        description="Minimum storage temperature in °C"
    )
    storage_temp_max_C: Optional[float] = Field(
        None,
        description="Maximum storage temperature in °C"
    )

    # ─── Physical Specifications ─────────────────────────────────────
    weight_g: Optional[float] = Field(
        None,
        description="Battery weight in grams"
    )
    energy_Wh: Optional[float] = Field(
        None,
        description="Energy capacity in Watt-hours"
    )

    # ─── Lifecycle ───────────────────────────────────────────────────
    cycle_life: Optional[int] = Field(
        None,
        description="Number of charge/discharge cycles at ≥80% capacity retention"
    )
    self_discharge_rate_percent_per_month: Optional[float] = Field(
        None,
        description="Self-discharge rate in percent per month"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}

    def filled_fields_count(self) -> int:
        """Count how many fields have non-None values."""
        return len(self.to_dict())

    def total_fields_count(self) -> int:
        """Count total number of extractable fields."""
        return len(self.model_fields)
