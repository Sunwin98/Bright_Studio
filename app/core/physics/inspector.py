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
        # Strip comments and trailing commas to make parsing more robust
        text = re.sub(r"//[^\n]*", "", text)
        text = re.sub(r",(\s*[}\]])", r"\1", text)
        try:
            return json.loads(text)
        except Exception:
            return None

def find_bone_chains(bones: List[dict]) -> List[dict]:
    """Helper to trace parent-child bone relationships and group them into chains
    sharing common prefixes (e.g. hair_1 -> hair_2 -> hair_3).
    """
    if not bones:
        return []
        
    bone_map = {b["name"]: b for b in bones}
    children_map = {}
    for name, b in bone_map.items():
        parent = b.get("parent")
        if parent:
            children_map.setdefault(parent, []).append(name)
            
    visited = set()
    chains = []
    
    # Sort bone names to process systematically
    sorted_bone_names = sorted(bone_map.keys())
    
    # Keywords indicating physics-susceptible bones
    keywords = ["hair", "cape", "tail", "wing", "skirt", "cloth", "wave", "spring", "dress", "sleeve"]
    
    # 1. Trace hierarchical single-child chains
    for name in sorted_bone_names:
        if name in visited:
            continue
            
        is_candidate = any(kw in name.lower() for kw in keywords)
        if is_candidate:
            chain = [name]
            visited.add(name)
            curr = name
            while True:
                children = children_map.get(curr, [])
                if not children:
                    break
                
                next_bone = None
                if len(children) == 1:
                    child = children[0]
                    # Check if child is also a candidate or continues the name prefix
                    base_prefix = curr.rstrip("0123456789_")
                    if any(kw in child.lower() for kw in keywords) or child.startswith(base_prefix):
                        next_bone = child
                else:
                    # Multiple children: prioritize the one that shares the prefix
                    base_prefix = curr.rstrip("0123456789_")
                    for child in children:
                        if child.startswith(base_prefix):
                            next_bone = child
                            break
                            
                if next_bone and next_bone not in visited:
                    chain.append(next_bone)
                    visited.add(next_bone)
                    curr = next_bone
                else:
                    break
            
            if len(chain) >= 2:
                # Deduce prefix by removing trailing numbers/underscores from the first bone
                prefix = re.sub(r'[_]?\d+$', '', chain[0])
                if not prefix.endswith("_") and not prefix.endswith("."):
                    # If prefix ends with letters, but bones have numbers, keep a trailing character
                    # e.g., if bone is hair_1, prefix is hair_
                    if chain[0].startswith(prefix + "_"):
                        prefix = prefix + "_"
                
                chains.append({
                    "prefix": prefix,
                    "bones": chain
                })
                
    # 2. Trace sequential bones sharing a prefix without hierarchical connection
    prefix_groups = {}
    for name in sorted_bone_names:
        if name in visited:
            continue
        # Extract alphabetical prefix
        match = re.match(r'^([a-zA-Z_]+)(?:[_]?\d+)?$', name)
        if match:
            prefix = match.group(1)
            if any(kw in prefix.lower() for kw in keywords):
                prefix_groups.setdefault(prefix, []).append(name)
                
    for prefix, group in prefix_groups.items():
        if len(group) >= 2:
            # Sort group numerically
            def sort_num(n):
                m = re.search(r'\d+$', n)
                return int(m.group()) if m else 0
            group.sort(key=sort_num)
            
            # Ensure correct prefix suffix
            p_suffix = prefix
            if group[0].startswith(prefix + "_"):
                p_suffix = prefix + "_"
                
            chains.append({
                "prefix": p_suffix,
                "bones": group
            })
            for b in group:
                visited.add(b)
                
    return chains

