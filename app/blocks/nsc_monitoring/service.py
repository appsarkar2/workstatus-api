# backend/app/blocks/nsc_monitoring/service.py
import json
from pathlib import Path
from datetime import datetime
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
        'id': 'nsc_monitoring',
        'name': 'NSC Monitoring',
        'stages': [
            {'no': 1, 'name': 'Application Received'},
            {'no': 2, 'name': 'Quotation Generated'},
            {'no': 3, 'name': 'Work Order Issued'},
            {'no': 4, 'name': 'Connection Released'}
        ],
        'statuses': ['in_progress', 'completed', 'rejected', 'on_hold']
    }


class NSCMonitoringService(BaseBlockService):
    BLOCK_ID = 'nsc_monitoring'
    COLLECTION = 'nsc_monitoring_cases'

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

    def delete_record(self, record_id: str):
        if not self._can_delete():
            raise HTTPException(status_code=403, detail="Only admins can delete")
        try:
            oid = ObjectId(record_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid record ID format")
        
        result = self.collection.delete_one({"_id": oid})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Record not found")
        return {"message": "Record deleted successfully"}

    def delete_all_records(self):
        if not self._can_delete():
            raise HTTPException(status_code=403, detail="Only admins can delete")
        result = self.collection.delete_many({})
        return {"message": "All records deleted successfully", "deleted_count": result.deleted_count}

    def parse_no_of_poles(self, val) -> int:
        if val is None:
            return 0
        s = str(val).strip().lower()
        if s in ('', '(null)', 'null', 'nan', 'none', '0', '-'):
            return 0
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    async def bulk_upload_csv(self, file):
        try:
            self.collection.delete_many({})
            df = pd.read_csv(file.file, dtype=str)
            
            # Normalize header lookup: match NO_OF_POLES, no_of_poles, or column headers containing pole
            pole_col = None
            for col in df.columns:
                c_clean = col.strip().lower()
                if c_clean == 'no_of_poles' or 'pole' in c_clean:
                    pole_col = col
                    break

            df.columns = [c.lower() for c in df.columns]
            df = df.fillna("")
            records = df.to_dict('records')
            data = []
            for row in records:
                doc = dict(row)
                val = None
                if pole_col:
                    val = row.get(pole_col)
                if val is None:
                    val = row.get('no_of_poles') or row.get('NO_OF_POLES') or 0
                
                no_of_poles = self.parse_no_of_poles(val)
                doc['no_of_poles'] = max(no_of_poles, 0)
                data.append(doc)

            if data:
                self.collection.insert_many(data)
            return {"message": "Data uploaded successfully", "count": len(data)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def get_filter_options(self):
        return {
            "zones": sorted([str(z) for z in self.collection.distinct('zone_name') if z is not None]),
            "regions": sorted([str(r) for r in self.collection.distinct('reg') if r is not None]),
            "divisions": sorted([str(d) for d in self.collection.distinct('divn_name') if d is not None]),
            "cccs": sorted([str(c) for c in self.collection.distinct('supp_off') if c is not None]),
            "classes": sorted([str(cl) for cl in self.collection.distinct('conn_class') if cl is not None]),
            "applicant_types": sorted([str(a) for a in self.collection.distinct("applicant_type") if a and a != "(null)"])
        }

    def get_kpi_dashboard(self, filters: dict = None):
        filters = filters or {}
        query = {}
        group_by = filters.get("group_by", "reg")
        if group_by == "reg":
            group_by = "region"

        if filters.get("zone") and filters["zone"].strip() != "": 
            query["zone"] = {"$regex": filters["zone"].strip(), "$options": "i"}
        if filters.get("reg") and filters["reg"].strip() != "": 
            query["reg"] = {"$regex": filters["reg"].strip(), "$options": "i"}
        if filters.get("divn_name") and filters["divn_name"].strip() != "": 
            query["divn_name"] = {"$regex": filters["divn_name"].strip(), "$options": "i"}
        if filters.get("supp_off") and filters["supp_off"].strip() != "": 
            query["supp_off"] = {"$regex": filters["supp_off"].strip(), "$options": "i"}
        if filters.get("ccc_code") and str(filters["ccc_code"]).strip() != "": 
            query["ccc_code"] = str(filters["ccc_code"]).strip()
        if filters.get("conn_class") and filters["conn_class"].strip() != "": 
            query["conn_class"] = filters["conn_class"].strip()
        if filters.get("applicant_type") and filters["applicant_type"].strip() != "": 
            query["applicant_type"] = {"$regex": filters["applicant_type"].strip(), "$options": "i"}

        pole_type = filters.get("pole_type", "all")
        if pole_type == "pole":
            query["no_of_poles"] = {"$gt": 0}
        elif pole_type == "non_pole":
            query["$or"] = [
                {"no_of_poles": {"$exists": False}},
                {"no_of_poles": None},
                {"no_of_poles": 0},
                {"no_of_poles": "0"}
            ]


        if "reg" in query:
            reg_val = query.pop("reg")
            query["$or"] = [{"reg": reg_val}, {"region": reg_val}]

        total_cases = self.collection.count_documents(query)

        pending_count_query = dict(query)
        pending_count_query["$and"] = [
            {"coll_date": {"$ne": None}},
            {"coll_date": {"$ne": ""}},
            {"coll_date": {"$ne": "(null)"}}
        ]
        pending_count = self.collection.count_documents(pending_count_query)

        pending_app_query = dict(query)
        pending_app_query["$and"] = [
            {"$or": [
                {"quotation_issue_date": None},
                {"quotation_issue_date": ""},
                {"quotation_issue_date": "(null)"}
            ]}
        ]
        pending_application = self.collection.count_documents(pending_app_query)

        pending_wo_query = dict(query)
        pending_wo_query["$and"] = [
            {"$or": [
                {"wo_creation_date": None},
                {"wo_creation_date": ""},
                {"wo_creation_date": "(null)"}
            ]}
        ]
        pending_wo = self.collection.count_documents(pending_wo_query)

        docs = list(self.collection.find(query))

        valid_qtn_delays = []
        valid_wo_delays = []

        for d in docs:
            def parse_dt(val):
                if not val or pd.isna(val):
                    return None
                s = str(val).strip()
                if not s or s.lower() == 'nan' or s.lower() == '(null)':
                    return None
                for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(s[:16], fmt)
                    except ValueError:
                        try:
                            return datetime.strptime(s[:10], fmt)
                        except ValueError:
                            continue
                return None

            creation_dt = parse_dt(d.get('creation_date') or d.get('CREATION_DATE'))
            quot_issue_dt = parse_dt(d.get('quotation_issue_date') or d.get('QUOTATION_ISSUE_DATE'))
            wo_creation_dt = parse_dt(d.get('wo_creation_date') or d.get('WO_CREATION_DATE'))
            coll_dt = parse_dt(d.get('coll_date') or d.get('COLL_DATE') or d.get('connection_date') or d.get('conn_date') or d.get('release_date'))

            if creation_dt and quot_issue_dt:
                diff = (quot_issue_dt - creation_dt).days
                if diff > 0:
                    valid_qtn_delays.append(diff)

            if coll_dt:
                if wo_creation_dt:
                    diff = (wo_creation_dt - coll_dt).days
                    if diff > 0:
                        valid_wo_delays.append(diff)
                else:
                    diff = (datetime.now() - coll_dt).days
                    valid_wo_delays.append(diff)

            d['_id'] = str(d['_id'])

        quotation_delay = round(sum(valid_qtn_delays) / len(valid_qtn_delays), 2) if valid_qtn_delays else 0.00
        wo_delay = round(sum(valid_wo_delays) / len(valid_wo_delays), 2) if valid_wo_delays else 0.00

        total_poles_agg = list(self.collection.aggregate([
            {"$match": query},
            {"$group": {"_id": None, "total_poles": {"$sum": "$no_of_poles"}}}
        ]))
        total_poles = total_poles_agg[0]["total_poles"] if total_poles_agg else 0

        region_pipeline = [
            {"$match": query},
            {
                "$group": {
                    "_id": {"$ifNull": [f"${group_by}", "Unknown"]},
                    "count": {"$sum": 1},
                    "pending_count": {
                        "$sum": {
                            "$cond": {
                                "if": {
                                    "$and": [
                                        {"$ne": ["$coll_date", None]},
                                        {"$ne": ["$coll_date", ""]},
                                        {"$ne": ["$coll_date", "(null)"]}
                                    ]
                                },
                                "then": 1, "else": 0
                            }
                        }
                    },
                    "pending_application": {
                        "$sum": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": ["$quotation_issue_date", None]},
                                        {"$eq": ["$quotation_issue_date", ""]},
                                        {"$eq": ["$quotation_issue_date", "(null)"]}
                                    ]
                                },
                                "then": 1, "else": 0
                            }
                        }
                    },
                    "pending_wo": {
                        "$sum": {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": ["$wo_creation_date", None]},
                                        {"$eq": ["$wo_creation_date", ""]},
                                        {"$eq": ["$wo_creation_date", "(null)"]}
                                    ]
                                },
                                "then": 1, "else": 0
                            }
                        }
                    }
                }
            },
            {"$sort": {"count": -1}}
        ]
        region_data_agg = list(self.collection.aggregate(region_pipeline))
        region_data = [
            {
                "_id": r["_id"] or "Unknown",
                "count": r["count"],
                "pending_count": r.get("pending_count", 0),
                "pending_application": r.get("pending_application", 0),
                "pending_wo": r.get("pending_wo", 0)
            }
            for r in region_data_agg
        ]

        return {
            "total_cases": total_cases,
            "total_poles": total_poles,
            "pending_count": pending_count,
            "pending_wo": pending_wo,
            "pending_application": pending_application,
            "quotation_delay": quotation_delay,
            "wo_delay": wo_delay,
            "conn_delay": 0.00,
            "region_data": region_data
        }

    def get_pending_nsc(self, filters: dict = None):
        filters = filters or {}
        query = self._view_filter()
        query['status'] = {'$ne': 'completed'}

        if filters.get('region'):
            query['region'] = filters['region']
        if filters.get('division'):
            query['division'] = filters['division']
        if filters.get('ccc'):
            query['ccc'] = filters['ccc']
        if filters.get('class_type') or filters.get('class'):
            query['class_type'] = filters.get('class_type') or filters.get('class')
        if filters.get('pole_type') or filters.get('pole'):
            query['pole_type'] = filters.get('pole_type') or filters.get('pole')

        min_delay = filters.get('min_delay')
        max_delay = filters.get('max_delay')
        if min_delay is not None or max_delay is not None:
            delay_query = {}
            if min_delay is not None:
                delay_query['$gte'] = int(min_delay)
            if max_delay is not None:
                delay_query['$lte'] = int(max_delay)
            query['delay_days'] = delay_query

        docs = list(self.collection.find(query).sort('delay_days', -1))
        for d in docs:
            d['_id'] = str(d['_id'])

        return {'total': len(docs), 'items': docs}

    def get_pending_details(self, filters: dict = None):
        filters = filters or {}
        query = {}
        
        if filters.get("zone") and filters["zone"].strip() != "": 
            query["zone"] = {"$regex": filters["zone"].strip(), "$options": "i"}
        if filters.get("reg") and filters["reg"].strip() != "": 
            query["reg"] = {"$regex": filters["reg"].strip(), "$options": "i"}
        if filters.get("divn_name") and filters["divn_name"].strip() != "": 
            query["divn_name"] = {"$regex": filters["divn_name"].strip(), "$options": "i"}
        if filters.get("supp_off") and filters["supp_off"].strip() != "": 
            query["supp_off"] = {"$regex": filters["supp_off"].strip(), "$options": "i"}
        if filters.get("ccc_code") and str(filters["ccc_code"]).strip() != "": 
            query["ccc_code"] = str(filters["ccc_code"]).strip()
        if filters.get("conn_class") and filters["conn_class"].strip() != "": 
            query["conn_class"] = filters["conn_class"].strip()
        if filters.get("applicant_type") and filters["applicant_type"].strip() != "": 
            query["applicant_type"] = {"$regex": filters["applicant_type"].strip(), "$options": "i"}

        if "reg" in query:
            reg_val = query.pop("reg")
            query["$or"] = [{"reg": reg_val}, {"region": reg_val}]
        pole_type = filters.get("pole_type", "all")
        if pole_type == "pole":
            query["no_of_poles"] = {"$gt": 0}
        elif pole_type == "non_pole":
            query["$or"] = [
                {"no_of_poles": {"$exists": False}},
                {"no_of_poles": None},
                {"no_of_poles": 0},
                {"no_of_poles": "0"}
            ]



        status_type = filters.get("status_type")
        
        if status_type == "pending_wo":
            query["$and"] = [
                {"$or": [
                    {"wo_creation_date": None},
                    {"wo_creation_date": ""},
                    {"wo_creation_date": "(null)"}
                ]}
            ]
        elif status_type == "pending_conn":
            query["$and"] = [
                {"$and": [
                    {"coll_date": {"$ne": None}}, 
                    {"coll_date": {"$ne": ""}}, 
                    {"coll_date": {"$ne": "(null)"}}
                ]},
                {"$or": [
                    {"wo_creation_date": None}, 
                    {"wo_creation_date": ""}, 
                    {"wo_creation_date": "(null)"}
                ]}
            ]
        elif status_type == "pending_app":
            query["$and"] = [
                {"$or": [
                    {"quotation_issue_date": None},
                    {"quotation_issue_date": ""},
                    {"quotation_issue_date": "(null)"}
                ]}
            ]

        docs = list(self.collection.find(query))
        results = []

        for d in docs:
            def parse_dt(val):
                if not val or pd.isna(val):
                    return None
                s = str(val).strip()
                if not s or s.lower() == 'nan' or s.lower() == '(null)':
                    return None
                for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                    try:
                        return datetime.strptime(s[:16], fmt)
                    except ValueError:
                        try:
                            return datetime.strptime(s[:10], fmt)
                        except ValueError:
                            continue
                return None

            coll_dt = parse_dt(d.get('coll_date') or d.get('COLL_DATE') or d.get('connection_date') or d.get('conn_date') or d.get('release_date'))
            creation_dt = parse_dt(d.get('creation_date') or d.get('CREATION_DATE'))

            delay_as_on_today = 0
            if coll_dt:
                delay_as_on_today = (datetime.now() - coll_dt).days
            elif creation_dt:
                delay_as_on_today = (datetime.now() - creation_dt).days

            wo_status = "Not Issued"
            wo_date = d.get("wo_creation_date") or d.get("WO_CREATION_DATE")
            if wo_date and str(wo_date).strip() not in ["", "(null)", "None", "nan"]:
                wo_status = "Issued"

            results.append({
                "appl_no": d.get("appl_no") or d.get("APPL_NO") or d.get("application_no"),
                "name": d.get("name") or d.get("NAME") or d.get("applicant_name"),
                "division": d.get("divn_name") or d.get("division"),
                "ccc": d.get("supp_off") or d.get("ccc") or d.get("ccc_code"),
                "creation_date": d.get("creation_date") or d.get("CREATION_DATE"),
                "coll_date": d.get("coll_date") or d.get("COLL_DATE"),
                "wo_creation_date": wo_date,
                "agency_name": d.get("agency_name") or d.get("AGENCY_NAME") or "-",
                "wo_status": wo_status,
                "delay_as_on_today": delay_as_on_today
            })

        # Sort by delay_as_on_today in descending order (highest delay first)
        results = sorted(results, key=lambda x: x["delay_as_on_today"], reverse=True)

        return {"total": len(results), "items": results}