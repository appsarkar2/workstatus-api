from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from app.auth import get_current_user
from app.blocks.pm_surya_ghar.service import PMSuryaGharService

router = APIRouter(
    prefix="/api/blocks/pm_surya_ghar",
    tags=["PM Surya Ghar Monitoring"]
)

@router.get("/overview")
def get_overview(current=Depends(get_current_user)):
    service = PMSuryaGharService(current)
    return service.get_overview()

@router.get("/config")
def get_config(current=Depends(get_current_user)):
    service = PMSuryaGharService(current)
    return service.get_config()

@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    report_type: str = Query(None),
    current=Depends(get_current_user)
):
    if current.get("username") != "superadmin" and current.get("role") not in ("superadmin", "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Only superadmin can upload PM Surya Ghar reports")
    service = PMSuryaGharService(current)
    return await service.upload_report(file, query_report_type=report_type)

@router.get("/application/{application_number}")
def get_application_lookup(application_number: str, current=Depends(get_current_user)):
    service = PMSuryaGharService(current)
    return service.get_application_lookup(application_number)

@router.get("/{report_type}/filters")
def get_filters(report_type: str, current=Depends(get_current_user)):
    if report_type not in ["vendor_stage", "agreement_followup", "loan_status"]:
        raise HTTPException(status_code=404, detail="Invalid report type")
    service = PMSuryaGharService(current)
    return service.get_filters(report_type)

@router.get("/{report_type}/summary")
def get_summary(
    report_type: str,
    district: str = Query(None),
    circle: str = Query(None),
    division: str = Query(None),
    sub_division: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user)
):
    if report_type not in ["vendor_stage", "agreement_followup", "loan_status"]:
        raise HTTPException(status_code=404, detail="Invalid report type")
    service = PMSuryaGharService(current)
    filters = {
        "district": district,
        "circle": circle,
        "division": division,
        "sub_division": sub_division,
        "search": search
    }
    return service.get_summary(report_type, filters=filters)

@router.get("/{report_type}/records")
def list_records(
    report_type: str,
    district: str = Query(None),
    circle: str = Query(None),
    division: str = Query(None),
    sub_division: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    current=Depends(get_current_user)
):
    if report_type not in ["vendor_stage", "agreement_followup", "loan_status"]:
        raise HTTPException(status_code=404, detail="Invalid report type")
    service = PMSuryaGharService(current)
    filters = {
        "district": district,
        "circle": circle,
        "division": division,
        "sub_division": sub_division,
        "search": search
    }
    return service.list_records(report_type, filters=filters, page=page, limit=limit)

@router.delete("/{report_type}/records")
def delete_report_records(report_type: str, current=Depends(get_current_user)):
    if report_type not in ["vendor_stage", "agreement_followup", "loan_status"]:
        raise HTTPException(status_code=404, detail="Invalid report type")
    service = PMSuryaGharService(current)
    return service.delete_report_data(report_type)
