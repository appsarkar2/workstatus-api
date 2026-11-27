# backend/app/blocks/pm_surya_ghar/service.py
import json
from pathlib import Path
import pandas as pd
from fastapi import HTTPException, UploadFile
from datetime import datetime
from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / 'config.json'
if CONFIG_PATH.exists():
    with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
        CONFIG = json.load(f)
else:
    CONFIG = {
        'id': 'pm_surya_ghar',
        'name': 'PM Surya Ghar',
        'active': True
    }


class PMSuryaGharService(BaseBlockService):
    BLOCK_ID = "pm_surya_ghar"
    COLLECTION = "pm_surya_ghar"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)
        try:
            self.collection.create_index([("report_type", 1), ("application_number", 1)], unique=True, background=True)
        except Exception:
            pass

    def detect_report_type_from_columns(self, columns: list) -> str:
        cols_lower = [str(c).strip().lower() for c in columns]
        if any("loan processing bank" in c or "loan availed" in c or "agreement upload date" in c for c in cols_lower):
            return "loan_status"
    async def upload_report(self, file: UploadFile, query_report_type: str = None):
        try:
            filename = file.filename.lower()
            contents = await file.read()
            if filename.endswith(".csv"):
                import io
                df = pd.read_csv(io.BytesIO(contents), dtype=str)
            elif filename.endswith((".xlsx", ".xls")):
                import io
                df = pd.read_excel(io.BytesIO(contents), dtype=str)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format.")
            if df.empty:
                raise HTTPException(status_code=400, detail="Uploaded file is empty.")
            detected_type = self.detect_report_type_from_columns(list(df.columns))
            report_type = query_report_type if query_report_type in ["vendor_stage", "agreement_followup", "loan_status"] else detected_type
            df = df.fillna("")
            inserted, updated = 0, 0
            for _, row in df.iterrows():
                row_dict = row.to_dict()
                app_no, reg_no = "", ""
                for k, v in row_dict.items():
                    k_lower = str(k).strip().lower()
                    val_str = str(v).strip()
                    if "application number" in k_lower or k_lower == "application_number":
                        app_no = val_str
                    elif "registration number" in k_lower or k_lower == "registration_number":
                        reg_no = val_str
                if not app_no:
                    app_no = reg_no
                if not app_no:
                    continue
                cleaned_data = {}
                for k, v in row_dict.items():
                    clean_key = str(k).strip().lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").replace("-", "_")
                    val = str(v).strip() if v is not None else ""
                    if clean_key in ["total_call_attempts", "calls_remaining", "days_pending", "last_call_number", "sl_no"]:
                        try:
                            val = int(float(val)) if val != "" else 0
                        except Exception:
                            pass
                    cleaned_data[clean_key] = val
                cleaned_data["sl_no"] = cleaned_data.get("sl_no", 0)
                cleaned_data["registration_number"] = reg_no or cleaned_data.get("registration_number", "")
                cleaned_data["application_number"] = app_no
                cleaned_data["district"] = cleaned_data.get("district", "")
                cleaned_data["circle_name"] = cleaned_data.get("circle_name", cleaned_data.get("circle", ""))
                cleaned_data["division_name"] = cleaned_data.get("division_name", cleaned_data.get("division", ""))
                cleaned_data["sub_division_name"] = cleaned_data.get("sub_division_name", cleaned_data.get("sub_division", ""))
                
                doc_filter = {"report_type": report_type, "application_number": app_no}
                update_doc = {"$set": {"report_type": report_type, "application_number": app_no, "registration_number": reg_no, "district": cleaned_data.get("district", ""), "circle_name": cleaned_data.get("circle_name", ""), "division_name": cleaned_data.get("division_name", ""), "sub_division_name": cleaned_data.get("sub_division_name", ""), "consumer_number": cleaned_data.get("consumer_number", ""), "consumer_name": cleaned_data.get("consumer_name", ""), "data": cleaned_data, "updated_at": datetime.utcnow(), "uploaded_by": self.user.get("username", "system")}}
                res = self.collection.update_one(doc_filter, update_doc, upsert=True)
                if res.upserted_id: inserted += 1
                else: updated += 1
            return {"status": "success", "report_type": report_type, "inserted": inserted, "updated": updated, "total_processed": inserted + updated}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        if any("15-day window" in c or "call due today" in c or "agreement status" in c or "vendor contact" in c for c in cols_lower):
            return "agreement_followup"
        if any("vendor stage status" in c for c in cols_lower):
            return "vendor_stage"
        return "vendor_stage"

    def get_overview(self):
        overview = {}
        for r in ["vendor_stage", "agreement_followup", "loan_status"]:
            count = self.collection.count_documents({"report_type": r})
            last_doc = self.collection.find_one({"report_type": r}, sort=[("updated_at", -1)])
            overview[r] = {"count": count, "last_updated": last_doc.get("updated_at").isoformat() if last_doc and last_doc.get("updated_at") else None}
        return {"overview": overview}

    def get_filters(self, report_type: str):
        q = {"report_type": report_type}
        return {
            "districts": sorted([str(x) for x in self.collection.distinct("district", q) if x]),
            "circles": sorted([str(x) for x in self.collection.distinct("circle_name", q) if x]),
            "divisions": sorted([str(x) for x in self.collection.distinct("division_name", q) if x]),
            "sub_divisions": sorted([str(x) for x in self.collection.distinct("sub_division_name", q) if x])
        }

    def _build_filter_query(self, report_type: str, filters: dict) -> dict:
        q = {"report_type": report_type}
        if filters.get("district"): q["district"] = {"$regex": filters["district"], "$options": "i"}
        if filters.get("circle"): q["circle_name"] = {"$regex": filters["circle"], "$options": "i"}
        if filters.get("division"): q["division_name"] = {"$regex": filters["division"], "$options": "i"}
        if filters.get("sub_division"): q["sub_division_name"] = {"$regex": filters["sub_division"], "$options": "i"}
        if filters.get("search"):
            s = filters["search"]
            q["$or"] = [{"application_number": {"$regex": s, "$options": "i"}}, {"registration_number": {"$regex": s, "$options": "i"}}, {"consumer_number": {"$regex": s, "$options": "i"}}, {"consumer_name": {"$regex": s, "$options": "i"}}]
        return q

    def get_summary(self, report_type: str, filters: dict = None):
        q = self._build_filter_query(report_type, filters or {})
        total = self.collection.count_documents(q)
        if total == 0: return {"total_records": 0, "kpis": {}, "breakdown": {}, "division_breakdown": []}
        docs = list(self.collection.find(q))
        divs = {}
        for d in docs:
            div = d.get("division_name") or "Unknown Division"
            divs[div] = divs.get(div, 0) + 1
        div_bd = [{"division": k, "count": v} for k, v in sorted(divs.items(), key=lambda x: x[1], reverse=True)]
        
        if report_type == "vendor_stage":
            st_counts = {}
            for d in docs:
                st = d.get("data", {}).get("vendor_stage_status") or "Unspecified"
                st_counts[st] = st_counts.get(st, 0) + 1
            return {"total_records": total, "kpis": {"total": total, "completed": st_counts.get("Completed", 0), "pending": total - st_counts.get("Completed", 0)}, "breakdown": st_counts, "division_breakdown": div_bd}
        elif report_type == "agreement_followup":
            ag_done, due_today, st_counts = 0, 0, {}
            for d in docs:
                dt = d.get("data", {})
                if "done" in str(dt.get("agreement_status", "")).lower() or "yes" in str(dt.get("agreement_status", "")).lower(): ag_done += 1
                if "yes" in str(dt.get("call_due_today", "")).lower() or "true" in str(dt.get("call_due_today", "")).lower(): due_today += 1
                st = dt.get("agreement_status") or "Unspecified"
                st_counts[st] = st_counts.get(st, 0) + 1
            return {"total_records": total, "kpis": {"total": total, "agreement_done": ag_done, "calls_due_today": due_today, "pending_agreement": total - ag_done}, "breakdown": st_counts, "division_breakdown": div_bd}
        elif report_type == "loan_status":
            availed, bank_counts, st_counts = 0, {}, {}
            for d in docs:
                dt = d.get("data", {})
                if "yes" in str(dt.get("loan_availed", "")).lower() or "availed" in str(dt.get("loan_availed", "")).lower(): availed += 1
                bank = dt.get("loan_bank_name") or "Unspecified Bank"
                bank_counts[bank] = bank_counts.get(bank, 0) + 1
                st = dt.get("current_loan_status") or "Unspecified Status"
                st_counts[st] = st_counts.get(st, 0) + 1
            return {"total_records": total, "kpis": {"total": total, "loan_availed": availed, "loan_not_availed": total - availed}, "breakdown": st_counts, "bank_breakdown": bank_counts, "division_breakdown": div_bd}
        return {"total_records": total, "division_breakdown": div_bd}

    def list_records(self, report_type: str, filters: dict = None, page: int = 1, limit: int = 50):
        q = self._build_filter_query(report_type, filters or {})
        total = self.collection.count_documents(q)
        sort_field = [("data.days_pending", -1)] if report_type == "agreement_followup" else [("updated_at", -1)]
        docs = list(self.collection.find(q).sort(sort_field).skip((page - 1) * limit).limit(limit))
        items = []
        for d in docs:
            d["_id"] = str(d["_id"])
            if d.get("updated_at"): d["updated_at"] = d["updated_at"].isoformat()
            items.append(d)
        return {"total": total, "page": page, "limit": limit, "items": items}

    def delete_report_data(self, report_type: str):
        if self.user.get("role") not in ("superadmin", "admin", "super_admin"):
            raise HTTPException(status_code=403, detail="Only superadmin can delete records")
        res = self.collection.delete_many({"report_type": report_type})
        return {"status": "success", "deleted_count": res.deleted_count}
