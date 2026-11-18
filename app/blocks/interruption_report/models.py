from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class InterruptionCreate(BaseModel):
    zone: Optional[str] = None
    region: Optional[str] = None
    division: Optional[str] = None
    substation: Optional[str] = None
    feeder_name: Optional[str] = None
    daily_outage: Optional[float] = None
    monthly_outage: Optional[float] = None
    yearly_outage: Optional[float] = None
    trips: Optional[int] = None
    outage_hours: Optional[float] = None
    concern: Optional[bool] = None

    class Config:
        extra = "allow"