def inspect_addon_for_physics(path_str: str) -> dict:
    """Intake entry point. Resolves source path, extracts if archive,
    and auto-discovers Attachables, Models, Animations, and bone chains.
    """
    res = packio.inspect_source(path_str)
    rp_path_str = res.get("rp_path")
    if not rp_path_str:
        raise ValueError("ไม่พบ Resource Pack (RP) ในตำแหน่งที่ระบุ กรุณาตรวจสอบว่าเลือกโฟลเดอร์หรือไฟล์แอดออนถูกต้อง")
        
    rp_path = Path(rp_path_str)
    
    # 1. Scan Model files (models/**/*.json or models/**/*.geo.json)
    model_map: Dict[str, dict] = {}
    models_dir = rp_path / "models"
    if models_dir.exists():
        for p in models_dir.rglob("*.json"):
            if not p.is_file():
                continue
            data = _load_json(p)
            if not data or not isinstance(data, dict):
                continue
            
            geometries = data.get("minecraft:geometry", [])
            if isinstance(geometries, dict):
                geometries = [geometries]
            if not isinstance(geometries, list):
                continue
                
            for geo in geometries:
                desc = geo.get("description", {})
                geo_id = desc.get("identifier")
                if not geo_id:
                    continue
                bones_list = geo.get("bones", [])
                if not isinstance(bones_list, list):
                    bones_list = []
                
                bones = []
                for bone in bones_list:
                    name = bone.get("name")
                    if name:
                        bones.append({
                            "name": name,
                            "parent": bone.get("parent")
                        })
                
                model_map[geo_id] = {
                    "file_path": str(p),
                    "bones": bones
                }
                
    # 2. Scan Animation files (animations/**/*.json)
    animation_map: Dict[str, str] = {}
    anims_dir = rp_path / "animations"
    if anims_dir.exists():
        for p in anims_dir.rglob("*.json"):
            if not p.is_file():
                continue
            data = _load_json(p)
            if not data or not isinstance(data, dict):
                continue
            animations = data.get("animations", {})
            if isinstance(animations, dict):
                for anim_id in animations.keys():
                    animation_map[anim_id] = str(p)
                    
    # 3. Scan Attachable files (attachables/**/*.json)
    attachables_dir = rp_path / "attachables"
    attachables_list = []
    if attachables_dir.exists():
        for p in attachables_dir.rglob("*.json"):
            if not p.is_file():
                continue
            data = _load_json(p)
            if not data or not isinstance(data, dict):
                continue
                
            attachable = data.get("minecraft:attachable", {})
            desc = attachable.get("description", {})
            identifier = desc.get("identifier")
            if not identifier:
                continue
                
            # Geometry identifier
            geometries_spec = desc.get("geometry", {})
            geo_ids = []
            if isinstance(geometries_spec, dict):
                for gval in geometries_spec.values():
                    if isinstance(gval, str):
                        geo_ids.append(gval)
            elif isinstance(geometries_spec, str):
                geo_ids.append(geometries_spec)
                
            # Animation identifiers
            animations_spec = desc.get("animations", {})
            anim_ids = []
            if isinstance(animations_spec, dict):
                for aval in animations_spec.values():
                    if isinstance(aval, str):
                        anim_ids.append(aval)
            elif isinstance(animations_spec, str):
                anim_ids.append(animations_spec)
                
            # Resolve Model Path and Bones
            matched_model_path = None
            bones_data = []
            for gid in geo_ids:
                if gid in model_map:
                    matched_model_path = model_map[gid]["file_path"]
                    bones_data = model_map[gid]["bones"]
                    break
                    
            # Resolve Animation Paths
            matched_animations = []
            for aid in anim_ids:
                if aid in animation_map:
                    matched_animations.append({
                        "identifier": aid,
                        "file_path": animation_map[aid]
                    })
            
            # List all anim files as fallbacks
            all_anim_files = []
            if anims_dir.exists():
                all_anim_files = sorted([str(ap) for ap in anims_dir.rglob("*.json") if ap.is_file()])
                
            # Find bone chains
            discovered_chains = find_bone_chains(bones_data)
            
            attachables_list.append({
                "identifier": identifier,
                "attachable_path": str(p),
                "model_path": matched_model_path,
                "bones": [b["name"] for b in bones_data],
                "discovered_chains": discovered_chains,
                "animations": matched_animations,
                "all_animation_files": all_anim_files
            })
            
    return {
        "bp_path": res.get("bp_path"),
        "rp_path": res.get("rp_path"),
        "attachables": attachables_list
    }
