# backend/app/blocks/bulk_connection/service.py
"""
BulkConnectionService — extends BaseBlockService.
Only overrides what's unique to the bulk_connection block.
"""
import json
from pathlib import Path
from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class BulkConnectionService(BaseBlockService):
    BLOCK_ID = "bulk_connection"
    COLLECTION = "bulk_connections"

    def __init__(self, user: dict):
        # Pass both user and config to the base class
        super().__init__(user=user, config=CONFIG)