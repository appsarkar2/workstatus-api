from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from app.auth import get_current_user
from app.blocks.nsc_monitoring.models import NSCCaseCreate
from app.blocks.nsc_monitoring.service import NSCMonitoringService

router = APIRouter(
    prefix="/api/blocks/nsc_monitoring",
    tags=["NSC Monitoring"]
)

@router.get("/")
def list_cases(
    region: str = Query(None),
    division: str = Query(None),
    ccc: str = Query(None),
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user)
):
    service = NSCMonitoringService(current)
    return service.list_all(region=region, division=division, ccc=ccc, status=status, search=search)

@router.get("/config")
def get_config(current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.get_config()

@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.stats()

@router.get("/kpi-dashboard")
def get_kpi_dashboard(
    zone: str = Query(None),
    reg: str = Query(None),
    divn_name: str = Query(None),
    ccc_code: str = Query(None),
    conn_class: str = Query(None),
    no_of_poles: str = Query(None),
    current=Depends(get_current_user)
):
    service = NSCMonitoringService(current)
    filters = {
        "zone": zone,
        "reg": reg,
        "divn_name": divn_name,
        "supp_off": ccc_code,
        "ccc_code": ccc_code,
        "conn_class": conn_class,
        "no_of_poles": no_of_poles
    }
    return service.get_kpi_dashboard(filters=filters)

@router.get("/weekly-trend")
def get_weekly_trend(
    region: str = Query(None),
    division: str = Query(None),
    ccc: str = Query(None),
    current=Depends(get_current_user)
):
    service = NSCMonitoringService(current)
    filters = {
        "region": region,
        "division": division,
        "ccc": ccc
    }
    return service.get_weekly_deposit_disposal(filters=filters)

@router.get("/pending")
def get_pending_nsc(
    region: str = Query(None),
    division: str = Query(None),
    ccc: str = Query(None),
    class_type: str = Query(None),
    pole_type: str = Query(None),
    min_delay: int = Query(None),
    max_delay: int = Query(None),
    current=Depends(get_current_user)
):
    service = NSCMonitoringService(current)
    filters = {
        "region": region,
        "division": division,
        "ccc": ccc,
        "class_type": class_type,
        "pole_type": pole_type,
        "min_delay": min_delay,
        "max_delay": max_delay
    }
    return service.get_pending_nsc(filters=filters)

@router.get("/weekly-deposit-disposal")
def get_weekly_deposit_disposal(
    region: str = Query(None),
    division: str = Query(None),
    ccc: str = Query(None),
    current=Depends(get_current_user)
):
    service = NSCMonitoringService(current)
    filters = {
        "region": region,
        "division": division,
        "ccc": ccc
    }
    return service.get_weekly_deposit_disposal(filters=filters)

@router.post("/bulk-upload")
async def bulk_upload_csv(file: UploadFile = File(...), current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return await service.bulk_upload_csv(file)

@router.delete("/delete/{record_id}")
def delete_record(record_id: str, current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.delete_record(record_id)

@router.delete("/delete-all")
def delete_all_records(current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.delete_all_records()

@router.get("/filter-options")
def get_filter_options(current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.get_filter_options()

@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    if not app_id or len(app_id) < 12:
        raise HTTPException(status_code=400, detail="Invalid Application ID format")
    service = NSCMonitoringService(current)
    return service.get_one(app_id)

@router.post("/")
def create(body: NSCCaseCreate, current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.create(body)

@router.put("/{app_id}")
def update(app_id: str, current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.get_one(app_id)

@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    service = NSCMonitoringService(current)
    return service.delete(app_id)

