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

    async def bulk_upload_csv(self, file):
        try:
            self.collection.delete_many({})
            df = pd.read_csv(file.file, dtype=str)
            df.columns = [c.lower() for c in df.columns]
            df = df.fillna("")
            data = df.to_dict('records')
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

        if "reg" in query:
            reg_val = query.pop("reg")
            query["$or"] = [{"reg": reg_val}, {"region": reg_val}]

        total_cases = self.collection.count_documents(query)

        # Pending Count (Has Coll Date)
        pending_count_query = dict(query)
        pending_count_query["$and"] = [
            {"coll_date": {"$ne": None}},
            {"coll_date": {"$ne": ""}},
            {"coll_date": {"$ne": "(null)"}}
        ]
        pending_count = self.collection.count_documents(pending_count_query)

        # Pending Application (No Quotation Issue Date)
        pending_app_query = dict(query)
        pending_app_query["$and"] = [
            {"$or": [
                {"quotation_issue_date": None},
                {"quotation_issue_date": ""},
                {"quotation_issue_date": "(null)"}
            ]}
        ]
        pending_application = self.collection.count_documents(pending_app_query)

        # Pending WO (No WO Creation Date)
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

            # Quotation Delay: QUOTATION_ISSUE_DATE - CREATION_DATE
            if creation_dt and quot_issue_dt:
                diff = (quot_issue_dt - creation_dt).days
                if diff > 0:
                    valid_qtn_delays.append(diff)

            # WO Delay: WO_CREATION_DATE - COLL_DATE
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

        # Aggregation pipeline for Table Data
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
                                "then": 1,
                                "else": 0
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
                                "then": 1,
                                "else": 0
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
                                "then": 1,
                                "else": 0
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

    def get_weekly_deposit_disposal(self, filters: dict = None):
        filters = filters or {}
        query = self._view_filter()

        if filters.get('region'):
            query['region'] = filters['region']
        if filters.get('division'):
            query['division'] = filters['division']
        if filters.get('ccc'):
            query['ccc'] = filters['ccc']

        docs = list(self.collection.find(query, {'weekly_data': 1, 'region': 1, 'division': 1}))

        weekly_aggregates = {}
        for doc in docs:
            w_data = doc.get('weekly_data', [])
            if not isinstance(w_data, list):
                continue
            for entry in w_data:
                if not isinstance(entry, dict):
                    continue
                week = entry.get('week') or entry.get('week_no') or entry.get('period') or 'Unknown'
                deposited = float(entry.get('deposited') or entry.get('deposit') or 0)
                disposed = float(entry.get('disposed') or entry.get('disposal') or 0)

                if week not in weekly_aggregates:
                    weekly_aggregates[week] = {
                        'week': week,
                        'total_deposited': 0.0,
                        'total_disposed': 0.0,
                        'count': 0
                    }
                weekly_aggregates[week]['total_deposited'] += deposited
                weekly_aggregates[week]['total_disposed'] += disposed
                weekly_aggregates[week]['count'] += 1

        result_list = []
        for week, data in sorted(weekly_aggregates.items(), key=lambda x: str(x[0])):
            cnt = data['count'] if data['count'] > 0 else 1
            result_list.append({
                'week': week,
                'avg_deposited': round(data['total_deposited'] / cnt, 2),
                'avg_disposed': round(data['total_disposed'] / cnt, 2),
                'total_deposited': round(data['total_deposited'], 2),
                'total_disposed': round(data['total_disposed'], 2),
                'entries_count': data['count']
            })

        return {'weekly_summary': result_list}