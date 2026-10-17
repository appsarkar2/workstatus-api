from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user
from app.blocks.test_path.models import (
    TestPathCreate,
    TestPathUpdate,
    StageUpdate,
)
from app.blocks.test_path.service import TestPathService

router = APIRouter(
    prefix="/api/blocks/test_path",
    tags=["Block: Test Path"],
)


@router.get("/")
def list_applications(
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user),
):
    return TestPathService(current).list_all(status=status, search=search)


@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return TestPathService(current).get_config()


@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return TestPathService(current).stats()


@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    return TestPathService(current).get_one(app_id)


@router.post("/")
def create(body: TestPathCreate, current=Depends(get_current_user)):
    return TestPathService(current).create(body)


@router.put("/{app_id}")
def update(app_id: str, body: TestPathUpdate, current=Depends(get_current_user)):
    return TestPathService(current).update(app_id, body)


@router.put("/{app_id}/stage")
def update_stage(app_id: str, body: StageUpdate, current=Depends(get_current_user)):
    return TestPathService(current).update_stage(app_id, body)


@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    return TestPathService(current).delete(app_id)