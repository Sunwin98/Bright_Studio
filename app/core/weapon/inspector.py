import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any
from app.core import packio

def _load_json(p: Path) -> dict | None:
    try:
        text = p.read_text(encoding="utf-8-sig")
    except Exception:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Strip comments
        text = re.sub(r"//[^\n]*", "", text)
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        try:
            return json.loads(text)
        except Exception:
            return None

def inspect_addon_for_weapon(path_str: str) -> dict:
    """Inspects the selected addon folder/file and discovers Behavior Pack,
    Resource Pack, and all item JSON files in the Behavior Pack.
    """
    res = packio.inspect_source(path_str)
    bp_path_str = res.get("bp_path")
    if not bp_path_str:
        raise ValueError("ไม่พบ Behavior Pack (BP) ในตำแหน่งที่ระบุ กรุณาตรวจสอบว่าเลือกโฟลเดอร์หรือไฟล์แอดออนถูกต้อง")
        
    bp_path = Path(bp_path_str)
    items_list = []
    
    items_dir = bp_path / "items"
    if items_dir.exists():
        for p in items_dir.rglob("*.json"):
            if not p.is_file():
                continue
            data = _load_json(p)
            identifier = ""
            if data and isinstance(data, dict):
                item_data = data.get("minecraft:item", {})
                desc = item_data.get("description", {})
                identifier = desc.get("identifier", "")
                
            items_list.append({
                "file_path": str(p),
                "relative_path": str(p.relative_to(bp_path)),
                "identifier": identifier or p.stem
            })
            
    return {
        "bp_path": res.get("bp_path"),
        "rp_path": res.get("rp_path"),
        "items": items_list
    }
