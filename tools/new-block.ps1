# ═══════════════════════════════════════════════════════════════
# WorkStatus — New Block Scaffolder
# Usage: .\new-block.ps1 disconnection "Disconnection of Defaulter"
# ═══════════════════════════════════════════════════════════════

param(
    [Parameter(Mandatory=$true)]
    [string]$BlockId,

    [Parameter(Mandatory=$true)]
    [string]$BlockName
)

$ErrorActionPreference = "Stop"

$root       = Split-Path -Parent $PSScriptRoot
$blocksDir  = Join-Path $root "backend\app\blocks"
$targetDir  = Join-Path $blocksDir $BlockId

if (Test-Path $targetDir) {
    Write-Host "[ERROR] Block '$BlockId' already exists at $targetDir" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Creating block: $BlockId" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $targetDir | Out-Null
New-Item -ItemType File -Path (Join-Path $targetDir "__init__.py") | Out-Null

$safeName = ($BlockName -replace '[^a-zA-Z0-9]', '')

# --- config.json ---
$config = @"
{
  "id": "$BlockId",
  "name": "$BlockName",
  "code": "$($BlockId.Substring(0,3).ToUpper())",
  "icon": "box",
  "color": "blue",
  "active": true,
  "documents_required": [
    {"key": "application_form", "label": "Application Form"},
    {"key": "identity_proof",   "label": "Identity Proof"}
  ],
  "stages": [
    {"no": 1, "name": "Application Received"},
    {"no": 2, "name": "Verification"},
    {"no": 3, "name": "Approval"},
    {"no": 4, "name": "Completed"}
  ],
  "statuses": ["in_progress", "completed", "rejected", "on_hold"]
}
"@
[System.IO.File]::WriteAllText((Join-Path $targetDir "config.json"), $config, (New-Object System.Text.UTF8Encoding $false))

# --- models.py ---
$models = @"
from pydantic import BaseModel, Field
from typing import Optional, Dict


class ApplicantInfo(BaseModel):
    name: str
    contact: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    type: Optional[str] = "General"


class ${safeName}Create(BaseModel):
    application_no: str
    applicant: ApplicantInfo
    division: Optional[str] = ""
    application_date: Optional[str] = None
    documents: Optional[Dict[str, bool]] = Field(default_factory=dict)
    assigned_to: Optional[str] = None
    remarks: Optional[str] = ""


class ${safeName}Update(BaseModel):
    applicant: Optional[ApplicantInfo] = None
    division: Optional[str] = None
    documents: Optional[Dict[str, bool]] = None
    assigned_to: Optional[str] = None
    remarks: Optional[str] = None


class StageUpdate(BaseModel):
    stage_no: int
    status: str
    remarks: Optional[str] = ""
    completed_by: Optional[str] = None
"@
[System.IO.File]::WriteAllText((Join-Path $targetDir "models.py"), $models, (New-Object System.Text.UTF8Encoding $false))

# --- service.py ---
$service = @"
# backend/app/blocks/$BlockId/service.py
import json
from pathlib import Path
from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class ${safeName}Service(BaseBlockService):
    BLOCK_ID = "$BlockId"
    COLLECTION = "${BlockId}s"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)
"@
[System.IO.File]::WriteAllText((Join-Path $targetDir "service.py"), $service, (New-Object System.Text.UTF8Encoding $false))

# --- main.py ---
$main = @"
from fastapi import APIRouter, Depends, Query
from app.auth import get_current_user
from app.blocks.$BlockId.models import (
    ${safeName}Create,
    ${safeName}Update,
    StageUpdate,
)
from app.blocks.$BlockId.service import ${safeName}Service

router = APIRouter(
    prefix="/api/blocks/$BlockId",
    tags=["Block: $BlockName"],
)


@router.get("/")
def list_applications(
    status: str = Query(None),
    search: str = Query(None),
    current=Depends(get_current_user),
):
    return ${safeName}Service(current).list_all(status=status, search=search)


@router.get("/config")
def get_config(current=Depends(get_current_user)):
    return ${safeName}Service(current).get_config()


@router.get("/stats")
def get_stats(current=Depends(get_current_user)):
    return ${safeName}Service(current).stats()


@router.get("/{app_id}")
def get_one(app_id: str, current=Depends(get_current_user)):
    return ${safeName}Service(current).get_one(app_id)


@router.post("/")
def create(body: ${safeName}Create, current=Depends(get_current_user)):
    return ${safeName}Service(current).create(body)


@router.put("/{app_id}")
def update(app_id: str, body: ${safeName}Update, current=Depends(get_current_user)):
    return ${safeName}Service(current).update(app_id, body)


@router.put("/{app_id}/stage")
def update_stage(app_id: str, body: StageUpdate, current=Depends(get_current_user)):
    return ${safeName}Service(current).update_stage(app_id, body)


@router.delete("/{app_id}")
def delete(app_id: str, current=Depends(get_current_user)):
    return ${safeName}Service(current).delete(app_id)
"@
[System.IO.File]::WriteAllText((Join-Path $targetDir "main.py"), $main, (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "[DONE] Block '$BlockId' created at:" -ForegroundColor Green
Write-Host "  $targetDir" -ForegroundColor Gray
Write-Host ""
Write-Host "Next:" -ForegroundColor Yellow
Write-Host "  1. Edit config.json (add real stages + documents)" -ForegroundColor Gray
Write-Host "  2. Restart backend: python run.py" -ForegroundColor Gray
Write-Host "  3. Block auto-appears at /api/blocks" -ForegroundColor Gray