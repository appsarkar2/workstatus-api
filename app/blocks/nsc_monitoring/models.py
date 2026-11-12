from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class NSCCaseCreate(BaseModel):
    application_no: str
    reg: str
    divn_name: str
    ccc_code: str
    conn_class: str
    pole_type: str
    phase: str
    agency: str
    delay_days: int
    
    # dates
    application_date: str
    quotation_issue_date: str
    wo_creation_date: str
    connection_date: str
    
    # weekly_data: optional list of dicts for deposit/disposal metrics
    weekly_data: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    
    # kpi_data: a dict storing quotation_delay, wo_delay, conn_delay
    kpi_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"

