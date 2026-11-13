from pydantic import BaseModel
from typing import Optional, List


class RevenueEntryCreate(BaseModel):
    """Create a single revenue entry row."""
    zone: str
    region: str
    division: str
    ccc: str
    consumer_class: Optional[str] = "All Classes"  # Industrial, Domestic, Commercial, Govt, Others
    report_month: str  # YYYY-MM
    total_count: int = 0
    total_amount_cr: float = 0.0
    fully_paid_count: int = 0
    fully_paid_amount_lakh: float = 0.0
    part_paid_count: int = 0
    part_paid_amount_lakh: float = 0.0
    disconnected_count: int = 0
    disconnected_amount_lakh: float = 0.0
    no_action_count: int = 0
    no_action_amount_cr: float = 0.0
    osd_gt_3k_count: int = 0
    osd_gt_3k_amount_cr: float = 0.0
    osd_gt_5k_count: int = 0
    osd_gt_5k_amount_cr: float = 0.0


class RevenueEntryUpdate(BaseModel):
    zone: Optional[str] = None
    region: Optional[str] = None
    division: Optional[str] = None
    ccc: Optional[str] = None
    consumer_class: Optional[str] = None
    report_month: Optional[str] = None
    total_count: Optional[int] = None
    total_amount_cr: Optional[float] = None
    fully_paid_count: Optional[int] = None
    fully_paid_amount_lakh: Optional[float] = None
    part_paid_count: Optional[int] = None
    part_paid_amount_lakh: Optional[float] = None
    disconnected_count: Optional[int] = None
    disconnected_amount_lakh: Optional[float] = None
    no_action_count: Optional[int] = None
    no_action_amount_cr: Optional[float] = None
    osd_gt_3k_count: Optional[int] = None
    osd_gt_3k_amount_cr: Optional[float] = None
    osd_gt_5k_count: Optional[int] = None
    osd_gt_5k_amount_cr: Optional[float] = None


class BulkUploadPayload(BaseModel):
    entries: List[RevenueEntryCreate]
