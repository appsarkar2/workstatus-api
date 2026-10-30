from pydantic import BaseModel, Field
from typing import Optional, Dict


class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "LT"


class BulkConnectionCreate(BaseModel):
    applicant: ApplicantInfo
    
    # --- NEW FIELDS FOR CATEGORIZATION & FILTERS ---
    application_category: Optional[str] = "New Connection"  # New Connection, Load Enhancement, Load Decrease
    load_category: Optional[str] = None                     # Central Bulk, De-Central Bulk
    zone: Optional[str] = ""
    region: Optional[str] = ""
    # -----------------------------------------------
    
    division: Optional[str] = ""
    substation: Optional[str] = ""
    connection_type: Optional[str] = "Procedure-A"
    application_date: Optional[str] = None
    
    # Proposed Demand fields (1st to 5th Year)
    proposed_demand_1st: Optional[str] = ""
    proposed_demand_2nd: Optional[str] = ""
    proposed_demand_3rd: Optional[str] = ""
    proposed_demand_4th: Optional[str] = ""
    proposed_demand_5th: Optional[str] = ""
    
    documents: Optional[Dict[str, bool]] = Field(default_factory=dict)
    assigned_to: Optional[str] = None
    remarks: Optional[str] = ""


class BulkConnectionUpdate(BaseModel):
    applicant: Optional[ApplicantInfo] = None
    
    # --- NEW FIELDS FOR CATEGORIZATION & FILTERS ---
    application_category: Optional[str] = None
    load_category: Optional[str] = None
    zone: Optional[str] = None
    region: Optional[str] = None
    # -----------------------------------------------

    division: Optional[str] = None
    substation: Optional[str] = None
    connection_type: Optional[str] = None
    
    # Proposed Demand fields (1st to 5th Year)
    proposed_demand_1st: Optional[str] = None
    proposed_demand_2nd: Optional[str] = None
    proposed_demand_3rd: Optional[str] = None
    proposed_demand_4th: Optional[str] = None
    proposed_demand_5th: Optional[str] = None
    
    documents: Optional[Dict[str, bool]] = None
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None


class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    completed_by: Optional[str] = None
    
    # Custom Fields for specific stages
    ref_no: Optional[str] = None
    actual_date: Optional[str] = None
    inspection_date: Optional[str] = None
    eoffice_date: Optional[str] = None
    is_feasible: Optional[bool] = True
    deposit_amount: Optional[str] = None
    quotation_amount: Optional[str] = None