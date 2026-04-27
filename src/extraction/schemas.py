from typing import Optional
from pydantic import BaseModel, Field


class BatterySpecification(BaseModel):
    battery_model: Optional[str] = Field(None)
    manufacturer: Optional[str] = Field(None)
    chemistry: Optional[str] = Field(None)

    nominal_voltage_V: Optional[float] = Field(None)
    nominal_capacity_mAh: Optional[float] = Field(None)
    min_capacity_mAh: Optional[float] = Field(None)
    internal_resistance_mOhm: Optional[float] = Field(None)
    charge_voltage_V: Optional[float] = Field(None)
    discharge_cutoff_voltage_V: Optional[float] = Field(None)

    max_charge_current_A: Optional[float] = Field(None)
    max_discharge_current_A: Optional[float] = Field(None)
    standard_charge_current_A: Optional[float] = Field(None)
    standard_discharge_current_A: Optional[float] = Field(None)

    operating_temp_min_C: Optional[float] = Field(None)
    operating_temp_max_C: Optional[float] = Field(None)
    storage_temp_min_C: Optional[float] = Field(None)
    storage_temp_max_C: Optional[float] = Field(None)

    weight_g: Optional[float] = Field(None)
    energy_Wh: Optional[float] = Field(None)

    cycle_life: Optional[int] = Field(None)
    self_discharge_rate_percent_per_month: Optional[float] = Field(None)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}

    def filled_fields_count(self) -> int:
        return len(self.to_dict())

    def total_fields_count(self) -> int:
        return len(self.model_fields)
