from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user
from app.blocks.bulk_connection.models import (
    BulkConnectionCreate,
    BulkConnectionUpdate,
    StageUpdate,
)
from app.blocks.bulk_connection.service import BulkConnectionService

router = APIRouter(
    prefix="/api/blocks/bulk_connection",
    tags=["Block: Bulk Connection"],
)


@router.get("/")
def list_applications(
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user),
):
    return BulkConnectionService(current).list_all(status=status, search=search)


@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return BulkConnectionService(current).get_config()


@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return BulkConnectionService(current).stats()


@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
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
