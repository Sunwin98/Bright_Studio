"""Headless port of the TDC generator (App.generate, Tab 1).

Reuses the extracted create_*/generate_script functions verbatim so the produced
tdcmodel_*.js files are byte-identical to the desktop tool's output.
"""
from __future__ import annotations

import os
from typing import List

from app.core.weapon import tdc_source as t


def generate(bp_path: str, rp_path: str, gen_bp: bool, gen_rp: bool,
             item_paths: List[str], entity_opts: dict) -> dict:
    log: List[str] = []

    if not gen_bp and not gen_rp:
        raise ValueError("ต้องเลือกสร้างไฟล์สำหรับ BP หรือ RP อย่างน้อย 1 ฝั่ง")
    if gen_bp and (not bp_path or not os.path.exists(os.path.join(bp_path, "manifest.json"))):
        raise ValueError("โฟลเดอร์ BP ไม่ถูกต้อง (ไม่พบ manifest.json)")
    if gen_rp and (not rp_path or not os.path.exists(os.path.join(rp_path, "manifest.json"))):
        raise ValueError("โฟลเดอร์ RP ไม่ถูกต้อง (ไม่พบ manifest.json)")

    items = [p.strip() for p in item_paths if p and p.strip()]
    if not items:
        raise ValueError("ต้องเลือกไฟล์ไอเทม JSON อย่างน้อย 1 ชิ้น")

    def opt(key: str) -> bool:
        return bool(entity_opts.get(key))

    if gen_bp:
        ok, msg = t.update_manifest_dependencies(bp_path)
        if not ok:
            log.append(f"⚠️ อัปเดต Manifest ของ BP ไม่สำเร็จ: {msg}")
        else:
            log.append("✅ อัปเดต dependencies ใน BP manifest")

    generated_count = 0
    generated_scripts: List[str] = []

    for item_path in items:
        identifier = t.get_identifier(item_path)
        if not identifier:
            log.append(f"⚠️ ข้าม (อ่าน identifier ไม่ได้): {item_path}")
            continue

        entity_ids = {"attack": [], "skill": []}
        dummy_id = f"{identifier}_dummy_entity"

        if gen_bp:
            t.create_dummy_entity(bp_path, dummy_id)

        for j in range(1, 4):
            atk_id = f"{identifier}_attack_cube_{j}"
            atk_sec_id = f"{identifier}_attack_cube_{j}_sec"
            skill_id = f"{identifier}_skill_cube_{j}"
            skill_sec_id = f"{identifier}_skill_cube_{j}_sec"

            entity_ids["attack"].append(atk_id)
            entity_ids["skill"].append(skill_id)

            if gen_bp:
                if opt(f"atk{j}"): t.create_bp_entity(bp_path, atk_id)
                if opt(f"atk{j}_sec"): t.create_bp_entity(bp_path, atk_sec_id)
                if opt(f"sk{j}"): t.create_bp_entity(bp_path, skill_id)
                if opt(f"sk{j}_sec"): t.create_bp_entity(bp_path, skill_sec_id)

            if gen_rp:
                if opt(f"atk{j}"): t.create_rp_entity(rp_path, atk_id)
                if opt(f"atk{j}_sec"): t.create_rp_entity(rp_path, atk_sec_id)
                if opt(f"sk{j}"): t.create_rp_entity(rp_path, skill_id)
                if opt(f"sk{j}_sec"): t.create_rp_entity(rp_path, skill_sec_id)

        if gen_bp:
            script_filename = t.generate_script(bp_path, identifier, entity_ids, dummy_id)
            generated_scripts.append(script_filename)
            log.append(f"✅ สร้างสคริปต์: {script_filename}")

        generated_count += 1
        log.append(f"✅ ไอเทม: {identifier}")

    if gen_bp and generated_scripts:
        t.setup_main_script_and_manifest(bp_path, generated_scripts)
        log.append(f"✅ ตั้งค่า main.js รวม {len(generated_scripts)} สคริปต์")

    if generated_count == 0:
        raise ValueError("สร้างไม่สำเร็จ — ตรวจสอบว่าไฟล์ JSON ของไอเทมถูกต้อง")

    log.append(f"🎉 สำเร็จ {generated_count} ไอเทม")
    return {"log": log, "scripts": generated_scripts, "count": generated_count}
