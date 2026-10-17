# backend/app/blocks/puja_load_demand/service.py
"""
PUJALoadDemandService — extends BaseBlockService.

Customizations:
- Auto-generated application_no from date + division + time
- Substation-level load tracking with computed percentages
- Region-wide rollup across all divisions
- Peak load detection
- Cost center management (editable capacities)
- Cascade filtering for division_user role
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)

# Lookup: division name -> division config
DIVISION_MAP = {d["name"]: d for d in CONFIG["divisions"]}


class PUJALoadDemandService(BaseBlockService):
    BLOCK_ID = "puja_load_demand"
    COLLECTION = "puja_load_entries"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)
        # Separate collection for cost centers (substation capacities)
        self.cost_centers = self.db["cost_centers"]

    # ------------------------------------------------------------
    # Access control — cascade by division for division_user
    # ------------------------------------------------------------
    def _view_filter(self) -> dict:
        """
        - super_admin / admin / manager: see all entries
        - division_user: see only entries of their division
        """
        base = {"block_id": self.BLOCK_ID}

        role = self.user.get("role")
        if role in ("super_admin", "admin", "manager"):
            return base

        # division_user — filter by their assigned division
        division = self._get_user_division()
        if not division:
            # Fallback: no division assigned — see nothing
            return {**base, "division": "__none__"}

        return {**base, "division": division}

    def _get_user_division(self) -> Optional[str]:
        """
        Get the division this user belongs to.
        Reads from the users collection by username.
        """
        user_doc = self.db["users"].find_one({"username": self.user["username"]})
        if user_doc:
            return user_doc.get("division")
        return None

    def _can_edit_capacity(self) -> bool:
        return self.user.get("role") in ("super_admin", "admin")

    # ------------------------------------------------------------
    # Create entry — auto-generate application_no
    # ------------------------------------------------------------
    def create(self, body):
        # Division validation
        if body.division not in DIVISION_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid division: {body.division}"
            )

        # If division_user, force their own division
        if self.user.get("role") == "division_user":
            user_div = self._get_user_division()
            if user_div and body.division != user_div:
                raise HTTPException(
                    status_code=403,
                    detail=f"You can only submit entries for your division: {user_div}"
                )

        # Time validation (must be one of the 24 hourly slots)
        if body.time not in CONFIG["time_slots"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time slot: {body.time}. Use HH:00 format."
            )

        # Auto-generate application_no: PLD-YYYY-MM-DD-CODE-HH:MM
        div_code = DIVISION_MAP[body.division]["code"]
        app_no = f"PLD-{body.date}-{div_code}-{body.time}"

        # Duplicate check (same division + date + time)
        existing = self.collection.find_one({
            "block_id": self.BLOCK_ID,
            "application_no": app_no,
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Entry already exists for {body.division} on {body.date} at {body.time}"
            )

        # Compute totals + per-substation percentages
        substations = []
        total_load = 0.0
        total_capacity = 0.0

        for s in body.substations:
            pct = round((s.load_mva / s.capacity_mva * 100), 2) if s.capacity_mva > 0 else 0.0
            substations.append({
                "sl_no": s.sl_no,
                "name": s.name,
                "load_mva": round(s.load_mva, 2),
                "capacity_mva": round(s.capacity_mva, 2),
                "percent": pct,
            })
            total_load += s.load_mva
            total_capacity += s.capacity_mva

        overall_pct = round((total_load / total_capacity * 100), 2) if total_capacity > 0 else 0.0

        # Build stages
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
        stages[0]["status"] = "completed"
        stages[0]["completed_by"] = self.user["username"]
        stages[0]["completed_at"] = datetime.utcnow()
        if len(stages) > 1:
            stages[1]["status"] = "in_progress"
            stages[1]["started_at"] = datetime.utcnow()

        now = datetime.utcnow()
        doc = {
            "block_id": self.BLOCK_ID,
            "application_no": app_no,
            "division": body.division,
            "division_code": div_code,
            "date": body.date,
            "time": body.time,
            "substations": substations,
            "total_load_mva": round(total_load, 2),
            "total_capacity_mva": round(total_capacity, 2),
            "overall_percent": overall_pct,
            "system_report": body.system_report.dict() if body.system_report else {},
            "weather": body.weather or "Normal",
            "system_status": body.system_status or "Normal",
            "remarks": body.remarks or "",
            "current_stage": 1,
            "status": "submitted",
            "stages": stages,
            "created_by": self.user["username"],
            "created_at": now,
            "updated_at": now,
        }

        result = self.collection.insert_one(doc)
        return {
            "id": str(result.inserted_id),
            "application_no": app_no,
        }

    # ------------------------------------------------------------
    # Override update (PUJA has no applicant, has substations instead)
    # ------------------------------------------------------------
    def update(self, app_id: str, body):
        oid = self._to_oid(app_id)
        doc = self.collection.find_one({"_id": oid, "block_id": self.BLOCK_ID})
        if not doc:
            raise HTTPException(status_code=404, detail="Application not found")

        update_data = {}

        if body.substations is not None:
            # Recalculate totals + percentages
            total_load = 0.0
            total_capacity = 0.0
            new_substations = []
            for s in body.substations:
                pct = round((s.load_mva / s.capacity_mva * 100), 2) if s.capacity_mva > 0 else 0.0
                new_substations.append({
                    "sl_no": s.sl_no,
                    "name": s.name,
                    "load_mva": round(s.load_mva, 2),
                    "capacity_mva": round(s.capacity_mva, 2),
                    "percent": pct,
                })
                total_load += s.load_mva
                total_capacity += s.capacity_mva
            
            update_data["substations"] = new_substations
            update_data["total_load_mva"] = round(total_load, 2)
            update_data["total_capacity_mva"] = round(total_capacity, 2)
            update_data["overall_percent"] = round((total_load / total_capacity * 100), 2) if total_capacity > 0 else 0.0

        if body.system_report is not None:
            update_data["system_report"] = body.system_report.dict()
        
        if body.weather is not None:
            update_data["weather"] = body.weather
            
        if body.system_status is not None:
            update_data["system_status"] = body.system_status
            
        if getattr(body, "remarks", None) is not None:
            update_data["remarks"] = body.remarks

        update_data["updated_at"] = datetime.utcnow()

        self.collection.update_one(
            {"_id": oid, "block_id": self.BLOCK_ID},
            {"$set": update_data},
        )
        return {"message": "Updated", "id": app_id}

    # ------------------------------------------------------------
    # Region report — all divisions for a date + time
    # ------------------------------------------------------------
    def region_report(self, date: str, time: str):
        """
        Aggregate all divisions' entries for a specific date + time.
        Returns per-division totals + region grand total.
        """
        entries = list(self.collection.find({
            "block_id": self.BLOCK_ID,
            "date": date,
            "time": time,
        }))

        divisions_data = []
        region_total_load = 0.0
        region_total_capacity = 0.0

        for div_cfg in CONFIG["divisions"]:
            entry = next((e for e in entries if e["division"] == div_cfg["name"]), None)

            if entry:
                load = entry.get("total_load_mva", 0.0)
                capacity = entry.get("total_capacity_mva", 0.0)
                pct = entry.get("overall_percent", 0.0)
                system_status = entry.get("system_status", "Normal")
                weather = entry.get("weather", "Normal")
                entry_id = str(entry["_id"])
                submitted_at = entry.get("created_at")
            else:
                # No entry — use config capacity as placeholder
                capacity = sum(s["capacity_mva"] for s in div_cfg["substations"])
                load = 0.0
                pct = 0.0
                system_status = "—"
                weather = "—"
                entry_id = None
                submitted_at = None

            divisions_data.append({
                "division": div_cfg["name"],
                "division_code": div_cfg["code"],
                "capacity_mva": round(capacity, 2),
                "load_mva": round(load, 2),
                "percent": pct,
                "system_status": system_status,
                "weather": weather,
                "has_entry": entry is not None,
                "entry_id": entry_id,
                "submitted_at": submitted_at,
            })

            region_total_load += load
            region_total_capacity += capacity

        region_pct = round((region_total_load / region_total_capacity * 100), 2) if region_total_capacity > 0 else 0.0

        return {
            "date": date,
            "time": time,
            "divisions": divisions_data,
            "region": {
                "total_capacity_mva": round(region_total_capacity, 2),
                "total_load_mva": round(region_total_load, 2),
                "overall_percent": region_pct,
            },
        }

    # ------------------------------------------------------------
    # Peak load — find max load per substation across all entries for a date
    # ------------------------------------------------------------
    def peak_load(self, date: str):
        """
        For a given date, find the peak load and time for each substation.
        Returns dict keyed by substation name.
        """
        entries = list(self.collection.find({
            "block_id": self.BLOCK_ID,
            "date": date,
        }))

        peaks = {}  # name -> {time, load_mva, percent}

        for entry in entries:
            time = entry.get("time", "")
            for s in entry.get("substations", []):
                name = s["name"]
                load = s.get("load_mva", 0)
                pct = s.get("percent", 0)

                if name not in peaks or load > peaks[name]["load_mva"]:
                    peaks[name] = {
                        "time": time,
                        "load_mva": load,
                        "percent": pct,
                        "division": entry.get("division"),
                    }

        return {
            "date": date,
            "peak_substations": peaks,
        }

    # ------------------------------------------------------------
    # Cost center management
    # ------------------------------------------------------------
    def list_cost_centers(self):
        """Return all cost centers from collection (falls back to config)."""
        docs = list(self.cost_centers.find({"block_id": self.BLOCK_ID}))
        if docs:
            for d in docs:
                d["_id"] = str(d["_id"])
            return {"items": docs, "source": "collection"}
        # Fallback: return config divisions
        return {"items": CONFIG["divisions"], "source": "config"}

    def seed_cost_centers(self):
        """
        One-time seed: copy divisions from config into cost_centers collection.
        Safe to run multiple times — won't duplicate.
        """
        for div_cfg in CONFIG["divisions"]:
            existing = self.cost_centers.find_one({
                "block_id": self.BLOCK_ID,
                "division_code": div_cfg["code"],
            })
            if not existing:
                self.cost_centers.insert_one({
                    "block_id": self.BLOCK_ID,
                    "division": div_cfg["name"],
                    "division_code": div_cfg["code"],
                    "substations": div_cfg["substations"],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
        return {"message": "Cost centers seeded"}

    def update_capacity(self, division_code: str, substation_name: str, capacity_mva: float):
        """Admin only — update capacity for a single substation."""
        if not self._can_edit_capacity():
            raise HTTPException(status_code=403, detail="Only admins can edit capacity")

        cc = self.cost_centers.find_one({
            "block_id": self.BLOCK_ID,
            "division_code": division_code,
        })
        if not cc:
            raise HTTPException(status_code=404, detail="Cost center not found")

        updated = False
        for s in cc["substations"]:
            if s["name"] == substation_name:
                s["capacity_mva"] = capacity_mva
                updated = True
                break

        if not updated:
            raise HTTPException(status_code=404, detail="Substation not found")

        self.cost_centers.update_one(
            {"_id": cc["_id"]},
            {"$set": {"substations": cc["substations"], "updated_at": datetime.utcnow()}},
        )
        return {"message": "Capacity updated", "substation": substation_name}

    def get_config(self):
        """Return config (already includes divisions + time_slots)."""
        return CONFIG