# backend/app/blocks/interruption_report/service.py
import json
from pathlib import Path
import pandas as pd
from fastapi import HTTPException
from bson import ObjectId
from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / 'config.json'
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {
        'id': 'interruption_report',
        'name': 'Interruption Report',
        'active': True
    }


class InterruptionReportService(BaseBlockService):
    BLOCK_ID = "interruption_report"
    COLLECTION = "interruption_reports"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

    async def bulk_upload_csv(self, file):
        try:
            self.collection.delete_many({})
            df = pd.read_csv(file.file, dtype=str)
            df.columns = [c.strip().lower() for c in df.columns]
            df = df.fillna("")
            data = df.to_dict('records')
            if data:
                self.collection.insert_many(data)
            return {"message": "Data uploaded successfully", "count": len(data)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def get_dashboard_data(self, filters: dict = None):
        filters = filters or {}
        query = {}

        if filters.get("zone") and filters["zone"].strip() != "":
            query["zone"] = {"$regex": filters["zone"], "$options": "i"}
        if filters.get("region") and filters["region"].strip() != "":
            query["region"] = {"$regex": filters["region"], "$options": "i"}
        if filters.get("division") and filters["division"].strip() != "":
            query["division"] = {"$regex": filters["division"], "$options": "i"}
        if filters.get("substation") and filters["substation"].strip() != "":
            query["substation"] = {"$regex": filters["substation"], "$options": "i"}

        docs = list(self.collection.find(query))

        total_feeders = len(docs)
        
        def parse_float(val):
            try:
                return float(str(val).strip())
            except Exception:
                return 0.0

        def parse_int(val):
            try:
                return int(float(str(val).strip()))
            except Exception:
                return 0

        daily_outages = [parse_float(d.get("daily_outage") or d.get("daily_outage_hours") or d.get("outage_hours") or 0) for d in docs]
        monthly_outages = [parse_float(d.get("monthly_outage") or d.get("monthly_outage_hours") or 0) for d in docs]
        yearly_outages = [parse_float(d.get("yearly_outage") or d.get("yearly_outage_hours") or d.get("yearly") or 0) for d in docs]

        avg_daily_outage = round(sum(daily_outages) / total_feeders, 2) if total_feeders > 0 else 0.0
        
        min_monthly = min(monthly_outages) if monthly_outages else 0.0
        max_monthly = max(monthly_outages) if monthly_outages else 0.0
        monthly_range = f"{min_monthly} - {max_monthly}"

        avg_yearly = round(sum(yearly_outages) / total_feeders, 2) if total_feeders > 0 else 0.0

        concern_feeders = 0
        feeders_list = []

        for d in docs:
            d_out = parse_float(d.get("daily_outage") or d.get("daily_outage_hours") or d.get("outage_hours") or 0)
            m_out = parse_float(d.get("monthly_outage") or d.get("monthly_outage_hours") or 0)
            y_out = parse_float(d.get("yearly_outage") or d.get("yearly_outage_hours") or 0)
            trips = parse_int(d.get("trips") or d.get("trip_count") or 0)
            
            is_concern = False
            if trips > 5 or d_out > 4.0 or str(d.get("concern", "")).lower() in ["true", "1", "yes"]:
                is_concern = True
                concern_feeders += 1

            feeders_list.append({
                "id": str(d.get("_id")),
                "feeder_name": d.get("feeder_name") or d.get("feeder") or d.get("name") or "Unknown Feeder",
                "substation": d.get("substation") or d.get("sub_station") or "-",
                "division": d.get("division") or d.get("divn_name") or "-",
                "daily_outage": d_out,
                "monthly_outage": m_out,
                "yearly_outage": y_out,
                "trips": trips,
                "is_concern": is_concern
            })

        feeders_list = sorted(feeders_list, key=lambda x: x["daily_outage"], reverse=True)

        return {
            "total_feeders": total_feeders,
            "avg_daily_outage": avg_daily_outage,
            "monthly_range": monthly_range,
            "avg_yearly": avg_yearly,
            "concern_feeders": concern_feeders,
            "feeders": feeders_list
        }

    def get_filter_options(self):
        zones = sorted([str(z) for z in self.collection.distinct('zone') if z is not None and str(z).strip() != ""])
        regions = sorted([str(r) for r in self.collection.distinct('region') if r is not None and str(r).strip() != ""])
        divisions = sorted([str(d) for d in self.collection.distinct('division') if d is not None and str(d).strip() != ""])
        substations = sorted([str(s) for s in self.collection.distinct('substation') if s is not None and str(s).strip() != ""])
        
        return {
            "zones": zones,
            "regions": regions,
            "divisions": divisions,
            "substations": substations
        }

    def get_pending_details(self, filters: dict = None):
        data = self.get_dashboard_data(filters)
        feeders = data.get("feeders", [])
        return {"total": len(feeders), "items": feeders}