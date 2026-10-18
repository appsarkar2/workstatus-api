from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.blocks.base_service import BaseBlockService
from .service import CivilWorkService
from .models import CivilWorkCreate, CivilWorkUpdate, StageUpdate
import json
from pathlib import Path

router = APIRouter(prefix="/api/blocks/civil_work", tags=["civil_work"])

def get_config():
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)

def get_service(user=Depends(get_current_user)):
    return CivilWorkService(user=user, config=get_config())

@router.get("/config")
def get_block_config(service=Depends(get_service)):
    return service.get_config()

@router.get("/stats")
def get_stats(service=Depends(get_service)):
    return service.stats()

@router.get("/")
def list_apps(status: str = None, search: str = None, service=Depends(get_service)):
    return service.list_all(status=status, search=search)

@router.post("/")
def create_app(body: CivilWorkCreate, service=Depends(get_service)):
    # This calls the custom create() method we wrote in service.py
    return service.create(body)

@router.get("/{app_id}")
def get_app(app_id: str, service=Depends(get_service)):
    return service.get_one(app_id)

@router.put("/{app_id}")
def update_app(app_id: str, body: CivilWorkUpdate, service=Depends(get_service)):
    return service.update(app_id, body)

@router.put("/{app_id}/stage")
def update_app_stage(app_id: str, body: StageUpdate, service=Depends(get_service)):
    return service.update_stage(app_id, body)

@router.delete("/{app_id}")
def delete_app(app_id: str, service=Depends(get_service)):
    return service.delete(app_id)