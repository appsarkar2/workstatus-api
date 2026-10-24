from fastapi import APIRouter, Depends, Query, HTTPException
from app.auth import get_current_user
from app.blocks.bulk_connection.models import (
    BulkConnectionCreate,
    BulkConnectionUpdate,
    StageUpdate,
)
from app.blocks.bulk_connection.service import BulkConnectionService
from datetime import datetime

router = APIRouter(
    prefix="/api/blocks/bulk_connection",
    tags=["Block: Bulk Connection"],
)

@router.get("/")
def list_applications(status: str = Query(None), search: str = Query(None), current=Depends(get_current_user)):
    return BulkConnectionService(current).list_all(status=status, search=search)

@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return BulkConnectionService(current).get_config()

@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return BulkConnectionService(current).stats()

@router.get("/sla-report")
def get_sla_report(current=Depends(get_current_user)):
    if current.get("role") not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return BulkConnectionService(current).get_sla_report()

@router.get("/sla-summary")
def get_sla_summary(current=Depends(get_current_user)):
    return BulkConnectionService(current).get_stage_sla_summary()

@router.get("/stage-apps")
def get_stage_apps(stage_no: int = Query(...), current=Depends(get_current_user)):
    service = BulkConnectionService(current)
    apps = list(service.collection.find({"block_id": service.BLOCK_ID, "status": "in_progress", "current_stage": stage_no}))
    
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
                # Compare dates only
                if now.date() > target.date():
                    app["is_breached"] = True
                    app["delay_days"] = (now.date() - target.date()).days
            except Exception:
                pass
        results.append(app)
        
    return {"items": results}

@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    if not app_id or len(app_id) < 12:
        raise HTTPException(status_code=400, detail="Invalid Application ID format")
    return BulkConnectionService(current).get_one(app_id)

@router.post("/")
def create(body: BulkConnectionCreate, current=Depends(get_current_user)):
    return BulkConnectionService(current).create(body)

@router.put("/{app_id}")
def update(app_id: str, body: BulkConnectionUpdate, current=Depends(get_current_user)):
    return BulkConnectionService(current).update(app_id, body)

@router.put("/{app_id}/stage")
def update_stage(app_id: str, body: StageUpdate, current=Depends(get_current_user)):
    return BulkConnectionService(current).update_stage(app_id, body)

@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    return BulkConnectionService(current).delete(app_id)