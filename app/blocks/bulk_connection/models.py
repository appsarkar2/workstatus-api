from pydantic import BaseModel, Field
from typing import Optional, Dict


class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "LT Bulk"


class BulkConnectionCreate(BaseModel):
    application_no: str
    applicant: ApplicantInfo
    division: Optional[str] = ""
    application_date: Optional[str] = None
    documents: Optional[Dict[str, bool]] = Field(default_factory=dict)
    assigned_to: Optional[str] = None
    remarks: Optional[str] = ""


class BulkConnectionUpdate(BaseModel):
    applicant: Optional[ApplicantInfo] = None
    division: Optional[str] = None
    documents: Optional[Dict[str, bool]] = None
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None


class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    completed_by: Optional[str] = None
