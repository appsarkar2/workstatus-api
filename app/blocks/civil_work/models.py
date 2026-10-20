from pydantic import BaseModel, Field
from typing import Optional, Dict


class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "General"


class CivilWorkCreate(BaseModel):
    work_type: str
    zone: str
    region: str
    division: str
    location_type: str
    location_name: str
    feeder_name: Optional[str] = ""  # <-- Added to support Feeders
    
    applicant: ApplicantInfo
    application_date: Optional[str] = None
    documents: Optional[Dict[str, bool]] = Field(default_factory=dict)
    assigned_to: Optional[str] = None
    remarks: Optional[str] = ""


class CivilWorkUpdate(BaseModel):
    work_type: Optional[str] = None
    zone: Optional[str] = None
    region: Optional[str] = None
    division: Optional[str] = None
    location_type: Optional[str] = None
    location_name: Optional[str] = None
    feeder_name: Optional[str] = None   # <-- Added to support Feeders
    
    applicant: Optional[ApplicantInfo] = None
    documents: Optional[Dict[str, bool]] = None
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None


class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    completed_by: Optional[str] = None