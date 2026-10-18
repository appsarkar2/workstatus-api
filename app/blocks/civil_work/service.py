from datetime import datetime
from app.blocks.base_service import BaseBlockService
from fastapi import HTTPException

class CivilWorkService(BaseBlockService):
    BLOCK_ID = "civil_work"
    COLLECTION = "civil_work_entries"

    def create(self, body):
        # Check for duplicate project names
        if self.collection.find_one({"applicant.name": body.applicant.name, "block_id": self.BLOCK_ID}):
            raise HTTPException(status_code=400, detail="Project name already exists")

        # Auto-generate a Project ID: CIV-2026-001
        current_year = datetime.utcnow().year
        count = self.collection.count_documents({"block_id": self.BLOCK_ID}) + 1
        generated_app_no = f"CIV-{current_year}-{count:03d}"

        # Set up standard stages from config.json
        stages = [{"stage_no": s["no"], "name": s["name"], "status": "pending", "completed_by": None, "completed_at": None, "started_at": None, "remarks": ""} for s in self.config["stages"]]
        stages[0]["status"] = "in_progress"
        stages[0]["started_at"] = datetime.utcnow()
        
        now = datetime.utcnow()
        
        # Build the document for MongoDB
        doc = {
            "block_id": self.BLOCK_ID, 
            "application_no": generated_app_no, 
            "applicant": body.applicant.dict(), 
            
            # New Civil Work specific fields
            "work_type": body.work_type,
            "zone": body.zone,
            "region": body.region,
            "division": body.division,
            "location_type": body.location_type,
            "location_name": body.location_name,
            
            "application_date": body.application_date or now.strftime("%Y-%m-%d"),
            "documents": body.documents or {}, 
            "current_stage": 1, 
            "status": "in_progress", 
            "stages": stages, 
            "assigned_to": body.assigned_to, 
            "assigned_by": self.user["username"], 
            "created_by": self.user["username"], 
            "created_at": now, 
            "updated_at": now
        }
        
        result = self.collection.insert_one(doc)
        return {"id": str(result.inserted_id), "application_no": generated_app_no}