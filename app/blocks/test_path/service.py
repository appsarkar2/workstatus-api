# backend/app/blocks/test_path/service.py
import json
from pathlib import Path
from app.blocks.base_service import BaseBlockService

CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
    CONFIG = json.load(f)


class TestPathService(BaseBlockService):
    BLOCK_ID = "test_path"
    COLLECTION = "test_paths"

    def __init__(self, user: dict):
        super().__init__(user=user, config=CONFIG)