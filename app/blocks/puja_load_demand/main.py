# backend/app/blocks/puja_load_demand/main.py
"""
FastAPI routes for PUJA Load Demand block.

Route order matters! Custom endpoints MUST come before /{app_id} catch-all,
otherwise FastAPI matches /cost-centers as app_id="cost-centers".
"""
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.blocks.puja_load_demand.models import (
    PUJALoadDemandCreate,
    PUJALoadDemandUpdate,
    StageUpdate,
    CostCenterUpdate,
)
from app.blocks.puja_load_demand.service import PUJALoadDemandService


router = APIRouter(
    prefix="/api/blocks/puja_load_demand",
    tags=["Block: PUJA Load Demand"],
)


# ---------- IMPORTANT: specific routes FIRST ----------

@router.get("/")
def list_entries(
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user),
):
    return PUJALoadDemandService(current).list_all(status=status, search=search)


@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return PUJALoadDemandService(current).get_config()


@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return PUJALoadDemandService(current).stats()


# ---------- Custom endpoints (MUST be before /{app_id}) ----------

@router.get("/report/region")
def region_report(
    date: str = Query(..., description="YYYY-MM-DD"),
    time: str = Query(..., description="HH:MM (e.g. 17:00)"),
    current=Depends(get_current_user),
):
    """Aggregate report: all divisions for a given date+time."""
    return PUJALoadDemandService(current).region_report(date=date, time=time)


@router.get("/report/peak")
def peak_load(
    date: str = Query(..., description="YYYY-MM-DD"),
    current=Depends(get_current_user),
):
    """Peak load per substation for a given date."""
    return PUJALoadDemandService(current).peak_load(date=date)


# NEW: Date Range Peaks endpoint for the frontend table
@router.get("/report/date-range-peaks")
def get_date_range_peaks(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current=Depends(get_current_user),
):
    """Find the max load and exact time for each division across a date range."""
    return PUJALoadDemandService(current).date_range_peaks(start_date=start_date, end_date=end_date)


@router.get("/cost-centers")
def list_cost_centers(current=Depends(get_current_user)):
    return PUJALoadDemandService(current).list_cost_centers()


@router.post("/cost-centers/seed")
def seed_cost_centers(current=Depends(get_current_user)):
    """One-time seed of cost centers from config. Safe to re-run."""
    return PUJALoadDemandService(current).seed_cost_centers()


@router.put("/cost-centers/capacity")
def update_capacity(
    body: CostCenterUpdate,
    current=Depends(get_current_user),
):
    """Admin only — update a substation's capacity."""
    return PUJALoadDemandService(current).update_capacity(
        division_code=body.division_code,
        substation_name=body.substation_name,
        capacity_mva=body.capacity_mva,
    )


# ---------- Catch-all and stage routes LAST ----------

@router.post("/")
def create(body: PUJALoadDemandCreate, current=Depends(get_current_user)):
    return PUJALoadDemandService(current).create(body)


@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    return PUJALoadDemandService(current).get_one(app_id)


@router.put("/{app_id}")
def update(app_id: str, body: PUJALoadDemandUpdate, current=Depends(get_current_user)):
    return PUJALoadDemandService(current).update(app_id, body)


@router.put("/{app_id}/stage")
def update_stage(app_id: str, body: StageUpdate, current=Depends(get_current_user)):
    return PUJALoadDemandService(current).update_stage(app_id, body)


@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    return PUJALoadDemandService(current).delete(app_id)