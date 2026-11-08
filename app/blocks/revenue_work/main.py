from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from app.auth import get_current_user
from .service import RevenueWorkService
from .models import RevenueEntryCreate, RevenueEntryUpdate, BulkUploadPayload
import json
from pathlib import Path

router = APIRouter(prefix="/api/blocks/revenue_work", tags=["revenue_work"])


def get_config():
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)


def get_service(user=Depends(get_current_user)):
    return RevenueWorkService(user=user, config=get_config())


@router.get("/config")
def get_block_config(service=Depends(get_service)):
    return service.get_config()


@router.get("/stats")
def get_stats(service=Depends(get_service)):
    return service.stats()


@router.get("/dashboard-summary")
def dashboard_summary(
    zone: str = Query(None, description="Filter by zone"),
    region: str = Query(None, description="Filter by region"),
    division: str = Query(None, description="Filter by division"),
    month: str = Query(None, description="Filter by report month YYYY-MM"),
    service=Depends(get_service),
):
    return service.get_dashboard_summary(
        zone=zone,
        region=region,
        division=division,
        month=month,
    )


@router.post("/bulk-upload")
def bulk_upload_csv(
    file: UploadFile = File(...),
    service=Depends(get_service),
):
    return service.bulk_upload_csv(file)


@router.get("/")
def list_entries(service=Depends(get_service)):
    return service.list_all()


@router.post("/")
def create_entry(body: RevenueEntryCreate, service=Depends(get_service)):
    return service.create(body)


@router.get("/{app_id}")
def get_entry(app_id: str, service=Depends(get_service)):
    return service.get_one(app_id)


@router.put("/{app_id}")
def update_entry(app_id: str, body: RevenueEntryUpdate, service=Depends(get_service)):
    return service.update(app_id, body)


@router.delete("/{app_id}")
def delete_entry(app_id: str, service=Depends(get_service)):
    return service.delete(app_id)
