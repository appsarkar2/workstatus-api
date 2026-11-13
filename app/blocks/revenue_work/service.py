from datetime import datetime
from app.blocks.base_service import BaseBlockService
from fastapi import HTTPException, UploadFile
from typing import Optional, List
import pandas as pd
import io


class RevenueWorkService(BaseBlockService):
    BLOCK_ID = 'revenue_work'
    COLLECTION = 'revenue_work_entries'

    def create(self, body):
        existing = self.collection.find_one({
            'division': body.division,
            'consumer_class': body.consumer_class,
            'report_month': body.report_month,
            'block_id': self.BLOCK_ID,
        })
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f'Entry already exists for {body.division} / {body.consumer_class} / {body.report_month}',
            )
        now = datetime.utcnow()
        doc = {
            'block_id': self.BLOCK_ID,
            'zone': body.zone,
            'region': body.region,
            'division': body.division,
            'ccc': body.ccc,
            'consumer_class': body.consumer_class,
            'report_month': body.report_month,
            'total_count': body.total_count,
            'total_amount_cr': body.total_amount_cr,
            'fully_paid_count': body.fully_paid_count,
            'fully_paid_amount_lakh': body.fully_paid_amount_lakh,
            'part_paid_count': body.part_paid_count,
            'part_paid_amount_lakh': body.part_paid_amount_lakh,
            'disconnected_count': body.disconnected_count,
            'disconnected_amount_lakh': body.disconnected_amount_lakh,
            'no_action_count': body.no_action_count,
            'no_action_amount_cr': body.no_action_amount_cr,
            'osd_gt_3k_count': body.osd_gt_3k_count,
            'osd_gt_3k_amount_cr': body.osd_gt_3k_amount_cr,
            'osd_gt_5k_count': body.osd_gt_5k_count,
            'osd_gt_5k_amount_cr': body.osd_gt_5k_amount_cr,
            'created_at': now,
            'updated_at': now,
        }
        result = self.collection.insert_one(doc)
        return {'id': str(result.inserted_id)}

    def bulk_upload_csv(self, file: UploadFile):
        try:
            contents = file.file.read()
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f'Invalid CSV file: {str(e)}')

        now = datetime.utcnow()
        docs = []
        for _, row in df.iterrows():
            doc = {
                'block_id': self.BLOCK_ID,
                'zone': str(row.get('zone', 'All Zones')),
                'region': str(row.get('region', 'All Regions')),
                'division': str(row.get('division', 'Unknown')),
                'ccc': str(row.get('ccc', 'All CCC')),
                'consumer_class': str(row.get('consumer_class', 'All Classes')),
                'report_month': str(row.get('report_month', '2026-10')),
                'total_count': int(row.get('total_count', 0)),
                'total_amount_cr': float(row.get('total_amount_cr', 0.0)),
                'fully_paid_count': int(row.get('fully_paid_count', 0)),
                'fully_paid_amount_lakh': float(row.get('fully_paid_amount_lakh', 0.0)),
                'part_paid_count': int(row.get('part_paid_count', 0)),
                'part_paid_amount_lakh': float(row.get('part_paid_amount_lakh', 0.0)),
                'disconnected_count': int(row.get('disconnected_count', 0)),
                'disconnected_amount_lakh': float(row.get('disconnected_amount_lakh', 0.0)),
                'no_action_count': int(row.get('no_action_count', 0)),
                'no_action_amount_cr': float(row.get('no_action_amount_cr', 0.0)),
                'osd_gt_3k_count': int(row.get('osd_gt_3k_count', 0)),
                'osd_gt_3k_amount_cr': float(row.get('osd_gt_3k_amount_cr', 0.0)),
                'osd_gt_5k_count': int(row.get('osd_gt_5k_count', 0)),
                'osd_gt_5k_amount_cr': float(row.get('osd_gt_5k_amount_cr', 0.0)),
                'created_at': now,
                'updated_at': now,
            }
            docs.append(doc)

        if docs:
            self.collection.insert_many(docs)

        return {'count': len(docs), 'message': 'Successfully uploaded revenue records'}

    def get_dashboard_summary(
        self,
        zone: Optional[str] = None,
        region: Optional[str] = None,
        division: Optional[str] = None,
        ccc: Optional[str] = None,
        consumer_class: Optional[str] = None,
        month: Optional[str] = None,
    ):
        match_stage = {'block_id': self.BLOCK_ID}
        if zone:
            match_stage['zone'] = zone
        if region:
            match_stage['region'] = region
        if division:
            match_stage['division'] = division
        if ccc:
            match_stage['ccc'] = ccc
        if consumer_class:
            match_stage['consumer_class'] = consumer_class
        if month:
            match_stage['report_month'] = month

        pipeline = [
            {'$match': match_stage},
            {
                '$group': {
                    '_id': None,
                    'total_count': {'$sum': '$total_count'},
                    'total_amount_cr': {'$sum': '$total_amount_cr'},
                    'fully_paid_count': {'$sum': '$fully_paid_count'},
                    'fully_paid_amount_lakh': {'$sum': '$fully_paid_amount_lakh'},
                    'part_paid_count': {'$sum': '$part_paid_count'},
                    'part_paid_amount_lakh': {'$sum': '$part_paid_amount_lakh'},
                    'disconnected_count': {'$sum': '$disconnected_count'},
                    'disconnected_amount_lakh': {'$sum': '$disconnected_amount_lakh'},
                    'no_action_count': {'$sum': '$no_action_count'},
                    'no_action_amount_cr': {'$sum': '$no_action_amount_cr'},
                    'osd_gt_3k_count': {'$sum': '$osd_gt_3k_count'},
                    'osd_gt_3k_amount_cr': {'$sum': '$osd_gt_3k_amount_cr'},
                    'osd_gt_5k_count': {'$sum': '$osd_gt_5k_count'},
                    'osd_gt_5k_amount_cr': {'$sum': '$osd_gt_5k_amount_cr'},
                    'entry_count': {'$sum': 1},
                },
            },
        ]

        results = list(self.collection.aggregate(pipeline))
        defaults = {
            'total_count': 0, 'total_amount_cr': 0.0,
            'fully_paid_count': 0, 'fully_paid_amount_lakh': 0.0,
            'part_paid_count': 0, 'part_paid_amount_lakh': 0.0,
            'disconnected_count': 0, 'disconnected_amount_lakh': 0.0,
            'no_action_count': 0, 'no_action_amount_cr': 0.0,
            'osd_gt_3k_count': 0, 'osd_gt_3k_amount_cr': 0.0,
            'osd_gt_5k_count': 0, 'osd_gt_5k_amount_cr': 0.0,
            'entry_count': 0,
        }
        totals = results[0] if results else dict(defaults)
        totals.pop('_id', None)

        # Region breakdown pipeline for Bar Chart
        region_pipeline = [
            {'$match': match_stage},
            {
                '$group': {
                    '_id': '$region',
                    'total_amount_cr': {'$sum': '$total_amount_cr'},
                },
            },
            {'$sort': {'total_amount_cr': -1}},
        ]
        regions_breakdown = [
            {
                'region': r['_id'] or 'Unassigned',
                'total_amount_cr': r['total_amount_cr'],
            }
            for r in self.collection.aggregate(region_pipeline)
        ]

        # Distinct filter options for dropdowns
        zones = self.collection.distinct('zone', {'block_id': self.BLOCK_ID})
        regions = self.collection.distinct('region', {'block_id': self.BLOCK_ID})
        divisions = self.collection.distinct('division', {'block_id': self.BLOCK_ID})
        cccs = self.collection.distinct('ccc', {'block_id': self.BLOCK_ID})
        consumer_classes = self.collection.distinct('consumer_class', {'block_id': self.BLOCK_ID})

        return {
            'totals': totals,
            'regions_breakdown': regions_breakdown,
            'filters': {
                'zones': [z for z in zones if z],
                'regions': [r for r in regions if r],
                'divisions': [d for d in divisions if d],
                'cccs': [c for c in cccs if c],
                'consumer_classes': [cc for cc in consumer_classes if cc],
            }
        }
