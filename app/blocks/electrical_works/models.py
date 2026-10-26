from pydantic import BaseModel, Field
from typing import Optional, Dict

class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    address: Optional[str] = ""

class ElectricalWorkCreate(BaseModel):
    applicant: ApplicantInfo
    
    # General Info
    phase: Optional[str] = "Phase-I"
    zone: Optional[str] = ""          # <-- ADDED
    region: Optional[str] = ""
    division: Optional[str] = ""
    scheme_head: Optional[str] = ""
    voltage_level: Optional[str] = "11 KV"
    related_ss: Optional[str] = ""
    
    # Scheme Details
    scheme_name: Optional[str] = ""
    existing_parameter: Optional[str] = ""
    proposed_parameter: Optional[str] = ""
    loading_peak: Optional[str] = ""
    major_material: Optional[str] = ""
    
    # Timeline & Status
    priority: Optional[str] = "High"
    taa_no: Optional[str] = ""
    taa_value: Optional[str] = ""      # <-- ADDED
    billed_value: Optional[str] = ""   # <-- ADDED
    presently_with: Optional[str] = "" # <-- ADDED
    target_date: Optional[str] = ""
    eoffice_ref: Optional[str] = ""
    detailed_status: Optional[str] = ""

class ElectricalWorkUpdate(BaseModel):
    applicant: Optional[ApplicantInfo] = None
    phase: Optional[str] = None
    zone: Optional[str] = None         # <-- ADDED
    region: Optional[str] = None
    division: Optional[str] = None
    scheme_head: Optional[str] = None
    voltage_level: Optional[str] = None
    related_ss: Optional[str] = None
    scheme_name: Optional[str] = None
    existing_parameter: Optional[str] = None
    proposed_parameter: Optional[str] = None
    loading_peak: Optional[str] = None
    major_material: Optional[str] = None
    priority: Optional[str] = None
    taa_no: Optional[str] = None
    taa_value: Optional[str] = None      # <-- ADDED
    billed_value: Optional[str] = None   # <-- ADDED
    presently_with: Optional[str] = None # <-- ADDED
    target_date: Optional[str] = None
    eoffice_ref: Optional[str] = None
    detailed_status: Optional[str] = None

class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    actual_date: Optional[str] = None
    ref_no: Optional[str] = None
    is_feasible: Optional[bool] = True