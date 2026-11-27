# backend/app/blocks/electrical_works/service.py
"""
ElectricalWorksService — extends BaseBlockService.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import HTTPException
from bson import ObjectId


from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class ElectricalWorksService(BaseBlockService):
    BLOCK_ID = "electrical_works"
    COLLECTION = "electrical_works"

    # Strict mapping of who can update which stage
    ALLOWED_MAP = {
        "hr_user": [1], 
        "dro_h&r": [1],
        "commerce_manager_1": [2, 4, 5, 6],
        "finance_user": [3], 
        "dro_finance": [3]
    }

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

    def _view_filter(self) -> dict:
        """Electrical Works allows viewing all schemes for authenticated users without filtering by assigned_to."""
        return {"block_id": self.BLOCK_ID}


    def create(self, body):
        now = datetime.utcnow()
        date_str = now.strftime("%Y%m%d")
        
        # Generate custom ID based on Scheme Name or Applicant Name
        name_source = body.scheme_name or body.applicant.name or "APP"
        name_prefix = "".join(e for e in name_source.strip().upper() if e.isalnum())[:3]
        if not name_prefix:
            name_prefix = "ELE"

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        count_today = self.collection.count_documents({
            "block_id": self.BLOCK_ID,
            "created_at": {"$gte": today_start}
        }) + 1
        
        generated_ref_no = f"ELE-{name_prefix}-{date_str}-{count_today:03d}"

        # Build stages with Dynamic SLA target dates
        stages = []
        for s in CONFIG["stages"]:
            target_date = now + timedelta(days=s.get("sla_days", 0))
            stages.append({
                "stage_no": s["no"],
                "name": s["name"],
                "dept": s.get("dept", "Commerce"),
                "status": "pending",
                "target_date": target_date.strftime("%Y-%m-%d"),
                "actual_date": None,
                "is_breached": False,
                "ref_no": "",
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
            "applicant": body.applicant.dict() if body.applicant else {"name": "Electrical Scheme", "contact": "", "address": ""},
            
            # Advanced Scheme Fields
            "phase": getattr(body, "phase", "Phase-I"),
            "zone": getattr(body, "zone", ""),
            "region": getattr(body, "region", ""),
            "division": getattr(body, "division", ""),
            "scheme_head": getattr(body, "scheme_head", ""),
            "voltage_level": getattr(body, "voltage_level", "11 KV"), 
            "related_ss": getattr(body, "related_ss", ""),
            "scheme_name": getattr(body, "scheme_name", ""),
            "existing_parameter": getattr(body, "existing_parameter", ""),
            "proposed_parameter": getattr(body, "proposed_parameter", ""),
            "loading_peak": getattr(body, "loading_peak", ""),
            "major_material": getattr(body, "major_material", ""),
            "priority": getattr(body, "priority", None),
            "taa_no": getattr(body, "taa_no", ""),
            "taa_date": getattr(body, "taa_date", None),
            "taa_value": getattr(body, "taa_value", None),
            "billed_value": getattr(body, "billed_value", None),
            "planning_date": getattr(body, "planning_date", ""),
            "proposal_initiate_date": getattr(body, "proposal_initiate_date", ""),
            "presently_with": getattr(body, "presently_with", ""),
            "target_date": getattr(body, "target_date", ""),
            "eoffice_ref": getattr(body, "eoffice_ref", ""),
            "detailed_status": getattr(body, "detailed_status", ""),
            "status": getattr(body, "status", None) if getattr(body, "status", None) is not None else "Planned",

            "edit_count": 0,
            "current_stage": 1,
            "stages": stages,
            "assigned_to": None,
            "assigned_by": self.user["username"],
            "created_by": self.user["username"],
            "created_at": now,
            "updated_at": now
        }

        result = self.collection.insert_one(doc)
        return {"id": str(result.inserted_id), "application_no": generated_ref_no}

    def update(self, app_id: str, body):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        update_data = {}
        for field in ["phase", "zone", "region", "division", "scheme_head", "voltage_level", "related_ss", 
                      "scheme_name", "existing_parameter", "proposed_parameter", 
                      "loading_peak", "major_material", "priority", "taa_no", "taa_value", 
                      "billed_value", "planning_date", "proposal_initiate_date", "presently_with", "target_date", "eoffice_ref", "detailed_status"]:
            val = getattr(body, field, None)
            if val is not None:
                update_data[field] = val

        if body.applicant is not None:
            update_data["applicant"] = body.applicant.dict()

        current_count = doc.get("edit_count", 0)
        update_data["edit_count"] = current_count + 1
        update_data["updated_at"] = datetime.utcnow()

        self.collection.update_one({"_id": oid, "block_id": self.BLOCK_ID}, {"$set": update_data})
        return {"message": "Updated", "id": app_id}

    def update_scheme(self, scheme_id: str, update_data: dict):
        oid = self._to_oid(scheme_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            # Try raw string id
            doc = self.collection.find_one({"_id": scheme_id, "block_id": self.BLOCK_ID})
            if not doc:
                raise HTTPException(status_code=404, detail="Scheme not found")
            query = {"_id": scheme_id, "block_id": self.BLOCK_ID}
        else:
            query = {"_id": oid, "block_id": self.BLOCK_ID}

        update_data["updated_at"] = datetime.utcnow()
        if "status" in update_data and update_data["status"]:
            update_data["overall_status"] = update_data["status"]
        elif "overall_status" in update_data and update_data["overall_status"]:
            update_data["status"] = update_data["overall_status"]

        if "major_materials" in update_data and update_data["major_materials"] is not None:
            update_data["major_material"] = update_data["major_materials"]
        if "work_status" in update_data and update_data["work_status"] is not None:
            update_data["detailed_status"] = update_data["work_status"]

        current_count = doc.get("edit_count", 0)
        update_data["edit_count"] = current_count + 1

        self.collection.update_one(query, {"$set": update_data})
        updated_doc = self.collection.find_one(query)
        if updated_doc and "_id" in updated_doc:
            updated_doc["_id"] = str(updated_doc["_id"])
        return updated_doc

    def update_status(self, app_id: str, status: str):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")
        
        now = datetime.utcnow()
        self.collection.update_one(
            {"_id": oid, "block_id": self.BLOCK_ID},
            {"$set": {"status": status, "updated_at": now}}
        )
        return {"message": "Status updated successfully", "id": app_id, "status": status}

    def update_stage(self, app_id: str, body):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        role = self.user.get("role", "").lower()
        username = self.user.get("username", "").lower()

        if role not in ("super_admin", "admin", "division_user"):
            allowed_stages = self.ALLOWED_MAP.get(username, [])
            if body.stage_no not in allowed_stages:
                raise HTTPException(status_code=403, detail=f"Not authorized for Stage {body.stage_no}")

        stages = doc.get("stages", [])
        now = datetime.utcnow()
        found = False

        for i, stage in enumerate(stages):
            if stage["stage_no"] == body.stage_no:
                stages[i]["status"] = body.status
                stages[i]["remarks"] = body.remarks or stage.get("remarks", "")
                
                if getattr(body, "ref_no", None): 
                    stages[i]["ref_no"] = body.ref_no
                    
                if getattr(body, "actual_date", None): 
                    stages[i]["actual_date"] = body.actual_date
                    try:
                        target = datetime.strptime(stage["target_date"], "%Y-%m-%d")
                        actual = datetime.strptime(body.actual_date, "%Y-%m-%d")
                        if actual > target: 
                            stages[i]["is_breached"] = True
                    except Exception: 
                        pass
                
                # Save feasibility check for Stage 2
                if body.stage_no == 2:
                    stages[i]["is_feasible"] = getattr(body, "is_feasible", True)

                if body.status == "completed":
                    stages[i]["completed_by"] = self.user["username"]
                    stages[i]["completed_at"] = now
                    
                    # Stop if Not Feasible
                    if body.stage_no == 2 and getattr(body, "is_feasible", True) == False:
                        doc["status"] = "rejected"
                    else:
                        next_stage_no = body.stage_no + 1
                        if next_stage_no <= len(stages):
                            if stages[next_stage_no - 1]["status"] == "pending":
                                stages[next_stage_no - 1]["status"] = "in_progress"
                                stages[next_stage_no - 1]["started_at"] = now
                                next_sla_days = CONFIG["stages"][next_stage_no - 1].get("sla_days", 0)
                                next_target = now + timedelta(days=next_sla_days)
                                stages[next_stage_no - 1]["target_date"] = next_target.strftime("%Y-%m-%d")
                            doc["current_stage"] = next_stage_no
                        else:
                            doc["status"] = "completed"
                found = True
                break

        if not found:
            raise HTTPException(status_code=404, detail="Stage not found")

        self.collection.update_one(
            {"_id": oid}, 
            {"$set": {"stages": stages, "current_stage": doc.get("current_stage", 1), "status": doc["status"], "updated_at": now}}
        )
        return {"message": "Stage updated"}
    def delete(self, scheme_id: str) -> bool:
        if not self._can_delete():
            raise HTTPException(status_code=403, detail="Only admins can delete")
            
        queries = []
        
        # 1. Try ObjectId format
        if ObjectId.is_valid(scheme_id):
            queries.append({"_id": ObjectId(scheme_id), "block_id": self.BLOCK_ID})
        
        # 2. Try raw string format
        queries.append({"_id": scheme_id, "block_id": self.BLOCK_ID})
        queries.append({"id": scheme_id, "block_id": self.BLOCK_ID})
        queries.append({"work_number": scheme_id, "block_id": self.BLOCK_ID})
        queries.append({"application_no": scheme_id, "block_id": self.BLOCK_ID})

        # Execute deletion
        for q in queries:
            result = self.collection.delete_one(q)
            if result.deleted_count > 0:
                return True

        return False


    def get_scheme_overview_table(self, voltage=None, phase=None, zone=None, region=None, division=None, status=None):
        """Calculates grouped stats for the scheme head overview table view, applying filters first."""
        
        user_role = self.user.get("role", "").lower()
        user_division = self.user.get("division", "")
        
        query = {"block_id": self.BLOCK_ID}
        
        # If user is not admin/super_admin, restrict to their division
        if user_role not in ("super_admin", "admin") and user_division:
            query["division"] = user_division
        else:
            if voltage: query["voltage_level"] = voltage
            if phase: query["phase"] = phase
            if zone: query["zone"] = zone
            if region: query["region"] = region
            if division: query["division"] = division

        if status:
            query["status"] = status

        apps = list(self.collection.find(query))
        overview = {}

        for app in apps:
            head = app.get("scheme_head", "Uncategorized")
            
            group_key = head
            
            if group_key not in overview:
                overview[group_key] = {
                    "scheme_head": head,
                    "total": 0, "planning": 0, "proposal": 0, "working": 0, "completed": 0
                }
            
            overview[group_key]["total"] += 1
            st_val = (app.get("status") or "Planned").strip().capitalize()
            
            if st_val == "Completed":
                overview[group_key]["completed"] += 1
            elif st_val == "Working":
                overview[group_key]["working"] += 1
            elif st_val == "Proposal":
                overview[group_key]["proposal"] += 1
            else:
                overview[group_key]["planning"] += 1

        result = []
        for key, stats in overview.items():
            result.append({
                "scheme_head": stats["scheme_head"],
                "category": stats["scheme_head"],
                "total": stats["total"],
                "planning": stats["planning"],
                "proposal": stats["proposal"],
                "working": stats["working"],
                "completed": stats["completed"]
            })
            
        result.sort(key=lambda x: x["scheme_head"])
        return result

    def get_division_overview_table(self, voltage=None, phase=None, zone=None, region=None, division=None, status=None):
        """Calculates grouped stats for the division overview table view, applying filters first."""
        
        user_role = self.user.get("role", "").lower()
        user_division = self.user.get("division", "")
        
        query = {"block_id": self.BLOCK_ID}
        
        # If user is not admin/super_admin, restrict to their division
        if user_role not in ("super_admin", "admin") and user_division:
            query["division"] = user_division
        else:
            if voltage: query["voltage_level"] = voltage
            if phase: query["phase"] = phase
            if zone: query["zone"] = zone
            if region: query["region"] = region
            if division: query["division"] = division

        if status:
            query["status"] = status

        apps = list(self.collection.find(query))
        overview = {}

        for app in apps:
            div = app.get("division", "Unassigned")
            
            group_key = div
            
            if group_key not in overview:
                overview[group_key] = {
                    "division": div,
                    "total": 0, "planning": 0, "proposal": 0, "working": 0, "completed": 0
                }
            
            overview[group_key]["total"] += 1
            st_val = (app.get("status") or "Planned").strip().capitalize()
            
            if st_val == "Completed":
                overview[group_key]["completed"] += 1
            elif st_val in ("Working", "In Progress", "Under Execution"):
                overview[group_key]["working"] += 1
            elif st_val == "Proposal":
                overview[group_key]["proposal"] += 1
            else:
                overview[group_key]["planning"] += 1

        result = []
        for key, stats in overview.items():
            result.append({
                "division": stats["division"],
                "total": stats["total"],
                "planning": stats["planning"],
                "proposal": stats["proposal"],
                "working": stats["working"],
                "completed": stats["completed"]
            })
            
        result.sort(key=lambda x: x["division"])
        return result

    def get_region_overview_table(self, voltage=None, phase=None, zone=None, region=None, division=None, status=None):
        """Calculates grouped stats for the region overview table view, applying filters first."""
        
        user_role = self.user.get("role", "").lower()
        user_division = self.user.get("division", "")
        
        query = {"block_id": self.BLOCK_ID}
        
        if user_role not in ("super_admin", "admin") and user_division:
            query["division"] = user_division
        else:
            if voltage: query["voltage_level"] = voltage
            if phase: query["phase"] = phase
            if zone: query["zone"] = zone
            if region: query["region"] = region
            if division: query["division"] = division

        if status:
            query["status"] = status

        apps = list(self.collection.find(query))
        overview = {}

        for app in apps:
            reg = app.get("region", "Unassigned")
            
            group_key = reg
            
            if group_key not in overview:
                overview[group_key] = {
                    "region": reg,
                    "total": 0, "planning": 0, "proposal": 0, "working": 0, "completed": 0
                }
            
            overview[group_key]["total"] += 1
            st_val = (app.get("status") or "Planned").strip().capitalize()
            
            if st_val == "Completed":
                overview[group_key]["completed"] += 1
            elif st_val in ("Working", "In Progress", "Under Execution"):
                overview[group_key]["working"] += 1
            elif st_val == "Proposal":
                overview[group_key]["proposal"] += 1
            else:
                overview[group_key]["planning"] += 1

        result = []
        for key, stats in overview.items():
            result.append({
                "region": stats["region"],
                "total": stats["total"],
                "planning": stats["planning"],
                "proposal": stats["proposal"],
                "working": stats["working"],
                "completed": stats["completed"]
            })
            
        result.sort(key=lambda x: x["region"])
        return result


    def get_scheme_overview(self):
        """Calculates stats grouped by Scheme Head and Phase."""
        apps = list(self.collection.find({"block_id": self.BLOCK_ID}))
        
        overview = {
            "total": len(apps),
            "completed": len([a for a in apps if a.get("status") == "completed"]),
            "in_progress": len([a for a in apps if a.get("status") == "in_progress"]),
            "scheme_heads": {},
            "phases": {},
            "voltage_levels": {}
        }

        for app in apps:
            head = app.get("scheme_head", "Uncategorized")
            phase = app.get("phase", "Phase-I")
            voltage = app.get("voltage_level", "Misc")
            status = app.get("status", "in_progress")

            if head not in overview["scheme_heads"]:
                overview["scheme_heads"][head] = {"total": 0, "completed": 0}
            overview["scheme_heads"][head]["total"] += 1
            if status == "completed": overview["scheme_heads"][head]["completed"] += 1

            if phase not in overview["phases"]:
                overview["phases"][phase] = 0
            overview["phases"][phase] += 1
            
            if voltage not in overview["voltage_levels"]:
                overview["voltage_levels"][voltage] = 0
            overview["voltage_levels"][voltage] += 1

        return overview