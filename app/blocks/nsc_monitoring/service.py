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


    # Applications WITH a valid work order (Pending Connection WO Issued):
VALID_WON_FILTER = {
    "won": {
        "$exists": True,
        "$nin": [None, "", " ", "(null)", "null", "NULL", "None", "-", "N/A", "won", "WON"]
    }
}


# Applications WITHOUT a valid work order (Pending WO):
NO_WON_FILTER = {
    "$or": [
        {"won": None},
        {"won": {"$in": ["", " ", "(null)", "null", "NULL", "None", "NONE", "-", "N/A", "n/a", "won", "WON"]}},
        {"won": {"$exists": False}}
    ]
}


class NSCMonitoringService(BaseBlockService):
    BLOCK_ID = 'nsc_monitoring'
    COLLECTION = 'nsc_monitoring_cases'

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)

        # Ensure required database indexes for high performance load times
        try:
            self.collection.create_index([("zone", 1), ("reg", 1), ("divn_name", 1)])
            self.collection.create_index([("status", 1)])
            self.collection.create_index([("coll_date", 1)])
            self.collection.create_index([("no_of_poles", 1)])
        except Exception:
            pass
    def get_filter_options(self):
        try:
            classes = sorted([str(c) for c in self.collection.distinct('conn_class') if c is not None and str(c).strip() != ""])
            applicant_types = sorted([str(a) for a in self.collection.distinct('applicant_type') if a is not None and str(a).strip() != ""])
            return {
                "classes": classes,
                "applicant_types": applicant_types
            }
        except Exception as e:
            print(f"Error in get_filter_options: {e}")
            return {
                "classes": [],
                "applicant_types": []
            }

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

    def parse_won(self, val):
        if val is None:
            return None
        s = str(val).strip()
        if s.lower() in ["", "(null)", "null", "none", "-", "n/a", "won"]:
            return None
        return s

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

    def parse_coll_date(self, val):
        if not val or str(val).strip().lower() in ('', '(null)', 'null', 'none', '-', 'nan'):
            return None
        s = str(val).strip()
        for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                try:
                    return datetime.strptime(s[:10], fmt)
                except ValueError:
                    continue
        return None

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

            coll_col = None
            for col in df.columns:
                c_clean = col.strip().lower()
                if c_clean == 'coll_date' or 'coll' in c_clean or 'deposit' in c_clean:
                    coll_col = col
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

                c_val = None
                if coll_col:
                    c_val = row.get(coll_col.lower())
                if not c_val:
                    c_val = row.get('coll_date') or row.get('connection_date') or row.get('conn_date') or row.get('release_date')
                
                doc['coll_date'] = self.parse_coll_date(c_val)

                # Parse creation_date, quotation_issue_date, and wo_creation_date
                creation_val = row.get('creation_date') or row.get('CREATION_DATE') or row.get('application_date')
                doc['creation_date'] = self.parse_coll_date(creation_val)

                quot_val = row.get('quotation_issue_date') or row.get('QUOTATION_ISSUE_DATE')
                doc['quotation_issue_date'] = self.parse_coll_date(quot_val)

                wo_creation_val = row.get('wo_creation_date') or row.get('WO_CREATION_DATE') or row.get('work_order_creation_date')
                doc['wo_creation_date'] = self.parse_coll_date(wo_creation_val)

                raw_won = str(row.get("won") or row.get("WON") or "").strip()
                if raw_won.lower() in ["", "(null)", "null", "none", "-", "n/a"]:
                    doc['won'] = None
                else:
                    doc['won'] = raw_won

                data.append(doc)

            if data:
                self.collection.insert_many(data)
            
            # Store metadata in db['block_metadata']
            meta_coll = self.db["block_metadata"]
            now_iso = datetime.now().isoformat()
            
            # Find data_as_on (maximum date in dataset across coll_date, creation_date, etc.)
            max_dt = None
            for d in data:
                for date_key in ['coll_date', 'creation_date', 'CREATION_DATE', 'connection_date', 'conn_date', 'release_date']:
                    val = d.get(date_key)
                    if isinstance(val, datetime):
                        if max_dt is None or val > max_dt:
                            max_dt = val
                    elif val and str(val).strip() not in ("", "(null)", "None", "nan"):
                        parsed = self.parse_coll_date(val)
                        if parsed and (max_dt is None or parsed > max_dt):
                            max_dt = parsed

            data_as_on_str = max_dt.strftime("%d/%m/%Y") if max_dt else datetime.now().strftime("%d/%m/%Y")

            meta_coll.update_one(
                {"block_id": self.BLOCK_ID},
                {
                    "$set": {
                        "block_id": self.BLOCK_ID,
                        "last_uploaded_at": now_iso,
                        "data_as_on": data_as_on_str,
                        "total_records": len(data)
                    }
                },
                upsert=True
            )

            return {"message": "Data uploaded successfully", "count": len(data), "last_uploaded_at": now_iso, "data_as_on": data_as_on_str}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def _build_query(self, filters: dict) -> dict:
        filters = filters or {}
        query = {}
        
        if filters.get("zone") and str(filters["zone"]).strip() != "": 
            query["zone"] = {"$regex": str(filters["zone"]).strip(), "$options": "i"}
        if filters.get("reg") and str(filters["reg"]).strip() != "": 
            query["reg"] = {"$regex": str(filters["reg"]).strip(), "$options": "i"}
        if filters.get("divn_name") and str(filters["divn_name"]).strip() != "": 
            query["divn_name"] = {"$regex": str(filters["divn_name"]).strip(), "$options": "i"}
        if filters.get("supp_off") and str(filters["supp_off"]).strip() != "": 
            query["supp_off"] = {"$regex": str(filters["supp_off"]).strip(), "$options": "i"}
        if filters.get("ccc_code") and str(filters["ccc_code"]).strip() != "": 
            query["ccc_code"] = str(filters["ccc_code"]).strip()
        if filters.get("conn_class") and str(filters["conn_class"]).strip() != "": 
            query["conn_class"] = str(filters["conn_class"]).strip()
        if filters.get("applicant_type") and str(filters["applicant_type"]).strip() != "": 
            query["applicant_type"] = {"$regex": str(filters["applicant_type"]).strip(), "$options": "i"}

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

        appl_no_filter = {
            "$or": [
                {"appl_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"APPL_NO": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"application_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}}
            ]
        }
        if query:
            query = {"$and": [query, appl_no_filter]}
        else:
            query = appl_no_filter
        return query

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

        appl_no_filter = {
            "$or": [
                {"appl_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"APPL_NO": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"application_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}}
            ]
        }
        if query:
            query = {"$and": [query, appl_no_filter]}
        else:
            query = appl_no_filter

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
            NO_WON_FILTER
        ]
        pending_wo = self.collection.count_documents(pending_wo_query)

        pending_conn_wo_issued_query = dict(query)
        pending_conn_wo_issued_query["$and"] = [
            VALID_WON_FILTER
        ]
        pending_conn_wo_issued = self.collection.count_documents(pending_conn_wo_issued_query)

        docs = list(self.collection.find(query))

        valid_qtn_delays = []
        valid_wo_delays = []

        for d in docs:
            def parse_dt(val):
                if not val or pd.isna(val):
                    return None
                if isinstance(val, datetime):
                    return val
                s = str(val).strip()
                if not s or s.lower() == 'nan' or s.lower() == '(null)':
                    return None
                for fmt in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
                    try:
                        return datetime.strptime(s[:19], fmt)
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
                diff = (quot_issue_dt - creation_dt).total_seconds() / 86400.0
                if diff >= 0:
                    valid_qtn_delays.append(diff)

            if coll_dt:
                end_dt = wo_creation_dt if wo_creation_dt else datetime.now()
                try:
                    diff = (end_dt - coll_dt).total_seconds() / 86400.0
                    valid_wo_delays.append(max(0.0, diff))
                except Exception:
                    pass

            d['_id'] = str(d['_id'])

        quotation_delay = round(sum(valid_qtn_delays) / len(valid_qtn_delays), 1) if valid_qtn_delays else 0.0
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
                                        {"$eq": ["$won", None]},
                                        {"$eq": ["$won", ""]},
                                        {"$eq": ["$won", " "]},
                                        {"$eq": ["$won", "null"]},
                                        {"$eq": ["$won", "NULL"]},
                                        {"$eq": ["$won", "(null)"]},
                                        {"$eq": ["$won", "(NULL)"]},
                                        {"$eq": ["$won", "None"]},
                                        {"$eq": ["$won", "NONE"]},
                                        {"$eq": ["$won", "-"]},
                                        {"$eq": ["$won", "N/A"]},
                                        {"$eq": ["$won", "n/a"]}
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

        total_cases = self.collection.count_documents(query)
        return {
            "total_cases": total_cases,
            "total_poles": total_poles,
            "pending_count": pending_count,
            "pending_wo": pending_wo,
            "pending_conn_wo_issued": pending_conn_wo_issued,
            "pending_application": pending_application,
            "quotation_delay": quotation_delay,
            "wo_delay": wo_delay,
            "avg_wo_delay": wo_delay,
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
        status_type = filters.get("status_type")
        
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



        appl_no_filter = {
            "$or": [
                {"appl_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"APPL_NO": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"application_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}}
            ]
        }
        if query:
            query = {"$and": [query, appl_no_filter]}
        else:
            query = appl_no_filter
        
        if status_type == "pending_wo":
            query["$and"] = [
                NO_WON_FILTER
            ]
        elif status_type == "pending_conn_wo_issued":
            query["$and"] = [
                VALID_WON_FILTER
            ]
        elif status_type == "pending_conn":
            query["$and"] = [
                {"$and": [
                    {"coll_date": {"$ne": None}}, 
                    {"coll_date": {"$ne": ""}}, 
                    {"coll_date": {"$ne": "(null)"}}
                ]},
                NO_WON_FILTER
            ]
        elif status_type == "pending_app":
            query["$and"] = [
                {"$or": [
                    {"quotation_issue_date": None},
                    {"quotation_issue_date": ""},
                    {"quotation_issue_date": "(null)"}
                ]}
            ]
        elif status_type == "quotation_delay":
            pass
        elif status_type and status_type.startswith("aging_"):
            query["coll_date"] = {"$type": "date"}
            now = datetime.now()
            if status_type == "aging_within_3":
                # days_elapsed between 0 and 3
                min_dt = now - timedelta(days=3)
                query["coll_date"] = {"$gte": min_dt, "$lte": now}
            elif status_type == "aging_4_to_15":
                max_dt = now - timedelta(days=3)
                min_dt = now - timedelta(days=15)
                query["coll_date"] = {"$gte": min_dt, "$lt": max_dt}
            elif status_type == "aging_16_to_30":
                max_dt = now - timedelta(days=15)
                min_dt = now - timedelta(days=30)
                query["coll_date"] = {"$gte": min_dt, "$lt": max_dt}
            elif status_type == "aging_above_30":
                max_dt = now - timedelta(days=30)
                query["coll_date"] = {"$lt": max_dt}

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

            creation_dt = parse_dt(d.get('creation_date') or d.get('CREATION_DATE'))
            quot_issue_dt = parse_dt(d.get('quotation_issue_date') or d.get('QUOTATION_ISSUE_DATE'))
            wo_creation_dt = parse_dt(d.get('wo_creation_date') or d.get('WO_CREATION_DATE'))
            coll_dt = parse_dt(d.get('coll_date') or d.get('COLL_DATE') or d.get('connection_date') or d.get('conn_date') or d.get('release_date'))

            if status_type == "quotation_delay":
                if not (creation_dt and quot_issue_dt and quot_issue_dt >= creation_dt):
                    continue
                delay_as_on_today = max(0, int((quot_issue_dt - creation_dt).total_seconds() / 86400.0))
            elif status_type == "wo_delay":
                if not coll_dt:
                    continue
                end_dt = wo_creation_dt if wo_creation_dt else datetime.now()
                delay_as_on_today = max(0.0, (end_dt - coll_dt).total_seconds() / 86400.0)
            else:
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

        return {"total": len(results), "items": results}


    def get_collection_aging(self, filters: dict = None):
        filters = filters or {}
        query = {}

        if filters.get("zone") and filters["zone"].strip() != "":
            query["zone"] = {"$regex": filters["zone"].strip(), "$options": "i"}
        if filters.get("reg") and filters["reg"].strip() != "":
            query["reg"] = {"$regex": filters["reg"].strip(), "$options": "i"}
        if filters.get("region") and filters["region"].strip() != "":
            query["region"] = {"$regex": filters["region"].strip(), "$options": "i"}
        if filters.get("divn_name") and filters["divn_name"].strip() != "":
            query["divn_name"] = {"$regex": filters["divn_name"].strip(), "$options": "i"}
        if filters.get("division") and filters["division"].strip() != "":
            query["division"] = {"$regex": filters["division"].strip(), "$options": "i"}
        if filters.get("supp_off") and filters["supp_off"].strip() != "":
            query["supp_off"] = {"$regex": filters["supp_off"].strip(), "$options": "i"}
        if filters.get("ccc") and filters["ccc"].strip() != "":
            query["ccc"] = {"$regex": filters["ccc"].strip(), "$options": "i"}
        if filters.get("ccc_code") and str(filters["ccc_code"]).strip() != "":
            query["ccc_code"] = str(filters["ccc_code"]).strip()

        if "reg" in query and "region" not in query:
            reg_val = query.pop("reg")
            query["$or"] = [{"reg": reg_val}, {"region": reg_val}]

        pole_type = filters.get("pole_type", "all")
        if pole_type and pole_type.lower() == "pole":
            query["no_of_poles"] = {"$gt": 0}
        elif pole_type and pole_type.lower() == "non_pole":
            query["$or"] = [
                {"no_of_poles": {"$exists": False}},
                {"no_of_poles": None},
                {"no_of_poles": 0},
                {"no_of_poles": "0"}
            ]

        appl_no_filter = {
            "$or": [
                {"appl_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"APPL_NO": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}},
                {"application_no": {"$exists": True, "$nin": [None, "", "null", "None", "nan", "NaN", "APPL_NO"]}}
            ]
        }
        if query:
            query = {"$and": [query, appl_no_filter]}
        else:
            query = appl_no_filter

        query["coll_date"] = {"$type": "date"}
        now = datetime.now()

        pipeline = [
            {"$match": query},
            {
                "$addFields": {
                    "days_elapsed": {
                        "$divide": [
                            {"$subtract": [now, "$coll_date"]},
                            1000 * 60 * 60 * 24
                        ]
                    }
                }
            },
            {
                "$facet": {
                    "totals": [
                        {
                            "$group": {
                                "_id": None,
                                "total_collected": {"$sum": 1},
                                "within_3_days": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gte": ["$days_elapsed", 0]}, {"$lte": ["$days_elapsed", 3]}]}, 1, 0]
                                    }
                                },
                                "days_4_to_15": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 3]}, {"$lte": ["$days_elapsed", 15]}]}, 1, 0]
                                    }
                                },
                                "days_16_to_30": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 15]}, {"$lte": ["$days_elapsed", 30]}]}, 1, 0]
                                    }
                                },
                                "above_30_days": {
                                    "$sum": {
                                        "$cond": [{"$gt": ["$days_elapsed", 30]}, 1, 0]
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        ]

        pipeline = [
            {"$match": query},
            {
                "$addFields": {
                    "days_elapsed": {
                        "$divide": [
                            {"$subtract": [now, "$coll_date"]},
                            1000 * 60 * 60 * 24
                        ]
                    }
                }
            },
            {
                "$facet": {
                    "totals": [
                        {
                            "$group": {
                                "_id": None,
                                "total_collected": {"$sum": 1},
                                "within_3_days": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gte": ["$days_elapsed", 0]}, {"$lte": ["$days_elapsed", 3]}]}, 1, 0]
                                    }
                                },
                                "days_4_to_15": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 3]}, {"$lte": ["$days_elapsed", 15]}]}, 1, 0]
                                    }
                                },
                                "days_16_to_30": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 15]}, {"$lte": ["$days_elapsed", 30]}]}, 1, 0]
                                    }
                                },
                                "above_30_days": {
                                    "$sum": {
                                        "$cond": [{"$gt": ["$days_elapsed", 30]}, 1, 0]
                                    }
                                }
                            }
                        }
                    ],
                    "breakdown_region": [
                        {
                            "$group": {
                                "_id": {"$ifNull": ["$reg", {"$ifNull": ["$region", "Unknown"]}]},
                                "total_collected": {"$sum": 1},
                                "within_3_days": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gte": ["$days_elapsed", 0]}, {"$lte": ["$days_elapsed", 3]}]}, 1, 0]
                                    }
                                },
                                "days_4_to_15": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 3]}, {"$lte": ["$days_elapsed", 15]}]}, 1, 0]
                                    }
                                },
                                "days_16_to_30": {
                                    "$sum": {
                                        "$cond": [{"$and": [{"$gt": ["$days_elapsed", 15]}, {"$lte": ["$days_elapsed", 30]}]}, 1, 0]
                                    }
                                },
                                "above_30_days": {
                                    "$sum": {
                                        "$cond": [{"$gt": ["$days_elapsed", 30]}, 1, 0]
                                    }
                                }
                            }
                        },
                        {"$sort": {"total_collected": -1}}
                    ]
                    ,
                    "breakdown_division": [
                        {
                            "$group": {
                                "_id": {"$ifNull": ["$divn_name", {"$ifNull": ["$division", "Unknown"]}]},
                                "total_collected": {"$sum": 1},
                                "within_3_days": {"$sum": {"$cond": [{"$and": [{"$gte": ["$days_elapsed", 0]}, {"$lte": ["$days_elapsed", 3]}]}, 1, 0]}},
                                "days_4_to_15": {"$sum": {"$cond": [{"$and": [{"$gt": ["$days_elapsed", 3]}, {"$lte": ["$days_elapsed", 15]}]}, 1, 0]}},
                                "days_16_to_30": {"$sum": {"$cond": [{"$and": [{"$gt": ["$days_elapsed", 15]}, {"$lte": ["$days_elapsed", 30]}]}, 1, 0]}},
                                "above_30_days": {"$sum": {"$cond": [{"$gt": ["$days_elapsed", 30]}, 1, 0]}}
                            }
                        },
                        {"$sort": {"total_collected": -1}}
                    ],
                    "breakdown_ccc": [
                        {
                            "$group": {
                                "_id": {"$ifNull": ["$supp_off", {"$ifNull": ["$ccc", {"$ifNull": ["$ccc_code", "Unknown"]}]}]},
                                "total_collected": {"$sum": 1},
                                "within_3_days": {"$sum": {"$cond": [{"$and": [{"$gte": ["$days_elapsed", 0]}, {"$lte": ["$days_elapsed", 3]}]}, 1, 0]}},
                                "days_4_to_15": {"$sum": {"$cond": [{"$and": [{"$gt": ["$days_elapsed", 3]}, {"$lte": ["$days_elapsed", 15]}]}, 1, 0]}},
                                "days_16_to_30": {"$sum": {"$cond": [{"$and": [{"$gt": ["$days_elapsed", 15]}, {"$lte": ["$days_elapsed", 30]}]}, 1, 0]}},
                                "above_30_days": {"$sum": {"$cond": [{"$gt": ["$days_elapsed", 30]}, 1, 0]}}
                            }
                        },
                        {"$sort": {"total_collected": -1}}
                    ]
                }
            }
        ]
        agg_result = list(self.collection.aggregate(pipeline))
        if not agg_result:
            return {
                "within_3_days": 0,
                "days_4_to_15": 0,
                "days_16_to_30": 0,
                "above_30_days": 0,
                "total_collected": 0,
                "breakdown": {"region": [], "division": [], "ccc": []}
            }

        res = agg_result[0]
        totals_list = res.get("totals", [])
        totals = totals_list[0] if totals_list else {}

        return {
            "within_3_days": totals.get("within_3_days", 0),
            "days_4_to_15": totals.get("days_4_to_15", 0),
            "days_16_to_30": totals.get("days_16_to_30", 0),
            "above_30_days": totals.get("above_30_days", 0),
            "total_collected": totals.get("total_collected", 0),
            "breakdown": {
                "region": [
                    {
                        "region": r["_id"],
                        "within_3_days": r.get("within_3_days", 0),
                        "days_4_to_15": r.get("days_4_to_15", 0),
                        "days_16_to_30": r.get("days_16_to_30", 0),
                        "above_30_days": r.get("above_30_days", 0),
                        "total_collected": r.get("total_collected", 0)
                    }
                    for r in res.get("breakdown_region", [])
                ],
                "division": [
                    {
                        "division": d["_id"],
                        "within_3_days": d.get("within_3_days", 0),
                        "days_4_to_15": d.get("days_4_to_15", 0),
                        "days_16_to_30": d.get("days_16_to_30", 0),
                        "above_30_days": d.get("above_30_days", 0),
                        "total_collected": d.get("total_collected", 0)
                    }
                    for d in res.get("breakdown_division", [])
                ],
                "ccc": [
                    {
                        "ccc": c["_id"],
                        "within_3_days": c.get("within_3_days", 0),
                        "days_4_to_15": c.get("days_4_to_15", 0),
                        "days_16_to_30": c.get("days_16_to_30", 0),
                        "above_30_days": c.get("above_30_days", 0),
                        "total_collected": c.get("total_collected", 0)
                    }
                    for c in res.get("breakdown_ccc", [])
                ]
            }
        }