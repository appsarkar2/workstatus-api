from pydantic import BaseModel
from typing import Optional, Dict, Any

class PMSuryaGharRecordCreate(BaseModel):
    report_type: str # "vendor_stage" | "agreement_followup" | "loan_status"
    application_number: str
    registration_number: Optional[str] = ""
    data: Dict[str, Any] = {}
