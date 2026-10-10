"""Auto-discover all block folders and register their routers."""
import importlib
from pathlib import Path

BLOCKS_DIR = Path(__file__).parent


def register_all_blocks(app):
    for entry in sorted(BLOCKS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"app.blocks.{entry.name}.main")
            if hasattr(module, "router"):
                app.include_router(module.router)
                print(f"[OK] Registered block: {entry.name}")
        except Exception as e:
            print(f"[FAIL] Block {entry.name}: {e}")
