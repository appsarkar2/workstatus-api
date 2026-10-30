from pydantic import BaseModel
from typing import List, Optional

class CategoryData(BaseModel):
    category: str
    nos: int = 0
    remarks: str = ""

class UnbilledReportCreate(BaseModel):
    zone: Optional[str] = None      # <-- ADDED
    region: Optional[str] = None    # <-- ADDED
    division: str
    ccc: str
    report_month: str
    topic: str = "Unbilled nos. of L&MV consumer and detailed analysis for the last billing month"
    data: List[CategoryData]