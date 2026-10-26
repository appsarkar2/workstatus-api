# backend/app/blocks/electrical_works/service.py
"""
ElectricalWorksService — extends BaseBlockService.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import HTTPException

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
            "applicant": body.applicant.dict(),
            
            # Advanced Scheme Fields
            "phase": body.phase,
            "zone": body.zone,
            "region": body.region,
            "division": body.division,
            "scheme_head": body.scheme_head,
            "voltage_level": body.voltage_level, 
            "related_ss": body.related_ss,
            "scheme_name": body.scheme_name,
            "existing_parameter": body.existing_parameter,
            "proposed_parameter": body.proposed_parameter,
            "loading_peak": body.loading_peak,
            "major_material": body.major_material,
            "priority": body.priority,
            "taa_no": body.taa_no,
            "taa_value": body.taa_value,
            "billed_value": body.billed_value,
            "presently_with": body.presently_with,
            "target_date": body.target_date,
            "eoffice_ref": body.eoffice_ref,
            "detailed_status": body.detailed_status,

            "edit_count": 0,
            "current_stage": 1,
            "status": "in_progress",
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
                      "billed_value", "presently_with", "target_date", "eoffice_ref", "detailed_status"]:
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

    def get_scheme_overview_table(self, voltage=None, phase=None, zone=None, region=None, division=None):
        """Calculates grouped stats for the data table view, applying filters first."""
        
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

        apps = list(self.collection.find(query))
        overview = {}

        for app in apps:
            head = app.get("scheme_head", "Uncategorized")
            div = app.get("division", "Unassigned")
            
            group_key = f"{head}|||{div}" 
            
            if group_key not in overview:
                overview[group_key] = {
                    "scheme_head": head,
                    "division": div,
                    "total": 0, "completed": 0, "in_progress": 0, "pending": 0, "last_updated": None
                }
            
            overview[group_key]["total"] += 1
            status = app.get("status", "in_progress")
            
            if status == "completed":
                overview[group_key]["completed"] += 1
            elif status == "in_progress":
                overview[group_key]["in_progress"] += 1
            else:
                overview[group_key]["pending"] += 1
                
            upd = app.get("updated_at")
            if upd and (overview[group_key]["last_updated"] is None or upd > overview[group_key]["last_updated"]):
                overview[group_key]["last_updated"] = upd

        result = []
        for key, stats in overview.items():
            pct = round((stats["completed"] / stats["total"]) * 100) if stats["total"] > 0 else 0
            result.append({
                "scheme_head": stats["scheme_head"],
                "division": stats["division"],
                "total": stats["total"],
                "completed": stats["completed"],
                "in_progress": stats["in_progress"],
                "pending": stats["pending"],
                "progress_pct": pct,
                "last_updated": stats["last_updated"].strftime("%d/%m/%Y %I:%M %p") if stats["last_updated"] else "N/A"
            })
            
        result.sort(key=lambda x: (x["scheme_head"], x["division"]))
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