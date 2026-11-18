from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from app.auth import get_current_user
from app.blocks.interruption_report.models import InterruptionCreate
from app.blocks.interruption_report.service import InterruptionReportService

router = APIRouter(
    prefix="/api/blocks/interruption_report",
    tags=["Interruption Report"]
)

# --- ROOT ROUTE (Fixes the 404) ---
@router.get("/")
def list_all(current=Depends(get_current_user)):
    return {"message": "Interruption Report API is working!"}

# --- DASHBOARD ROUTE ---
@router.get("/dashboard")
def get_dashboard(
    zone: str = Query(None),
    region: str = Query(None),
    division: str = Query(None),
    substation: str = Query(None),
    current=Depends(get_current_user)
):
    service = InterruptionReportService(current)
    filters = {
        "zone": zone,
        "region": region,
        "division": division,
        "substation": substation
    }
    return service.get_dashboard_data(filters=filters)

# --- CSV UPLOAD ROUTE ---
@router.post("/bulk-upload")
async def bulk_upload_csv(file: UploadFile = File(...), current=Depends(get_current_user)):
    if current.get("username") != "superadmin":
        raise HTTPException(status_code=403, detail="Only superadmin can upload CSV files")
    service = InterruptionReportService(current)
    return await service.bulk_upload_csv(file)

# --- FILTER OPTIONS ROUTE ---
@router.get("/filter-options")
def get_filter_options(current=Depends(get_current_user)):
    service = InterruptionReportService(current)
    return service.get_filter_options()

# --- PENDING DETAILS ROUTE ---
@router.get("/pending-details")
def get_pending_details(
    zone: str = Query(None),
    region: str = Query(None),
    division: str = Query(None),
    substation: str = Query(None),
    current=Depends(get_current_user)
):
    service = InterruptionReportService(current)
    filters = {
        "zone": zone,
        "region": region,
        "division": division,
        "substation": substation
    }
    return service.get_pending_details(filters=filters)