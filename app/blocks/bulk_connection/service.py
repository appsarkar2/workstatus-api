# backend/app/blocks/bulk_connection/service.py
"""
BulkConnectionService — extends BaseBlockService.
Only overrides what's unique to the bulk_connection block.
"""
import json
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException

from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class BulkConnectionService(BaseBlockService):
    BLOCK_ID = "bulk_connection"
    COLLECTION = "bulk_connections"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

    def create(self, body):
        """
        Custom create method to auto-generate a custom traceable ID.
        """
        now = datetime.utcnow()
        date_str = now.strftime("%Y%m%d")
        
        applicant_name = body.applicant.name.strip().upper()
        name_prefix = "".join(e for e in applicant_name if e.isalnum())[:3]
        if not name_prefix:
            name_prefix = "APP"

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        count_today = self.collection.count_documents({
            "block_id": self.BLOCK_ID,
            "created_at": {"$gte": today_start}
        }) + 1
        
        generated_ref_no = f"{name_prefix}-{date_str}-{count_today:03d}"

        stages = []
        for s in CONFIG["stages"]:
            stages.append({
                "stage_no": s["no"],
                "name": s["name"],
                "status": "pending",
                "completed_by": None,
                "completed_at": None,
                "started_at": None,
                "remarks": "",
            })
        
        if stages:
            stages[0]["status"] = "in_progress"
            stages[0]["started_at"] = now

        doc = {
            "block_id": self.BLOCK_ID,
            "application_no": generated_ref_no, 
            "applicant": body.applicant.dict(),
            "division": body.division or "",
            "substation": getattr(body, "substation", ""),
            "application_date": body.application_date or now.strftime("%Y-%m-%d"),
            "documents": body.documents or {},
            
            "proposed_demand_1st": getattr(body, "proposed_demand_1st", ""),
            "proposed_demand_2nd": getattr(body, "proposed_demand_2nd", ""),
            "proposed_demand_3rd": getattr(body, "proposed_demand_3rd", ""),
            "proposed_demand_4th": getattr(body, "proposed_demand_4th", ""),
            "proposed_demand_5th": getattr(body, "proposed_demand_5th", ""),
            
            "edit_count": 0,
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
        return {
            "id": str(result.inserted_id),
            "application_no": generated_ref_no
        }

    def update(self, app_id: str, body):
        """
        Custom update method. Auto-completes Stage 1 for Managers/Admins.
        """
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        update_data = {}

        if body.applicant is not None:
            update_data["applicant"] = body.applicant.dict()
            
        if body.division is not None:
            update_data["division"] = body.division
            
        if getattr(body, "substation", None) is not None:
            update_data["substation"] = body.substation

        if body.documents is not None:
            update_data["documents"] = body.documents
            
        if body.assigned_to is not None:
            update_data["assigned_to"] = body.assigned_to
            
        if body.remarks is not None:
            update_data["remarks"] = body.remarks

        # Handle Proposed Demand updates
        if getattr(body, "proposed_demand_1st", None) is not None:
            update_data["proposed_demand_1st"] = body.proposed_demand_1st
        if getattr(body, "proposed_demand_2nd", None) is not None:
            update_data["proposed_demand_2nd"] = body.proposed_demand_2nd
        if getattr(body, "proposed_demand_3rd", None) is not None:
            update_data["proposed_demand_3rd"] = body.proposed_demand_3rd
        if getattr(body, "proposed_demand_4th", None) is not None:
            update_data["proposed_demand_4th"] = body.proposed_demand_4th
        if getattr(body, "proposed_demand_5th", None) is not None:
            update_data["proposed_demand_5th"] = body.proposed_demand_5th

        # --- AUTO-COMPLETE LOGIC ---
        role = self.user.get("role", "").lower()
        
        # If the user is a Manager, Admin, or Super Admin
        if role in ("manager", "admin", "super_admin"):
            stages = doc.get("stages", [])
            
            for i, stage in enumerate(stages):
                # Check if this is Stage 1 and it's not already completed
                if stage["stage_no"] == 1 and stage["status"] != "completed":
                    print(f"--> [AUTO-ADVANCE] Completing Stage 1 for {self.user['username']}")
                    
                    stages[i]["status"] = "completed"
                    stages[i]["completed_by"] = self.user["username"]
                    stages[i]["completed_at"] = datetime.utcnow()
                    
                    # Move to Stage 2 if it exists
                    if len(stages) > 1 and stages[1]["status"] == "pending":
                        stages[1]["status"] = "in_progress"
                        stages[1]["started_at"] = datetime.utcnow()
                        update_data["current_stage"] = 2
                    
                    update_data["stages"] = stages
                    break

        # Increment the edit counter
        current_count = doc.get("edit_count", 0)
        update_data["edit_count"] = current_count + 1
        update_data["updated_at"] = datetime.utcnow()

        self.collection.update_one(
            {"_id": oid, "block_id": self.BLOCK_ID},
            {"$set": update_data},
        )
        return {"message": "Updated", "id": app_id}