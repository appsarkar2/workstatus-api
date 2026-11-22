from pydantic import BaseModel, Field
from typing import Optional, Dict, Union

class SchemeUpdate(BaseModel):
    scheme_name: Optional[str] = None
    scheme_head: Optional[str] = None
    region: Optional[str] = None
    division: Optional[str] = None
    status: Optional[str] = None
    overall_status: Optional[str] = None
    planning_date: Optional[str] = None
    proposal_initiate_date: Optional[str] = None
    presently_with: Optional[str] = None
    taa_no: Optional[str] = None
    taa_date: Optional[str] = None
    taa_value: Optional[float] = None
    billed_value: Optional[float] = None
    target_date: Optional[str] = None
    related_ss: Optional[str] = None
    major_materials: Optional[str] = None
    work_status: Optional[str] = None


class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    address: Optional[str] = ""

class ElectricalWorkCreate(BaseModel):
    applicant: ApplicantInfo
    
    # General Info
    phase: Optional[str] = "Phase-I"
    zone: Optional[str] = ""          
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
    major_materials: Optional[str] = None
    
    # Timeline & Status
    priority: Optional[str] = None
    taa_no: Optional[str] = ""
    taa_date: Optional[str] = None
    taa_value: Optional[Union[float, int, str, None]] = None
    billed_value: Optional[Union[float, int, str, None]] = None
    planning_date: Optional[str] = ""
    proposal_initiate_date: Optional[str] = ""
    presently_with: Optional[str] = ""
    target_date: Optional[str] = ""
    eoffice_ref: Optional[str] = ""
    detailed_status: Optional[str] = ""
    work_status: Optional[str] = None
    status: Optional[str] = "Planned"

class ElectricalWorkUpdate(BaseModel):
    applicant: Optional[ApplicantInfo] = None
    phase: Optional[str] = None
    zone: Optional[str] = None
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
    major_materials: Optional[str] = None
    priority: Optional[str] = None
    taa_no: Optional[str] = None
    taa_date: Optional[str] = None
    taa_value: Optional[float] = None
    billed_value: Optional[float] = None
    planning_date: Optional[str] = None
    proposal_initiate_date: Optional[str] = None
    presently_with: Optional[str] = None
    target_date: Optional[str] = None
    eoffice_ref: Optional[str] = None
    detailed_status: Optional[str] = None
    work_status: Optional[str] = None
    status: Optional[str] = None
    overall_status: Optional[str] = None

class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    actual_date: Optional[str] = None
    ref_no: Optional[str] = None
    is_feasible: Optional[bool] = True