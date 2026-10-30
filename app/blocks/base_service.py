# backend/app/blocks/base_service.py
"""
BaseBlockService — reusable CRUD logic for all block types.

Each block (bulk_connection, disconnection, etc.) extends this class
and overrides only what's unique to it (BLOCK_ID, COLLECTION).

This eliminates ~150 lines of copy-paste per block.
"""
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db


class BaseBlockService:
    # Subclass MUST override these
    BLOCK_ID = None       # e.g. "bulk_connection"
    COLLECTION = None     # e.g. "bulk_connections"

    def __init__(self, user: dict, config: dict):
        """
        user:   {"username": "...", "role": "..."} — from JWT
        config: loaded config.json for this block
        """
        self.user = user
        self.config = config
        self.db = get_db()
        self.collection = self.db[self.COLLECTION]

    # ------------------------------------------------------------
    # Access control helpers
    # ------------------------------------------------------------
    def _can_view_all(self) -> bool:
        """Roles that see all applications. Others see only assigned."""
        return self.user.get("role") in ("super_admin", "admin", "manager")

    def _view_filter(self) -> dict:
        if self._can_view_all():
            return {"block_id": self.BLOCK_ID}
        return {"block_id": self.BLOCK_ID, "assigned_to": self.user["username"]}

    def _can_delete(self) -> bool:
        return self.user.get("role") in ("super_admin", "admin")

    # ------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------
    def list_all(self, status=None, search=None, zone=None, region=None, division=None):
        """Fetch applications, with optional backend filtering."""
        query = self._view_filter()
        
        if status:
            query["status"] = status
            
        if search:
            query["$or"] = [
                {"application_no": {"$regex": search, "$options": "i"}},
                {"applicant.name": {"$regex": search, "$options": "i"}},
            ]
            
        # --- NEW BACKEND FILTERS ---
        if zone:
            query["zone"] = zone
        if region:
            query["region"] = region
        if division:
            query["division"] = division
        # ---------------------------

        docs = list(self.collection.find(query).sort("created_at", -1))
        for d in docs:
            d["_id"] = str(d["_id"])
        return {"total": len(docs), "items": docs}

    def get_one(self, app_id: str):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")
        doc["_id"] = str(doc["_id"])
        return doc

    def stats(self):
        query = self._view_filter()
        return {
            "total":       self.collection.count_documents(query),
            "in_progress": self.collection.count_documents({**query, "status": "in_progress"}),
            "pending":     self.collection.count_documents({**query, "status": "in_progress"}),
            "completed":   self.collection.count_documents({**query, "status": "completed"}),
            "rejected":    self.collection.count_documents({**query, "status": "rejected"}),
        }

    def get_config(self):
        return self.config

    # ------------------------------------------------------------
    # Create
    # ------------------------------------------------------------
    def create(self, body):
        existing = self.collection.find_one({
            "application_no": body.application_no,
            "block_id": self.BLOCK_ID,
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Application No '{body.application_no}' already exists",
            )

        stages = []
        for s in self.config["stages"]:
            stages.append({
                "stage_no": s["no"],
                "name": s["name"],
                "status": "pending",
                "completed_by": None,
                "completed_at": None,
                "started_at": None,
                "remarks": "",
            })
        stages[0]["status"] = "in_progress"
        stages[0]["started_at"] = datetime.utcnow()

        now = datetime.utcnow()
        doc = {
            "block_id": self.BLOCK_ID,
            "application_no": body.application_no,
            "applicant": body.applicant.dict(),
            "zone": getattr(body, "zone", ""),         # Add fallback for safety
            "region": getattr(body, "region", ""),     # Add fallback for safety
            "division": body.division or "",
            "application_date": body.application_date,
            "documents": body.documents or {},
            "current_stage": 1,
            "status": "in_progress",
            "stages": stages,
            "assigned_to": body.assigned_to,
            "assigned_by": self.user["username"],
            "created_by": self.user["username"],
            "created_at": now,
            "updated_at": now,
        }
        
        # Dynamically copy any extra fields from the Pydantic body 
        # that aren't explicitly handled above (like load_category, application_category)
        body_dict = body.dict()
        for key, val in body_dict.items():
            if key not in doc and key not in ["applicant", "division", "application_date", "documents", "assigned_to"]:
                doc[key] = val

        result = self.collection.insert_one(doc)
        return {"id": str(result.inserted_id), "application_no": body.application_no}

    # ------------------------------------------------------------
    # Update
    # ------------------------------------------------------------
    def update(self, app_id: str, body):
        oid = self._to_oid(app_id)

        update_data = {}
        if body.applicant is not None:
            update_data["applicant"] = body.applicant.dict()
        if getattr(body, "zone", None) is not None:
            update_data["zone"] = body.zone
        if getattr(body, "region", None) is not None:
            update_data["region"] = body.region
        if body.division is not None:
            update_data["division"] = body.division
        if getattr(body, "substation", None) is not None:
            update_data["substation"] = body.substation
        if getattr(body, "connection_type", None) is not None:
            update_data["connection_type"] = body.connection_type
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
            
        if body.documents is not None:
            update_data["documents"] = body.documents
        if body.assigned_to is not None:
            update_data["assigned_to"] = body.assigned_to
        if getattr(body, "remarks", None) is not None:
            update_data["remarks"] = body.remarks
            
        # Copy any other dynamic fields (application_category, load_category)
        body_dict = body.dict(exclude_unset=True)
        for key, val in body_dict.items():
            if key not in update_data and key not in ["applicant", "division", "documents", "assigned_to", "remarks"]:
                update_data[key] = val

        update_data["updated_at"] = datetime.utcnow()

        result = self.collection.update_one(
            {"_id": oid, "block_id": self.BLOCK_ID},
            {"$set": update_data},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"message": "Updated", "id": app_id}

    # ------------------------------------------------------------
    # Stage update (advance workflow)
    # ------------------------------------------------------------
    def update_stage(self, app_id: str, body):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        stages = doc.get("stages", [])
        found = False

        for s in stages:
            if s["stage_no"] == body.stage_no:
                s["status"] = body.status
                s["remarks"] = body.remarks or s.get("remarks", "")

                if body.status == "completed":
                    s["completed_by"] = body.completed_by or self.user["username"]
                    s["completed_at"] = datetime.utcnow()

                    next_stage_no = body.stage_no + 1
                    if next_stage_no <= len(stages):
                        if stages[next_stage_no - 1]["status"] == "pending":
                            stages[next_stage_no - 1]["status"] = "in_progress"
                            stages[next_stage_no - 1]["started_at"] = datetime.utcnow()
                        doc["current_stage"] = next_stage_no
                    else:
                        doc["status"] = "completed"
                elif body.status == "in_progress":
                    if not s.get("started_at"):
                        s["started_at"] = datetime.utcnow()

                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="Stage not found")

        if all(s["status"] in ("completed", "not_applicable") for s in stages):
            doc["status"] = "completed"

        self.collection.update_one(
            {"_id": oid},
            {"$set": {
                "stages": stages,
                "current_stage": doc.get("current_stage", 1),
                "status": doc["status"],
                "updated_at": datetime.utcnow(),
            }},
        )
        return {"message": "Stage updated"}

    # ------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------
    def delete(self, app_id: str):
        if not self._can_delete():
            raise HTTPException(status_code=403, detail="Only admins can delete")
        oid = self._to_oid(app_id)
        result = self.collection.delete_one({"_id": oid, "block_id": self.BLOCK_ID})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"message": "Deleted"}

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------
    @staticmethod
    def _to_oid(app_id: str) -> ObjectId:
        try:
            return ObjectId(app_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")