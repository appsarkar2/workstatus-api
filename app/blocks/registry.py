# backend/app/blocks/registry.py
import json
from pathlib import Path

BLOCKS_DIR = Path(__file__).parent


def list_active_blocks():
    """Scan block folders and return metadata for active blocks."""
    blocks = []
    for entry in sorted(BLOCKS_DIR.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        cfg_path = entry / "config.json"
        if not cfg_path.exists():
            continue
        try:
            with open(cfg_path, encoding="utf-8-sig") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[registry] Failed to read {cfg_path}: {e}")
            continue
        if not cfg.get("active", True):
            continue
        blocks.append({
            "id": cfg["id"],
            "name": cfg["name"],
            "code": cfg.get("code"),
            "icon": cfg.get("icon"),
            "color": cfg.get("color"),
            "stage_count": len(cfg.get("stages", [])),
            "doc_count": len(cfg.get("documents_required", [])),
        })
    return blocks