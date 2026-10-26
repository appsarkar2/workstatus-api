from fastapi import APIRouter, Depends, Query, HTTPException
from app.auth import get_current_user
from app.blocks.electrical_works.models import (
    ElectricalWorkCreate,
    ElectricalWorkUpdate,
    StageUpdate,
)
from app.blocks.electrical_works.service import ElectricalWorksService
from datetime import datetime

router = APIRouter(
    prefix="/api/blocks/electrical_works",
    tags=["Block: Electrical Works"],
)

# --- STANDARD ROUTES ---

@router.get("/")
def list_applications(
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user),
):
    return ElectricalWorksService(current).list_all(status=status, search=search)

@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return ElectricalWorksService(current).get_config()

@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return ElectricalWorksService(current).stats()

# --- CUSTOM ROUTES (Must be above /{app_id}) ---

@router.get("/sla-summary")
def get_sla_summary(current=Depends(get_current_user)):
    return {}

@router.get("/stage-apps")
def get_stage_apps(
    stage_no: int = Query(...),
    current=Depends(get_current_user)
):
    service = ElectricalWorksService(current)
    apps = list(service.collection.find({
        "block_id": service.BLOCK_ID, 
        "status": "in_progress", 
        "current_stage": stage_no
    }))
    
    now = datetime.utcnow()
    results = []
    
    for app in apps:
        app["_id"] = str(app["_id"])
        app["delay_days"] = 0
        app["is_breached"] = False
        
        current_stage_data = next((s for s in app.get("stages", []) if s["stage_no"] == stage_no), None)
        
        if current_stage_data and current_stage_data.get("target_date"):
            try:
                target = datetime.strptime(current_stage_data["target_date"], "%Y-%m-%d")
                if now.date() > target.date():
                    app["is_breached"] = True
                    app["delay_days"] = (now.date() - target.date()).days
            except Exception:
                pass
                
        results.append(app)
        
    return {"items": results}

# --- NEW ROUTE FOR TABLE OVERVIEW (UPDATED WITH FILTERS) ---

@router.get("/overview-table")
def get_overview_table(
    voltage: str = Query(None),
    phase: str = Query(None),
    zone: str = Query(None),
    region: str = Query(None),
    division: str = Query(None),
    current=Depends(get_current_user)
):
    """Returns grouped stats by Scheme Head and Division with filters."""
    return ElectricalWorksService(current).get_scheme_overview_table(
        voltage=voltage, phase=phase, zone=zone, region=region, division=division
    )

# --- PARAMETERIZED ROUTES (Must be at the bottom) ---

@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    if not app_id or len(app_id) < 12:
        raise HTTPException(status_code=400, detail="Invalid Application ID format")
    return ElectricalWorksService(current).get_one(app_id)

@router.post("/")
def create(body: ElectricalWorkCreate, current=Depends(get_current_user)):
    return ElectricalWorksService(current).create(body)

@router.put("/{app_id}")
def update(app_id: str, body: ElectricalWorkUpdate, current=Depends(get_current_user)):
    return ElectricalWorksService(current).update(app_id, body)

@router.put("/{app_id}/stage")
def update_stage(app_id: str, body: StageUpdate, current=Depends(get_current_user)):
    return ElectricalWorksService(current).update_stage(app_id, body)

@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    return ElectricalWorksService(current).delete(app_id)