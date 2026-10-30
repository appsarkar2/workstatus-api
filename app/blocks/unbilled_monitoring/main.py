from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from datetime import datetime
from io import StringIO
import pandas as pd

from app.auth import get_current_user
from .models import UnbilledReportCreate
from .service import UnbilledMonitoringService

# Note: The prefix is defined here
router = APIRouter(prefix="/api/blocks/unbilled_monitoring", tags=["unbilled"])

@router.get("/dashboard-summary")
def get_summary(
    zone: str = Query(None), 
    region: str = Query(None), 
    division: str = Query(None), 
    current=Depends(get_current_user)
):
    service = UnbilledMonitoringService(current, {})
    return service.get_dashboard_summary(zone=zone, region=region, division=division)

@router.post("/report")
def submit_report(body: UnbilledReportCreate, current=Depends(get_current_user)):
    service = UnbilledMonitoringService(current, {})
    
    doc = {
        "block_id": service.BLOCK_ID,
        **body.dict(),
        "created_by": current["username"],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    service.collection.update_one(
        {
            "block_id": service.BLOCK_ID,
            "division": body.division, 
            "ccc": body.ccc, 
            "report_month": body.report_month
        },
        {"$set": doc},
        upsert=True
    )
    return {"message": "Report saved successfully"}

@router.post("/bulk-upload")
async def bulk_upload(file: UploadFile = File(...), current=Depends(get_current_user)):
    """Processes a CSV file and upserts all rows into MongoDB."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only .csv files are supported currently")

    service = UnbilledMonitoringService(current, {})
    
    try:
        # Read file contents
        contents = await file.read()
        # Parse CSV using pandas
        df = pd.read_csv(StringIO(contents.decode('utf-8')))
        
        # Validate required columns
        required_cols = ["zone", "region", "division", "ccc", "report_month", 
                         "quarterly_nos", "monthly_nos", "smart_meter_nos", "industrial_nos"]
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Missing column in CSV: {col}")

        records_processed = 0
        
        for _, row in df.iterrows():
            doc = {
                "block_id": service.BLOCK_ID,
                "zone": str(row["zone"]).strip(),
                "region": str(row["region"]).strip(),
                "division": str(row["division"]).strip(),
                "ccc": str(row["ccc"]).strip(),
                "report_month": str(row["report_month"]).strip(),
                "topic": "Unbilled nos. of L&MV consumer...",
                "data": [
                    {"category": "Quarterly", "nos": int(row["quarterly_nos"]), "remarks": ""},
                    {"category": "Monthly", "nos": int(row["monthly_nos"]), "remarks": ""},
                    {"category": "Smart Meter", "nos": int(row["smart_meter_nos"]), "remarks": ""},
                    {"category": "Industrial", "nos": int(row["industrial_nos"]), "remarks": ""}
                ],
                "created_by": current["username"],
                "updated_at": datetime.utcnow()
            }

            # Upsert into MongoDB
            service.collection.update_one(
                {
                    "block_id": service.BLOCK_ID,
                    "division": doc["division"], 
                    "ccc": doc["ccc"], 
                    "report_month": doc["report_month"]
                },
                {"$set": doc},
                upsert=True
            )
            records_processed += 1

        return {"message": "Bulk upload successful", "count": records_processed}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def list_reports(current=Depends(get_current_user)):
    service = UnbilledMonitoringService(current, {})
    return service.list_all()