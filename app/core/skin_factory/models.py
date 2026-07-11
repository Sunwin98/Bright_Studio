"""Request/data models for the skin factory (lifted from factory_skin_v3)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SkinInfo:
    name: str
    display_name: str
    skin_path: str
    model_path: Optional[str]
    animation_path: Optional[str]
    slot_name: str
    slot_value: str
    equip_slot: str
    item_id: str
    geometry_id: str
    animation_names: Optional[List[str]] = None
