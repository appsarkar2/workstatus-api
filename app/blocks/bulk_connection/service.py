import json
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from fastapi import HTTPException
from app.database import get_db

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class BulkConnectionService:
    BLOCK_ID = "bulk_connection"

    def __init__(self, user: dict):
        self.user = user
        self.db = get_db()
        self.collection = self.db["bulk_connections"]

    def _can_view_all(self) -> bool:
        return self.user.get("role") in ("super_admin", "admin", "manager")

    def _view_filter(self) -> dict:
        if self._can_view_all():
            return {"block_id": self.BLOCK_ID}
        return {"block_id": self.BLOCK_ID, "assigned_to": self.user["username"]}

    def list_all(self, status=None, search=None):
        query = self._view_filter()
        if status:
            query["status"] = status
        if search:
            query["$or"] = [
                {"application_no": {"$regex": search, "$options": "i"}},
                {"applicant.name": {"$regex": search, "$options": "i"}},
            ]
        docs = list(self.collection.find(query).sort("created_at", -1))
        for d in docs:
            d["_id"] = str(d["_id"])
        return {"total": len(docs), "items": docs}

    def get_one(self, app_id):
        try:
            oid = ObjectId(app_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")
        doc["_id"] = str(doc["_id"])
        return doc

    def create(self, body):
        existing = self.collection.find_one({
            "application_no": body.application_no,
            "block_id": self.BLOCK_ID,
        })
        if existing:
            raise HTTPException(status_code=400, detail="Application No already exists")
        stages = []
        for s in CONFIG["stages"]:
            stages.append({
                "stage_no": s["no"],
                "name": s["name"],
                "status": "pending",
                "completed_by": None,
                "completed_at": None,
                "remarks": "",
            })
        stages[0]["status"] = "in_progress"
        stages[0]["started_at"] = datetime.utcnow()
        now = datetime.utcnow()
        doc = {
            "block_id": self.BLOCK_ID,
            "application_no": body.application_no,
            "applicant": body.applicant.dict(),
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
        result = self.collection.insert_one(doc)
        return {"id": str(result.inserted_id), "application_no": body.application_no}

    def update(self, app_id, body):
        try:
            oid = ObjectId(app_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")
        update_data = {}
        if body.applicant:
            update_data["applicant"] = body.applicant.dict()
        if body.division is not None:
            update_data["division"] = body.division
        if body.documents is not None:
            update_data["documents"] = body.documents
        if body.assigned_to is not None:
            update_data["assigned_to"] = body.assigned_to
        if body.remarks is not None:
            update_data["remarks"] = body.remarks
        update_data["updated_at"] = datetime.utcnow()
        result = self.collection.update_one(
            {"_id": oid, "block_id": self.BLOCK_ID},
            {"$set": update_data},
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"message": "Updated", "id": app_id}

    def update_stage(self, app_id, body):
        try:
            oid = ObjectId(app_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Not found")
        stages = doc.get("stages", [])
        found = False
        for s in stages:
            if s["stage_no"] == body.stage_no:
                s["status"] = body.status
                s["remarks"] = body.remarks or s.get("remarks", "")
                if body.status == "completed":
                    s["completed_by"] = body.completed_by or self.user["username"]
                    s["completed_at"] = datetime.utcnow()
                    next_stage = body.stage_no + 1
                    if next_stage <= len(stages):
                        if stages[next_stage - 1]["status"] == "pending":
                            stages[next_stage - 1]["status"] = "in_progress"
                        doc["current_stage"] = next_stage
                    else:
                        doc["status"] = "completed"
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
                "current_stage": doc.get("current_stage", doc["current_stage"]),
                "status": doc["status"],
                "updated_at": datetime.utcnow(),
            }},
        )
        return {"message": "Stage updated"}

    def delete(self, app_id):
        if self.user.get("role") not in ("super_admin", "admin"):
            raise HTTPException(status_code=403, detail="Only admins can delete")
        try:
            oid = ObjectId(app_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")
        result = self.collection.delete_one({"_id": oid, "block_id": self.BLOCK_ID})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"message": "Deleted"}

    def stats(self):
        query = self._view_filter()
        return {
            "total": self.collection.count_documents(query),
            "in_progress": self.collection.count_documents({**query, "status": "in_progress"}),
            "completed": self.collection.count_documents({**query, "status": "completed"}),
            "rejected": self.collection.count_documents({**query, "status": "rejected"}),
        }

    def get_config(self):
        return CONFIG

