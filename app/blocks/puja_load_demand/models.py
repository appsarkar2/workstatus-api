# backend/app/blocks/puja_load_demand/models.py
"""
Pydantic models for PUJA Load Demand block.

Different from bulk_connection because:
- Each entry = one division + one date + one time slot
- Substations are a nested array (not a separate collection)
- System report fields are specific to load reporting
- No document checklist
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class SubstationEntry(BaseModel):
    """One substation row: load + capacity."""
    sl_no: int
    name: str
    load_mva: float = 0.0
    capacity_mva: float = 0.0
    # percent is computed server-side, not accepted from client


class SystemReport(BaseModel):
    """Bottom section of the daily report."""
    ss_without_power: Optional[str] = "NIL/0"
    line_33kv_bd: Optional[str] = "NIL/0"
    line_33kv_bulk: Optional[str] = "NIL/0"  # Added
    line_11kv_bd: Optional[str] = "NIL/0"
    line_11kv_bd_partial: Optional[str] = "NIL/0" # Changed to string
    dtr_replacement_pending: Optional[str] = "NIL" # Changed to string


class PUJALoadDemandCreate(BaseModel):
    """Payload when a division user submits a new entry."""
    division: str                        # "Siliguri Town"
    date: str                            # "2026-10-16"
    time: str                            # "17:00"
    substations: List[SubstationEntry]   # full list for the division
    system_report: Optional[SystemReport] = Field(default_factory=SystemReport)
    weather: Optional[str] = "Normal"
    system_status: Optional[str] = "Normal"
    remarks: Optional[str] = ""


class PUJALoadDemandUpdate(BaseModel):
    """Fields admin can update after submission."""
    substations: Optional[List[SubstationEntry]] = None
    system_report: Optional[SystemReport] = None
    weather: Optional[str] = None
    system_status: Optional[str] = None
    remarks: Optional[str] = None


class StageUpdate(BaseModel):
    """Advance the 2-stage workflow (submitted -> verified)."""
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    completed_by: Optional[str] = None


class CostCenterUpdate(BaseModel):
    """Admin-only: update capacity for a substation."""
    division_code: str
    substation_name: str
    capacity_mva: float