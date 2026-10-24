# backend/app/blocks/bulk_connection/service.py
"""
BulkConnectionService — extends BaseBlockService.
Only overrides what's unique to the bulk_connection block.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import HTTPException

from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class BulkConnectionService(BaseBlockService):
    BLOCK_ID = "bulk_connection"
    COLLECTION = "bulk_connections"

    # Strict mapping of usernames to allowed stages
    ALLOWED_MAP = {
        "hr_user": [1],
        "dro_h&r": [1],
        "commerce_manager_1": [2, 3],
        "commerce_manager_2": [5, 6, 7, 8],
        "commerce_manager_3": [9, 10, 11, 12, 13],
        "finance_user": [4],
        "dro_finance": [4]
    }

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

    def create(self, body):
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
            "division": body.division or "",
            "substation": getattr(body, "substation", ""),
            "connection_type": getattr(body, "connection_type", "Procedure-A"),
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
        return {"id": str(result.inserted_id), "application_no": generated_ref_no}

    def update(self, app_id: str, body):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        update_data = {}
        if body.applicant is not None: update_data["applicant"] = body.applicant.dict()
        if body.division is not None: update_data["division"] = body.division
        if getattr(body, "substation", None) is not None: update_data["substation"] = body.substation
        if getattr(body, "connection_type", None) is not None: update_data["connection_type"] = body.connection_type
        if body.documents is not None: update_data["documents"] = body.documents
        if body.assigned_to is not None: update_data["assigned_to"] = body.assigned_to
        if body.remarks is not None: update_data["remarks"] = body.remarks

        if getattr(body, "proposed_demand_1st", None) is not None: update_data["proposed_demand_1st"] = body.proposed_demand_1st
        if getattr(body, "proposed_demand_2nd", None) is not None: update_data["proposed_demand_2nd"] = body.proposed_demand_2nd
        if getattr(body, "proposed_demand_3rd", None) is not None: update_data["proposed_demand_3rd"] = body.proposed_demand_3rd
        if getattr(body, "proposed_demand_4th", None) is not None: update_data["proposed_demand_4th"] = body.proposed_demand_4th
        if getattr(body, "proposed_demand_5th", None) is not None: update_data["proposed_demand_5th"] = body.proposed_demand_5th

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

        if role not in ("super_admin", "admin"):
            allowed_stages = self.ALLOWED_MAP.get(username, [])
            if body.stage_no not in allowed_stages:
                raise HTTPException(status_code=403, detail=f"Not authorized for Stage {body.stage_no}")

        # --- VALIDATION: Sub-station required before Stage 2 completion ---
        if body.stage_no == 2 and body.status == "completed":
            substation = doc.get("substation", "").strip()
            if not substation:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot complete Stage 2 without a Sub-station. Please use 'Edit Details' to assign a Sub-station first."
                )
        # -----------------------------------------------------------------

        stages = doc.get("stages", [])
        now = datetime.utcnow()
        found = False

        for i, stage in enumerate(stages):
            if stage["stage_no"] == body.stage_no:
                stages[i]["status"] = body.status
                stages[i]["remarks"] = body.remarks or stage.get("remarks", "")
                
                if getattr(body, "ref_no", None): stages[i]["ref_no"] = body.ref_no
                if getattr(body, "actual_date", None): 
                    stages[i]["actual_date"] = body.actual_date
                    try:
                        target = datetime.strptime(stage["target_date"], "%Y-%m-%d")
                        actual = datetime.strptime(body.actual_date, "%Y-%m-%d")
                        if actual > target: stages[i]["is_breached"] = True
                    except Exception: pass
                
                # --- SAVE STAGE 2 SPECIFIC DATA ---
                if body.stage_no == 2:
                    stages[i]["inspection_date"] = getattr(body, "inspection_date", None)
                    stages[i]["eoffice_date"] = getattr(body, "eoffice_date", None) # <-- SAVED HERE
                    stages[i]["is_feasible"] = getattr(body, "is_feasible", True)
                # ----------------------------------

                if getattr(body, "deposit_amount", None): stages[i]["deposit_amount"] = body.deposit_amount
                if getattr(body, "quotation_amount", None): stages[i]["quotation_amount"] = body.quotation_amount

                if body.status == "completed":
                    stages[i]["completed_by"] = self.user["username"]
                    stages[i]["completed_at"] = now
                    
                    # --- HANDLE FEASIBILITY (If Not Feasible, reject and STOP) ---
                    if body.stage_no == 2 and getattr(body, "is_feasible", True) == False:
                        doc["status"] = "rejected"
                    # -------------------------------------------------------------
                    else:
                        # Normal progression to next stage
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

    def get_sla_report(self):
        apps = list(self.collection.find({"block_id": self.BLOCK_ID}))
        report = {"summary": {"total_breaches": 0, "departments": {}, "users": {}}, "details": []}
        now = datetime.utcnow()

        for app in apps:
            app_breaches = []
            total_delay = 0
            
            for stage in app.get("stages", []):
                delay_days = 0
                is_breached = False
                user = "—"
                status = stage.get("status")
                target_str = stage.get("target_date")
                if not target_str: continue
                    
                try:
                    target = datetime.strptime(target_str, "%Y-%m-%d")
                    if status == "completed" and stage.get("is_breached"):
                        actual_str = stage.get("actual_date")
                        if actual_str:
                            actual = datetime.strptime(actual_str, "%Y-%m-%d")
                            delay_days = (actual - target).days
                            is_breached = True
                            user = stage.get("completed_by", "Unknown")
                    elif status == "in_progress" and now.date() > target.date():
                        delay_days = (now.date() - target.date()).days
                        is_breached = True
                        user = f"Pending ({stage.get('dept', 'Dept')})" 
                        
                    if is_breached and delay_days > 0:
                        dept = stage.get("dept", "Unknown")
                        report["summary"]["total_breaches"] += 1
                        if dept not in report["summary"]["departments"]: report["summary"]["departments"][dept] = {"breaches": 0, "total_delay_days": 0}
                        report["summary"]["departments"][dept]["breaches"] += 1
                        report["summary"]["departments"][dept]["total_delay_days"] += delay_days
                        if user not in report["summary"]["users"]: report["summary"]["users"][user] = {"breaches": 0, "total_delay_days": 0}
                        report["summary"]["users"][user]["breaches"] += 1
                        report["summary"]["users"][user]["total_delay_days"] += delay_days
                        app_breaches.append({"stage_no": stage["stage_no"], "stage_name": stage["name"], "dept": dept, "user": user, "delay_days": delay_days, "status": status})
                        total_delay += delay_days
                except Exception:
                    continue

            if app_breaches:
                report["details"].append({
                    "app_id": str(app["_id"]),
                    "application_no": app.get("application_no", "Unknown"),
                    "applicant_name": app.get("applicant", {}).get("name", "Unknown"),
                    "division": app.get("division", "Unknown"),
                    "zone": app.get("zone", "Unknown"),
                    "connection_type": app.get("connection_type", "Unknown"),
                    "voltage_class": app.get("voltage_class", "Unknown"),
                    "total_delay": total_delay,
                    "breaches": app_breaches
                })

        report["details"].sort(key=lambda x: x["total_delay"], reverse=True)
        return report

    def get_stage_sla_summary(self):
        apps = list(self.collection.find({"block_id": self.BLOCK_ID, "status": "in_progress"}))
        now = datetime.utcnow()
        summary = {}

        for app in apps:
            for stage in app.get("stages", []):
                stage_no = stage.get("stage_no")
                status = stage.get("status")
                target_str = stage.get("target_date")

                if status == "in_progress" and target_str:
                    try:
                        target = datetime.strptime(target_str, "%Y-%m-%d")
                        if now.date() > target.date():
                            delay_days = (now.date() - target.date()).days
                            if stage_no not in summary: summary[stage_no] = {"breached": 0, "total_delay": 0}
                            summary[stage_no]["breached"] += 1
                            summary[stage_no]["total_delay"] += delay_days
                    except Exception:
                        pass

        return summary