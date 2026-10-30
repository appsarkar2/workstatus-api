from app.blocks.base_service import BaseBlockService
from datetime import datetime

class UnbilledMonitoringService(BaseBlockService):
    BLOCK_ID = "unbilled_monitoring"
    COLLECTION = "unbilled_reports"

    def get_dashboard_summary(self, zone: str = None, region: str = None, division: str = None):
        # Build base query
        query = {"block_id": self.BLOCK_ID}
        if division:
            query["division"] = division
        if region:
            query["region"] = region
        if zone:
            query["zone"] = zone

        # Fetch reports sorted by month
        reports = list(self.collection.find(query).sort("report_month", 1))
        
        trend_summary = {}
        ccc_summary = {}

        for r in reports:
            m = r["report_month"]
            
            # Initialize month in trend if not exists
            if m not in trend_summary:
                trend_summary[m] = {"quarterly": 0, "monthly": 0, "smart_meter": 0, "industrial": 0, "total": 0}
            
            ccc_name = r.get("ccc", "Unknown CCC")
            # Initialize CCC if not exists
            if ccc_name not in ccc_summary:
                ccc_summary[ccc_name] = {"quarterly": 0, "monthly": 0, "smart_meter": 0, "industrial": 0, "total": 0}
            
            for item in r.get("data", []):
                cat = item["category"].lower().replace(" ", "_")
                
                # Add to trend
                if cat in trend_summary[m]:
                    trend_summary[m][cat] += item.get("nos", 0)
                    trend_summary[m]["total"] += item.get("nos", 0)
                    
                # Add to CCC
                if cat in ccc_summary[ccc_name]:
                    ccc_summary[ccc_name][cat] += item.get("nos", 0)
                    ccc_summary[ccc_name]["total"] += item.get("nos", 0)

        # Convert dicts to lists for frontend
        chart_data = [{"month": k, **v} for k, v in trend_summary.items()]
        ccc_data = [{"ccc": k, **v} for k, v in ccc_summary.items()]
        
        return {
            "chart_data": chart_data,
            "ccc_data": ccc_data
        }