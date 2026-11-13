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
            contents = await file.read()
            df = pd.read_csv(pd.io.common.BytesIO(contents))
            df.columns = [c.lower() for c in df.columns]
            data = df.to_dict('records')
            
            self.collection.delete_many({})
            
            if data:
                self.collection.insert_many(data)
            return {"message": "Data uploaded successfully", "count": len(data)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    def get_filter_options(self):
        zones = [z for z in self.collection.distinct('zone_name') if z is not None]
        regions = [r for r in self.collection.distinct('reg') if r is not None]
        divisions = [d for d in self.collection.distinct('divn_name') if d is not None]
        cccs = [c for c in self.collection.distinct('supp_off') if c is not None]
        classes = [cl for cl in self.collection.distinct("conn_class") if cl is not None]
        return {
            "zones": sorted([str(x) for x in zones]),
            "regions": sorted([str(x) for x in regions]),
            "divisions": sorted([str(x) for x in divisions]),
            "cccs": sorted([str(x) for x in cccs]),
            "classes": sorted([str(x) for x in classes])
        }

    def get_kpi_dashboard(self, filters: dict = None):
        filters = filters or {}
        query = {}

        supp_off = filters.get("supp_off") or filters.get("ccc_code") or filters.get("ccc")

        if filters.get("zone"): query["zone_name"] = {"$regex": filters["zone"], "$options": "i"}
        if filters.get("reg"): query["reg"] = {"$regex": filters["reg"], "$options": "i"}
        if filters.get("divn_name"): query["divn_name"] = {"$regex": filters["divn_name"], "$options": "i"}
        if supp_off: query["supp_off"] = {"$regex": supp_off, "$options": "i"}
        if filters.get("conn_class"): query["conn_class"] = {"$regex": filters["conn_class"], "$options": "i"}

        if filters.get("no_of_poles") is not None and filters.get("no_of_poles") != "":
            query['no_of_poles'] = filters['no_of_poles']

        docs = list(self.collection.find(query))

        total_cases = len(docs)
        pending_count = 0

        region_data = list(self.collection.aggregate([
            {"$match": query},
            {"$match": {"reg": {"$ne": None}}},
            {"$group": {"_id": "$reg", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))

        total_quot_delay = 0.0
        total_wo_delay = 0.0
        total_conn_delay = 0.0
        quot_count = 0
        wo_count = 0
        conn_count = 0

        for d in docs:
            conn_type = d.get('conn_type')
            conn_date = d.get('connection_date') or d.get('conn_date') or d.get('release_date')
            if not conn_type or conn_type == '' or not conn_date or pd.isna(conn_date) or str(conn_date).strip() == '':
                pending_count += 1

            def parse_date_dd_mm_first(val):
                if not val or pd.isna(val):
                    return None
                s = str(val).strip()
                if not s or s.lower() == 'nan':
                    return None
                for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(s[:10], fmt)
                    except ValueError:
                        continue
                return None

            quot_issue_val = d.get('quotation_issue_date') or d.get('quot_date') or d.get('quotation_date')
            quot_due_val = d.get('quotation_due_date') or d.get('quotation_expiry_date') or d.get('due_date')

            quot_issue_dt = parse_date_dd_mm_first(quot_issue_val)
            quot_due_dt = parse_date_dd_mm_first(quot_due_val)
            app_dt = parse_date_dd_mm_first(d.get('application_date') or d.get('app_date'))
            wo_dt = parse_date_dd_mm_first(d.get('wo_creation_date') or d.get('wo_date') or d.get('work_order_date'))
            rel_dt = parse_date_dd_mm_first(d.get('connection_date') or d.get('conn_date') or d.get('release_date'))

            if quot_issue_dt and quot_due_dt:
                diff = (quot_due_dt - quot_issue_dt).days
                if diff >= 0:
                    total_quot_delay += diff
                    quot_count += 1
            elif app_dt and quot_issue_dt:
                diff = (quot_issue_dt - app_dt).days
                if diff >= 0:
                    total_quot_delay += diff
                    quot_count += 1

            if quot_issue_dt and wo_dt:
                diff = (wo_dt - quot_issue_dt).days
                if diff >= 0:
                    total_wo_delay += diff
                    wo_count += 1

            if wo_dt and rel_dt:
                diff = (rel_dt - wo_dt).days
                if diff >= 0:
                    total_conn_delay += diff
                    conn_count += 1

            d['_id'] = str(d['_id'])

        quotation_delay = round(total_quot_delay / quot_count, 2) if quot_count > 0 else 0.00
        wo_delay = round(total_wo_delay / wo_count, 2) if wo_count > 0 else 0.00
        conn_delay = round(total_conn_delay / conn_count, 2) if conn_count > 0 else 0.00

        items = docs[:100]

        return {
            'total_cases': total_cases,
            'pending_count': pending_count,
            'region_data': region_data,
            'items': items,
            'avg_delay': round((quotation_delay + wo_delay + conn_delay) / 3, 2),
            'quotation_delay': quotation_delay,
            'wo_delay': wo_delay,
            'conn_delay': conn_delay
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
