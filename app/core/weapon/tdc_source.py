"""TDC weapon-addon data + generator functions, extracted verbatim from
สร้างท่าโจมตี+สกิลอาวุธ.py (lines 1..2171).
Only the tkinter imports and the GUI classes/main were dropped; everything
here — TRANSLATIONS, TOOLTIPS, effect templates, BASE_CONFIG, JS_TEMPLATE,
and the create_*/generate_script helpers — is byte-for-byte the original so
generated scripts stay identical.
"""
import os
import json
import base64
import re
import uuid
import copy

# ==================== DICTIONARY แปลภาษา & EMOJI ====================
TRANSLATIONS = {
    "TARGET_ITEM": "🆔 ไอดีอาวุธหลัก",
    "WEAPON_SWAP": "⚔️ ระบบสลับอาวุธ (Weapon Swap)",
    "target_weapon_id": "🆔 ไอดีอาวุธเป้าหมาย (ที่จะสลับ)",
    "DUMMY_TYPE": "🎯 ชนิดเป้าซ้อม",
    "DUMMY_INVISIBLE": "👻 ซ่อนเป้าซ้อมล่องหน",
    "DUMMY_SHOW_NAME": "🏷️ โชว์ชื่อเป้าซ้อม",
    "HIT_DISTANCE": "📏 ระยะเป้าซ้อม (บล็อก)",
    "HEIGHT_OFFSET": "↕️ ความสูงเป้าซ้อม (+สูง/-ต่ำ)",
    "ENABLE_SPECIAL_ATTACK": "⚔️ เปิดปุ่ม [โจมตีพิเศษ] ในหน้าเมนู UI",
    "enabled": "เปิดใช้งาน",
    "type": "🧩 ชนิด Entity / มอนสเตอร์",
    "invisible": "👻 ล่องหนโมเดล",
    "show_name": "🏷️ แสดงชื่อ Entity",
    "duration_ticks": "⏳ เวลาคงอยู่ (20 Ticks = 1 วิ)",
    "damage_bonus": "⚔️ พลังโจมตีบวกเพิ่ม",
    "damage_interval_ticks": "⏱️ ความถี่ในการทำดาเมจ (Ticks)",
    "cast_duration_ticks": "⏳ ระยะเวลาร่ายสกิล (Ticks) - [ห้ามขยับ]",
    "cooldown_duration_ticks": "❄️ คูลดาวน์สกิล (Ticks)",
    
    # --- UI SETTINGS ---
    "UI_SETTINGS": "🖥️ การตั้งค่าหน้าต่างเมนู (UI)",
    "main_menu": "🏠 เมนูหลัก (Main Menu)",
    "title": "🔠 หัวข้อเมนู",
    "body": "📝 ข้อความอธิบายเมนู",
    "btn_special_attack_text": "🔠 ชื่อปุ่ม: โจมตีพิเศษ",
    "icon_special_attack": "🖼️ ไอคอน: โจมตีพิเศษ",
    "btn_skill_prefix": "🔠 คำนำหน้าปุ่มสกิล",
    "icon_skill": "🖼️ ไอคอน: สกิล",
    "btn_weapon_swap_text": "🔠 ชื่อปุ่ม: สลับอาวุธ",
    "icon_weapon_swap": "🖼️ ไอคอน: สลับอาวุธ",
    "btn_ally_menu_text": "🔠 ชื่อปุ่ม: ตั้งค่าพันธมิตร",
    "icon_ally_menu": "🖼️ ไอคอน: ตั้งค่าพันธมิตร",
    "ally_system": "🤝 ระบบพันธมิตร (Ally System Menu)",
    "menu_title": "🔠 หัวข้อเมนูพันธมิตร",
    "menu_body": "📝 ข้อความอธิบายเมนูพันธมิตร",
    "btn_list_ally": "🔠 ชื่อปุ่ม: ดูรายชื่อ",
    "icon_list_ally": "🖼️ ไอคอน: รายชื่อ",
    "btn_add_ally": "🔠 ชื่อปุ่ม: เพิ่มคน",
    "icon_add_ally": "🖼️ ไอคอน: เพิ่ม",   
    "btn_remove_ally": "🔠 ชื่อปุ่ม: เตะคนออก",
    "icon_remove_ally": "🖼️ ไอคอน: เตะออก",
    "btn_back": "🔠 ชื่อปุ่ม: ย้อนกลับ",
    "icon_back": "🖼️ ไอคอน: ย้อนกลับ",

    # --- SECONDARY ENTITY ---
    "secondary_entity": "👥 Entity รอง (เสกตามหลังตัวหลัก)",
    "spawn_delay_ticks": "⏱️ ดีเลย์ก่อนปล่อยตัวรอง (Ticks)",

    # --- PARTICLE TRAIL ---
    "particle_trail": "✨ เอฟเฟกต์พาติคอล (Particle Trail)",
    "particle_id": "🆔 ไอดีพาติคอล (เช่น minecraft:basic_flame_particle)",
    "spawn_interval_ticks": "⏱️ ความถี่การเกิดพาติคอล (Ticks)",
    "active_duration_ticks": "⏳ ระยะเวลาที่ปล่อยพาติคอล (Ticks)",
    "amount": "🔢 จำนวนเส้น/จุดต่อครั้ง",
    "scale": "🔍 ขนาดพาติคอล (Scale)",
    "y_offset": "↕️ ความสูงพาติคอล",
    "radius": "📏 รัศมีกระจายตัว",
    "mode_trail": "☄️ ทิ้งหางตามหลัง (Trail)",
    "mode_spiral": "🌀 หมุนวนรอบตัว (Spiral)",
    "mode_aura": "⭕ วงแหวนออร่ารอบตัว (Aura)",
    "mode_sphere": "🔮 ทรงกลมล้อมรอบ (Sphere)",
    "mode_random_burst": "💥 ระเบิดกระจายสุ่ม (Random Burst)",

    # --- MOVEMENT ---
    "movement": "🚀 ทิศทางการเคลื่อนที่ของสกิล",
    "speed": "💨 ความเร็วในการพุ่ง/บิน (Base Speed)",
    "shared_search_radius": "🎯 รัศมีค้นหาเป้าหมาย (บล็อก)",
    "max_targets": "🔢 จำนวนเป้าหมายสูงสุด",
    "spawn_style": "📍 รูปแบบจุดเกิด",
    "spawn_y_offset": "↕️ ระยะความสูง Y (เฉพาะ burrow/sky)",
    "spawn_approach_speed": "💨 ความเร็วดึงเข้าหาเป้าหมาย (เฉพาะ burrow/sky)",
    
    "mode_static": "🛑 ยืนนิ่งอยู่กับที่",
    "mode_move_forward": "⬆️ พุ่งไปข้างหน้าทิศเดียว",
    "mode_follow_cursor": "🎯 วิ่งตามเมาส์ตลอดเวลา",
    "mode_follow_cursor_distance": "📏 ล็อกเป้าตามระยะเมาส์",
    "follow_distance": "📍 ระยะห่างจากผู้ใช้",
    "mode_summon_closest": "✨ วาร์ปไปหาศัตรูที่ใกล้สุด",
    "mode_walk_to_closest": "🚶 เดินพุ่งไปหาศัตรูที่ใกล้สุด",
    "mode_instant_teleport_attack": "⚡ วาร์ปไปตีเป้าหมายทันที (Instant)",
    "mode_random_around": "🎲 สุ่มเสกโจมตีรอบตัว",
    
    "mode_boomerang": "🪃 บินไปแล้ววนกลับ",
    "boomerang_distance": "📏 ระยะทางก่อนบินกลับ",
    "mode_orbital": "🪐 โคจรรอบตัวผู้เล่น",
    "orbital_radius": "📏 รัศมีวงโคจร",
    "mode_chain_ricochet": "⚡ ชิ่งกระดอนหาศัตรูถัดไป",
    "ricochet_bounces": "🔄 จำนวนครั้งที่ชิ่ง",
    "ricochet_radius": "📏 ระยะค้นหาเป้าหมายชิ่ง",
    "mode_delayed_homing": "☄️ ลอยค้างฟ้าแล้วพุ่งนำวิถี",
    "delay_ticks": "⏱️ หน่วงเวลาก่อนพุ่ง (Ticks)",
    "mode_toggle_hover_on_head": "✨ เสกออร่าลอยบนหัว (เปิด/ปิด)",
    "hover_height": "↕️ ความสูงออร่า",
    
    "destroy_on_hit": "💥 ทำลายทิ้งทันทีเมื่อชนเป้าหมาย",
    "respawn_on_hit": "🔄 เสกตัวใหม่เมื่อชนเป้าหมาย (Respawn on Hit)",
    "respawn_count": "🔢 จำนวนสูงสุดที่จะเสกซ้ำ",
    "respawn_interval_ticks": "⏱️ ดีเลย์การเสกซ้ำ (Ticks)",
    "player_dash": "🏃 พุ่งไปยังจุดที่สกิลหายไป/ชนเป้าหมาย (Dash)",
    "player_teleport_dash": "✨ วาร์ปไปยังจุดที่สกิลหายไป/ชน (Teleport)",
    "teleport_dash_distance": "📏 ระยะทางวาร์ป",
    "mode_grappling_hook": "🪝 ดึงศัตรูมาหาเรา (Hook)",
    "mode_parabola": "🌋 ยิงวิถีโค้งตกตามแรงโน้มถ่วง",
    "gravity_pull": "⏬ แรงโน้มถ่วงดึงลง",
    "mode_sine_wave": "🧬 เคลื่อนที่ส่ายเป็นคลื่น",
    "wave_amplitude": "↔️ ความกว้างของคลื่น",
    "wave_frequency": "〰️ ความเร็วของคลื่น",

    "messages": "💬 ข้อความแจ้งเตือน",
    "casting": "⏳ ข้อความร่ายเวทย์",
    "cooldown": "❄️ ข้อความติดคูลดาวน์",
    "ready": "✅ ข้อความพร้อมใช้",
    
    # --- EFFECTS OVERHAUL ---
    "effects_special": "💥 เอฟเฟคพิเศษ (กระเด็น, ดูด, ไฟ, ฮีล, เสียง, ฯลฯ)",
    "effects_buffs": "🟢 เอฟเฟคด้านดี (Buffs)",
    "effects_debuffs": "🔴 เอฟเฟคด้านเสีย (Debuffs)",
    
    "is_buff": "✅ เป็นบัฟ (แจกให้พันธมิตรเท่านั้น)",
    "knockback": "💨 กระเด็นถอยหลัง",
    "vacuum": "🌌 ดูดศัตรูเข้าหา",
    "fire": "🔥 ติดไฟเผาไหม้",
    "heal": "💖 ฮีลพลังชีวิต",
    "strength": "💪 พละกำลัง (ตีแรง)",
    "duration": "⏳ เวลาคงอยู่ (วินาที)",
    "amplifier": "📈 เลเวลเอฟเฟกต์ (0 = Lv.1)",
    
    "absorption": "💛 โล่สีทอง",
    "bad_omen": "👺 ลางร้าย (Bad Omen)",
    "blindness": "👁️‍🗨️ ตาบอด",
    "conduit_power": "🌀 พลังคอนดิวต์",
    "darkness": "🌑 มืดมิด (Darkness)",
    "dolphins_grace": "🐬 พรโลมา",
    "fatal_poison": "💀 ติดพิษรุนแรง (ลดเลือดถึงตาย)",
    "fire_resistance": "🌋 กันไฟ",
    "haste": "⚡ รีบเร่ง (ขุด/ตีไว)",
    "health_boost": "❤️ เพิ่มหลอดเลือด",
    "hero_of_the_village": "🦸 ฮีโร่หมู่บ้าน",
    "hunger": "🍖 หิวโหย",
    "infested": "🪲 แมลงติดตัว (1.21 โดนตีแล้วมี Silverfish)",
    "invisibility": "👻 ล่องหน",
    "jump_boost": "🦘 กระโดดสูง",
    "levitation": "🎈 ลอยตัวขึ้นฟ้า",
    "mining_fatigue": "🐌 ขุด/ตีช้า (Mining Fatigue)",
    "nausea": "😵 เวียนหัว (จอโยก)",
    "night_vision": "🦉 มองเห็นตอนกลางคืน",
    "oozing": "🤢 เมือกสไลม์ (1.21 ตายแล้วมี Slime)",
    "poison": "☠️ ติดพิษ",
    "regeneration": "💖 ฟื้นฟูเลือด",
    "resistance": "🛡️ ต้านทานดาเมจ",
    "saturation": "🍔 อิ่มเอม (เติมหลอดอาหาร)",
    "slow_falling": "🪂 ร่วงหล่นช้า",
    "slowness": "🐢 เดินช้า",
    "speed": "💨 วิ่งเร็ว",
    "water_breathing": "🤿 หายใจใต้น้ำ",
    "weakness": "💔 อ่อนแอ (ตีเบาลง)",
    "weaving": "🕸️ ถักทอใย (1.21 ตายแล้วกางใย)",
    "wind_charged": "🌪️ ชาร์จสายลม (1.21 ตายแล้วลมระเบิด)",
    "wither": "🖤 วิเธอร์ (ลดเลือดจนตาย)",

    "sounds": "🔊 เสียงเอฟเฟกต์",
    "list": "📋 รายชื่อเสียง",
    "camera_shake": "🫨 เขย่าหน้าจอ",
    "intensity": "💥 ความรุนแรงสั่นจอ",
    "duration_seconds": "⏳ เวลา (วินาที)",
    "title": "🔠 โชว์ตัวหนังสือบนจอ",
    "text": "📝 ข้อความ",
    "forced_animation": "🎬 บังคับเล่นอนิเมชัน",
    "start_anim": "▶️ ท่าเริ่มต้น",
    "end_anim": "⏹️ ท่าตอนจบ",
    "end_duration_ticks": "⏱️ เวลาท่าตอนจบ",
    "block_trail": "🧱 สร้างทางเดินบล็อก",
    "radius_xz": "↔️ รัศมีแนวนอน",
    "radius_y": "↕️ รัศมีแนวตั้ง",
    "blocks": "📦 รายชื่อบล็อก",
    "summon_minions": "🧟 เสกลูกน้อง",
    "spawn_radius": "📏 รัศมีเกิดลูกน้อง",
    "auto_tame": "🐾 จับเป็นสัตว์เลี้ยงอัตโนมัติ (โจมตีศัตรู)",
    "types": "👾 ชนิดลูกน้อง",
    "area_settings": "📍 ตั้งค่าเป้าหมายสกิล",
    "use_around_radius": "🔄 โจมตีรอบตัว",
    "around_radius": "📏 รัศมีรอบตัว",
    "front_range": "⬆️ โจมตีด้านหน้า",
    "forward": "⬆️ ด้านหน้า",
    "width": "↔️ ความกว้าง",
    "height": "↕️ ความสูง",
    "life_steal": "🧛 ระบบดูดเลือด",
    "heal_percent": "🩸 เปอร์เซ็นต์ดูดเลือด",
    "shield_barrier": "🛡️ เกราะโล่ป้องกัน",
    "critical_system": "⚡ ระบบคริติคอล",
    "crit_chance": "🎲 โอกาสคริติคอล",
    "crit_multiplier": "💥 ตัวคูณดาเมจ",
    "hit_counter": "⚔️ ระบบสะสมฮิตคอมโบ",
    "required_hits": "🎯 จำนวนฮิตที่ต้องการ",
    "apply_debuff_to_target": "🦠 ปล่อยดีบัฟ",
    "run_command": "💻 รันคำสั่ง",
    "time_based_passive": "⏳ บัฟ/ดาเมจ อัตโนมัติ",
    "on_kill_perks": "💀 โบนัสเมื่อฆ่า",
    "low_health_panic": "🚨 โหมดเลือดน้อยคลุ้มคลั่ง",
    "sneak_perks": "🥷 โบนัสย่อตัว",
    "environment_adaptation": "🌍 บัฟตามสภาพแวดล้อม",
    "death_defiance": "👼 โกงความตาย",
    "ANIMATIONS": "🎬 คีย์อนิเมชัน",
    
    # --- ANIMATION KEYS ---
    "idle": "🧍 ยืนนิ่ง (Idle)",
    "walk": "🚶 เดิน (Walk)",
    "run": "🏃 วิ่ง (Run)",
    "attack1": "🗡️ ท่าโจมตี 1",
    "attack2": "🗡️ ท่าโจมตี 2",
    "attack3": "🗡️ ท่าโจมตี 3",
    "use_skill1": "🔮 ท่าร่ายสกิล 1",
    "use_skill2": "🔮 ท่าร่ายสกิล 2",
    "use_skill3": "🔮 ท่าร่ายสกิล 3",
    "sneak": "🥷 ย่อตัว (Sneak)",
    "sit": "🪑 นั่ง (Sit)",
    "swim": "🏊 ว่ายน้ำ",
    "swimming": "🏊 ว่ายน้ำเคลื่อนที่",
    "fly": "👼 ลอยตัว (Fly)",
    "flying": "👼 ลอยตัวเคลื่อนที่",
    "jump": "🦘 กระโดด (Jump)",
    "fall": "⏬ ร่วงหล่น (Fall)",
    "empty": "❌ อนิเมชั่นว่างเปล่า",
    
    # --- ANIMATION TIMERS (TICKS) ---
    "USE_ITEM_1_TIMEOUT_TICKS": "⏱️ เวลาค้างท่า สกิล 1",
    "USE_ITEM_2_TIMEOUT_TICKS": "⏱️ เวลาค้างท่า สกิล 2",
    "USE_ITEM_3_TIMEOUT_TICKS": "⏱️ เวลาค้างท่า สกิล 3",
    "ATTACK_DURATION_TICKS": "⏱️ เวลาค้างท่า โจมตีปกติ",
    "IDLE_ANIMATION_LENGTH_TICKS": "⏱️ ความยาวท่า ยืนนิ่ง",
    "WALK_DURATION_TICKS": "⏱️ ความยาวท่า เดิน",
    "RUN_DURATION_TICKS": "⏱️ ความยาวท่า วิ่ง",
    "SWIM_DURATION_TICKS": "⏱️ ความยาวท่า ว่ายน้ำ",
    "SWIMMING_DURATION_TICKS": "⏱️ ความยาวท่า ว่ายน้ำเคลื่อนที่",
    "FLY_DURATION_TICKS": "⏱️ ความยาวท่า ลอยตัว",
    "FLYING_DURATION_TICKS": "⏱️ ความยาวท่า ลอยตัวเคลื่อนที่",
    "JUMP_DURATION_TICKS": "⏱️ ความยาวท่า กระโดด",
    "FALL_DURATION_TICKS": "⏱️ ความยาวท่า ร่วงหล่น",
    "SNEAK_DURATION_TICKS": "⏱️ ความยาวท่า ย่อตัว",
    "SIT_DURATION_TICKS": "⏱️ ความยาวท่า นั่ง"
}

# ==================== TOOLTIPS ====================
TOOLTIPS = {
    "shared_search_radius": "🔗 ใช้ร่วมกับ: \n- วาร์ปหาศัตรู\n- เดินหาศัตรู\n- วาร์ปไปตีทันที\n- สุ่มเสกรอบตัว",
    "spawn_style": "📍 รูปแบบการเกิด:\nfrom_player = เกิดที่ตัวเรา\nground = เกิดที่พื้นดินเป้าหมาย\nburrow = มุดจากใต้ดินขึ้นมา\nsky = ร่วงลงมาจากฟ้า",
    "destroy_on_hit": "💥 หากเปิด: เมื่อสกิลชนโดนศัตรู มันจะหายไปทันที\n(แนะนำให้ใช้คู่กับระบบ Dash/Teleport เพื่อให้ตัวเราพุ่งไปหาศัตรูเมื่อชนสำเร็จ)",
    "mode_instant_teleport_attack": "⚡ วาร์ปไปหาเป้าหมายและทำดาเมจทันที (อารมณ์เหมือนสกิลพุ่งฟันสายฟ้า)",
    "mode_random_around": "🎲 สุ่มเกิดจุดรอบๆ ตัวเราตาม Shared Radius เหมาะทำสกิลสุ่มระเบิดลงพื้น",
    "mode_chain_ricochet": "⚡ สกิลที่ชนตัวแรกแล้วจะหักเลี้ยวล็อคเป้าพุ่งไปหาตัวต่อไปอัตโนมัติ",
    "mode_grappling_hook": "🪝 ไอเดียการใช้งาน:\nเมื่อสกิลชนเป้าหมายสำเร็จ จะทำการดึงศัตรูตัวนั้นให้ปลิวมาอยู่ตรงหน้าผู้เล่นระยะ 1.5 บล็อกทันที เหมาะสำหรับทำสกิลจับหรือดึงมอนสเตอร์",
    "player_dash": "🏃 การพุ่งตัว (Velocity):\nตัวผู้เล่นจะพุ่งตามไป **ก็ต่อเมื่อ** สกิลหายไป, หมดเวลา, หรือชนเป้าหมาย (ต้องเปิดใช้งาน destroy_on_hit หากต้องการพุ่งไปฟันศัตรู)",
    "player_teleport_dash": "✨ การวาร์ปตัว (Instant TP):\nตัวผู้เล่นจะวาร์ปไป **ก็ต่อเมื่อ** สกิลหายไป, หมดเวลา, หรือชนเป้าหมาย (ต้องเปิดใช้งาน destroy_on_hit หากต้องการวาร์ปไปหาศัตรู)",
    "secondary_entity": "👥 ระบบจะทำการเสก Entity ตัวนี้ออกมาช่วยโจมตี โดยตามหลังตัวหลักมา",
    "spawn_delay_ticks": "⏱️ ระยะเวลาที่ต้องรอ (20 Ticks = 1 วินาที) โดยเริ่มนับถอยหลังทันทีตั้งแต่ที่สกิลตัวหลักถูกปล่อยออกมา",
    "respawn_on_hit": "🔄 เมื่อสกิล/มอนสเตอร์ ชนเป้าหมาย จะทำการเสกตัวมันเองออกมาซ้ำอีกครั้งตามจำนวนและเวลาที่กำหนด\n(ระยะเวลาการเสกซ้ำจะหยุดลงเมื่อเวลาของสกิลต้นฉบับหมดลง)",
    "auto_tame": "🐾 เมื่อเสกออกมา ระบบจะทำการ Tame มอนสเตอร์ให้เป็นของเราทันที และมันจะวิ่งไล่โจมตีศัตรูทั้งหมดโดยไม่ตีเราและพันธมิตร",
    "is_buff": "✅ หากติ๊กช่องนี้ เอฟเฟกต์จะไปติดที่ 'พันธมิตร / ผู้เล่น' แทน (ถ้าไม่ติ๊ก จะแจกใส่ศัตรู)",
    "cast_duration_ticks": "⏳ ระบบใหม่: ขณะที่ร่ายเวทย์ ตัวละครจะขยับไม่ได้และกระโดดไม่ได้เลย จนกว่าเวลาจะหมด"
}

# ==================== VISUAL HIERARCHY TREE ====================
HIERARCHY_MAP = {
    "shared_search_radius": {"group": "🔗 โหนดส่วนกลาง (Shared Dependencies)", "prefix": "   ┣━ "},
    "max_targets": {"group": "🔗 โหนดส่วนกลาง (Shared Dependencies)", "prefix": "   ┗━ "},
    
    "spawn_delay_ticks": {"group": "📍 โหนดจุดเกิด (Spawn Phase)", "prefix": "   ┣━ "},
    "spawn_style": {"group": "📍 โหนดจุดเกิด (Spawn Phase)", "prefix": "   ┣━ "},
    "spawn_y_offset": {"group": "📍 โหนดจุดเกิด (Spawn Phase)", "prefix": "   ┣━ "},
    "spawn_approach_speed": {"group": "📍 โหนดจุดเกิด (Spawn Phase)", "prefix": "   ┗━ "},
    
    "mode_static": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_move_forward": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_follow_cursor": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_summon_closest": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_walk_to_closest": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_instant_teleport_attack": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_random_around": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "mode_follow_cursor_distance": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┣━ "},
    "follow_distance": {"group": "🎯 โหนดโหมดการทำงานหลัก (Primary Modes)", "prefix": "   ┗━ "},
    
    "destroy_on_hit": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "respawn_on_hit": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "respawn_count": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "respawn_interval_ticks": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "player_dash": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "player_teleport_dash": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "teleport_dash_distance": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_boomerang": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "boomerang_distance": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_orbital": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "orbital_radius": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_chain_ricochet": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "ricochet_bounces": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "ricochet_radius": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_delayed_homing": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "delay_ticks": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_toggle_hover_on_head": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "hover_height": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_grappling_hook": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_parabola": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "gravity_pull": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "mode_sine_wave": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "wave_amplitude": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┣━ "},
    "wave_frequency": {"group": "⚙️ โหนดส่วนเสริม (Secondary Modifiers)", "prefix": "   ┗━ "},

    "particle_id": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "spawn_interval_ticks": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "active_duration_ticks": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "amount": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "scale": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "y_offset": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "radius": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "mode_trail": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "mode_spiral": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "mode_aura": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "mode_sphere": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┣━ "},
    "mode_random_burst": {"group": "✨ โหนดรูปทรงพาติคอล (Particle System)", "prefix": "   ┗━ "},
}

KEY_COLORS = {
    "ENABLE_SPECIAL_ATTACK": "#28a745", "is_buff": "#28a745", "heal": "#e83e8c", "fire": "#d32f2f", 
    "vacuum": "#6f42c1", "shared_search_radius": "#d35400", "spawn_style": "#8e44ad",
    "destroy_on_hit": "#c0392b", "respawn_on_hit": "#c0392b", "mode_instant_teleport_attack": "#2980b9",
    "WEAPON_SWAP": "#d35400", "target_weapon_id": "#2980b9", "secondary_entity": "#6f42c1",
    "particle_trail": "#8e44ad", "particle_id": "#e67e22", "auto_tame": "#28a745",
    "effects_special": "#e74c3c", "effects_buffs": "#27ae60", "effects_debuffs": "#c0392b"
}

ANIMATION_TIME_KEYS = ["USE_ITEM_1_TIMEOUT_TICKS", "USE_ITEM_2_TIMEOUT_TICKS", "USE_ITEM_3_TIMEOUT_TICKS", "ATTACK_DURATION_TICKS", "IDLE_ANIMATION_LENGTH_TICKS", "WALK_DURATION_TICKS", "RUN_DURATION_TICKS", "SWIM_DURATION_TICKS", "SWIMMING_DURATION_TICKS", "FLY_DURATION_TICKS", "FLYING_DURATION_TICKS", "JUMP_DURATION_TICKS", "FALL_DURATION_TICKS", "SNEAK_DURATION_TICKS", "SIT_DURATION_TICKS"]

# ==================== โครงสร้าง EFFECT TEMPLATE ที่แบ่งหมวดแล้ว ====================
SPECIAL_EFFECTS_TEMPLATE = {
    "knockback": {"enabled": False, "strength": 0.0, "delay_ticks": 0},
    "vacuum": {"enabled": False, "strength": 0.0, "delay_ticks": 0},
    "fire": {"enabled": False, "is_buff": False, "duration": 0, "delay_ticks": 0},
    "heal": {"enabled": False, "is_buff": True, "amount": 0, "delay_ticks": 0},
    "title": {"enabled": False, "text": "§l§cHit!"},
    "camera_shake": {"enabled": False, "intensity": 1.0, "duration_seconds": 1},
    "sounds": {"enabled": False, "delay_ticks": 10, "list": ["random.explode"]},
    "forced_animation": {"enabled": False, "start_anim": "animation.????.????", "duration_ticks": 20, "end_anim": "animation.????.empty", "end_duration_ticks": 100}
}

BUFFS_TEMPLATE = {
    "absorption": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "conduit_power": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "dolphins_grace": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "fire_resistance": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "haste": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "health_boost": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "hero_of_the_village": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "invisibility": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "jump_boost": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "night_vision": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "regeneration": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "resistance": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "saturation": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "slow_falling": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "speed": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "strength": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0},
    "water_breathing": {"enabled": False, "is_buff": True, "amplifier": 0, "duration": 0}
}

DEBUFFS_TEMPLATE = {
    "bad_omen": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "blindness": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "darkness": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "fatal_poison": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "hunger": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "infested": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "levitation": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "mining_fatigue": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "nausea": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "oozing": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "poison": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "slowness": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "weakness": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "weaving": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "wind_charged": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0},
    "wither": {"enabled": False, "is_buff": False, "amplifier": 0, "duration": 0}
}

def generate_default_entity(is_skill=False):
    return {
        "enabled": True,  # แก้ไขจาก False if not is_skill else True ให้เปิดเสมอ
        "name": "§lสกิล" if is_skill else "โจมตี",
        "type": "tdcmodel:",
        "invisible": False,
        "show_name": False,
        "duration_ticks": 60,
        "damage_interval_ticks": 20,
        "damage_bonus": 5,
        "cast_duration_ticks": 0 if not is_skill else 10,
        "cooldown_duration_ticks": 0 if not is_skill else 40,
        "secondary_entity": {
            "enabled": False,
            "spawn_delay_ticks": 20,
            "type": "minecraft:zombie",
            "invisible": False,
            "show_name": False,
            "duration_ticks": 60,
            "damage_interval_ticks": 20,
            "damage_bonus": 5,
            "area_settings": {"use_around_radius": False, "around_radius": 0.0, "front_range": {"forward": 3.0, "width": 2.0, "height": 2.5}},
            "movement": {"speed": 0.0, "shared_search_radius": 15.0, "max_targets": 5, "spawn_style": "from_player", "spawn_y_offset": 10.0, "spawn_approach_speed": 1.0, "mode_static": False, "mode_follow_cursor": False, "mode_move_forward": False, "mode_follow_cursor_distance": False, "follow_distance": 0.0, "mode_summon_closest": False, "mode_walk_to_closest": False, "mode_instant_teleport_attack": False, "mode_random_around": False, "mode_boomerang": False, "boomerang_distance": 5.0, "mode_orbital": False, "orbital_radius": 2.0, "mode_chain_ricochet": False, "ricochet_bounces": 3, "ricochet_radius": 10.0, "mode_delayed_homing": False, "delay_ticks": 20, "mode_toggle_hover_on_head": False, "hover_height": 1.0, "destroy_on_hit": False, "respawn_on_hit": False, "respawn_count": 5, "respawn_interval_ticks": 20, "player_dash": False, "player_teleport_dash": False, "teleport_dash_distance": 0.0, "mode_grappling_hook": False, "mode_parabola": False, "gravity_pull": 0.05, "mode_sine_wave": False, "wave_amplitude": 1.0, "wave_frequency": 0.5},
            "particle_trail": {"enabled": False, "particle_id": "minecraft:basic_flame_particle", "spawn_interval_ticks": 2, "active_duration_ticks": 60, "amount": 3, "scale": 1.0, "y_offset": 1.0, "radius": 0.5, "mode_trail": True, "mode_spiral": False, "mode_aura": False, "mode_sphere": False, "mode_random_burst": False},
            "block_trail": {"enabled": False, "radius_xz": 0, "radius_y": 0, "duration_ticks": 60, "blocks": ["minecraft:web"]},
            "summon_minions": {"enabled": False, "amount": 1, "spawn_radius": 3.0, "duration_ticks": 100, "types": ["minecraft:zombie"], "show_name": False, "auto_tame": True},
            "effects_special": json.loads(json.dumps(SPECIAL_EFFECTS_TEMPLATE)),
            "effects_buffs": json.loads(json.dumps(BUFFS_TEMPLATE)),
            "effects_debuffs": json.loads(json.dumps(DEBUFFS_TEMPLATE))
        },
        "messages": {"casting": "§l§eกำลังร่าย... เหลือเวลา: §b{time} วิ", "cooldown": "§l§cติดคูลดาวน์: §e{time} วิ", "ready": "§l§aพร้อมใช้งาน!"} if is_skill else {},
        "area_settings": {"use_around_radius": False, "around_radius": 0.0, "front_range": {"forward": 3.0, "width": 2.0, "height": 2.5}},
        "movement": {"speed": 0.0, "shared_search_radius": 15.0, "max_targets": 5, "spawn_style": "from_player", "spawn_y_offset": 10.0, "spawn_approach_speed": 1.0, "mode_static": False, "mode_follow_cursor": False, "mode_move_forward": False, "mode_follow_cursor_distance": False, "follow_distance": 0.0, "mode_summon_closest": False, "mode_walk_to_closest": False, "mode_instant_teleport_attack": False, "mode_random_around": False, "mode_boomerang": False, "boomerang_distance": 5.0, "mode_orbital": False, "orbital_radius": 2.0, "mode_chain_ricochet": False, "ricochet_bounces": 3, "ricochet_radius": 10.0, "mode_delayed_homing": False, "delay_ticks": 20, "mode_toggle_hover_on_head": False, "hover_height": 1.0, "destroy_on_hit": False, "respawn_on_hit": False, "respawn_count": 5, "respawn_interval_ticks": 20, "player_dash": False, "player_teleport_dash": False, "teleport_dash_distance": 0.0, "mode_grappling_hook": False, "mode_parabola": False, "gravity_pull": 0.05, "mode_sine_wave": False, "wave_amplitude": 1.0, "wave_frequency": 0.5},
        "particle_trail": {"enabled": False, "particle_id": "minecraft:basic_flame_particle", "spawn_interval_ticks": 2, "active_duration_ticks": 60, "amount": 3, "scale": 1.0, "y_offset": 1.0, "radius": 0.5, "mode_trail": True, "mode_spiral": False, "mode_aura": False, "mode_sphere": False, "mode_random_burst": False},
        "block_trail": {"enabled": False, "radius_xz": 0, "radius_y": 0, "duration_ticks": 60, "blocks": ["minecraft:web"]},
        "summon_minions": {"enabled": False, "amount": 1, "spawn_radius": 3.0, "duration_ticks": 100, "types": ["minecraft:zombie"], "show_name": False, "auto_tame": True},
        "effects_special": json.loads(json.dumps(SPECIAL_EFFECTS_TEMPLATE)),
        "effects_buffs": json.loads(json.dumps(BUFFS_TEMPLATE)),
        "effects_debuffs": json.loads(json.dumps(DEBUFFS_TEMPLATE))
    }

BASE_CONFIG = {
    "TARGET_ITEM": "tdcmodel:",
    "WEAPON_SWAP": {"enabled": True, "target_weapon_id": "tdcmodel:target"},
    "DUMMY_TYPE": "tdcmodel:",
    "DUMMY_INVISIBLE": False,
    "DUMMY_SHOW_NAME": False,
    "HIT_DISTANCE": 1.5,
    "HEIGHT_OFFSET": 0,
    "ENABLE_SPECIAL_ATTACK": False,
    "UI_SETTINGS": {
        "main_menu": {
            "title": "§l§5✨ System Menu ✨",
            "body": "§l§eโปรดเลือกรูปแบบการโจมตี/สกิล หรือตั้งค่าพันธมิตร:",
            "btn_special_attack_text": "§lโจมตีพิเศษ",
            "icon_special_attack": "textures/items/iron_sword",
            "btn_skill_prefix": "§l[สกิล",
            "icon_skill": "textures/items/book_enchanted",
            "btn_weapon_swap_text": "§l[สลับอาวุธ]",
            "icon_weapon_swap": "textures/ui/refresh",
            "btn_ally_menu_text": "§l§a[ตั้งค่าพันธมิตร]",
            "icon_ally_menu": "textures/ui/icon_steve"
        },
        "ally_system": {
            "enabled": True,
            "menu_title": "§l§a🤝 ระบบพันธมิตร (Ally System)",
            "menu_body": "§l§eจัดการรายชื่อผู้เล่นที่จะไม่ได้รับความเสียหายจากคุณ และจะได้รับบัฟดีๆ จากสกิลแทน!\n§7(รายชื่อจะถูกบันทึกติดตัวไปถาวร)",
            "btn_list_ally": "§l[รายชื่อพันธมิตร]",
            "icon_list_ally": "textures/items/book_normal",
            "btn_add_ally": "§l[เพิ่มพันธมิตร]",
            "icon_add_ally": "textures/ui/color_plus",
            "btn_remove_ally": "§l[ลบพันธมิตร]",
            "icon_remove_ally": "textures/ui/cancel",
            "btn_back": "§l§cย้อนกลับ",
            "icon_back": "textures/ui/refresh"
        }
    },
    "ATTACK_ENTITIES": {
        "attack1": generate_default_entity(),
        "attack2": generate_default_entity(),
        "attack3": generate_default_entity()
    },
    "SKILLS": {
        "skill1": generate_default_entity(True),
        "skill2": generate_default_entity(True),
        "skill3": generate_default_entity(True)
    },
    "RPG_MECHANICS": {
        "life_steal": {"enabled": False, "heal_percent": 0.0, "particle_effect": "minecraft:heart_particle"},
        "shield_barrier": {"enabled": False, "barrier_health": 0, "regen_cooldown_ticks": 0},
        "critical_system": {"enabled": False, "crit_chance": 0.0, "crit_multiplier": 0.0},
        "passive_buffs": {"enabled": False, "hide_particles": True, "speed": 0, "slowness": 0, "haste": 0, "mining_fatigue": 0, "strength": 0, "jump_boost": 0, "nausea": 0, "regeneration": 0, "resistance": 0, "hunger": 0, "weakness": 0, "poison": 0, "wither": 0, "health_boost": 0, "absorption": 0, "saturation": 0, "levitation": 0, "fatal_poison": 0, "bad_omen": 0, "hero_of_the_village": 0, "night_vision": False, "fire_resistance": False, "water_breathing": False, "invisibility": False, "blindness": False, "darkness": False, "slow_falling": False, "conduit_power": False, "dolphins_grace": False},
        "hit_counter": {"enabled": False, "required_hits": 5, "reduce_cooldown_ticks": 20, "heal_amount": 0, "trigger_sound": "random.levelup", "aoe_burst_damage": 0, "burst_radius": 5.0, "apply_debuff_to_target": {"enabled": False, "effect": "slowness", "duration_ticks": 60, "amplifier": 2}, "run_command": {"enabled": False, "command": "summon lightning_bolt ~ ~ ~"}, "self_buffs": {"enabled": False, "effect": "strength", "duration_ticks": 60, "amplifier": 1}},
        "time_based_passive": {"enabled": False, "interval_ticks": 100, "heal_amount": 0, "feed_hunger": 0, "give_exp": 0, "clear_debuffs": False, "aoe_damage": {"enabled": False, "radius": 4.0, "damage": 2}, "run_command": {"enabled": False, "command": "particle minecraft:heart_particle ~ ~2 ~"}},
        "on_kill_perks": {"enabled": False, "heal_amount": 0, "trigger_sound": "random.orb", "self_buffs": {"enabled": False, "effect": "regeneration", "duration_ticks": 60, "amplifier": 1}},
        "low_health_panic": {"enabled": False, "health_threshold": 6, "heal_instantly": 0, "trigger_sound": "mob.wither.spawn", "give_shield": {"enabled": False, "duration_ticks": 100, "amplifier": 2}, "speed_boost": {"enabled": False, "duration_ticks": 100, "amplifier": 2}, "cooldown_ticks": 600},
        "sneak_perks": {"enabled": False, "invisibility_while_sneaking": False, "heal_while_sneaking": 0},
        "environment_adaptation": {"enabled": False, "in_water_buffs": True, "in_rain_buffs": True},
        "death_defiance": {"enabled": False, "cooldown_ticks": 12000, "heal_amount": 20, "give_absorption": 4, "trigger_sound": "random.totem"}
    },
    "ANIMATIONS": {"idle": "animation.item.idle", "walk": "", "run": "", "swim": "", "swimming": "", "fly": "", "flying": "", "jump": "", "fall": "", "use_skill1": "", "use_skill2": "", "use_skill3": "", "attacks": ["", "", ""], "sneak": "", "sit": "", "empty": "animation.empty"},
    "USE_ITEM_1_TIMEOUT_TICKS": 0, "USE_ITEM_2_TIMEOUT_TICKS": 0, "USE_ITEM_3_TIMEOUT_TICKS": 0,
    "ATTACK_DURATION_TICKS": [5, 5, 5], "IDLE_ANIMATION_LENGTH_TICKS": 40, "WALK_DURATION_TICKS": 40, "RUN_DURATION_TICKS": 35, "SWIM_DURATION_TICKS": 0, "SWIMMING_DURATION_TICKS": 0, "FLY_DURATION_TICKS": 0, "FLYING_DURATION_TICKS": 0, "JUMP_DURATION_TICKS": 0, "FALL_DURATION_TICKS": 0, "SNEAK_DURATION_TICKS": 40, "SIT_DURATION_TICKS": 0
}


# ==================== JAVASCRIPT TEMPLATE STRING ====================
JS_TEMPLATE = r"""
import { world, system, EquipmentSlot, ItemStack, MolangVariableMap } from "@minecraft/server";
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";

// ===================================================================================================
// CONFIGURATION MATRIX
// ===================================================================================================
const CONFIG = __CONFIG_PLACEHOLDER__;

// ===================================================================================================
// NAMESPACE AUTO-PREFIX ISOLATION & EFFECT LISTS
// ===================================================================================================
const ITEM_PREFIX = CONFIG.TARGET_ITEM.replace(":", "_");

const SYS_TAGS = {
    SUMMONED: `${ITEM_PREFIX}_summoned`,
    SKILL: `${ITEM_PREFIX}_skill`,
    MINION: `${ITEM_PREFIX}_minion`,
    GLOBAL_IGNORE: "sys_tdc_weapon_entity" 
};

function safeHeal(entity, amount) {
    try {
        const hpComp = entity.getComponent("minecraft:health");
        if (hpComp) {
            let newHp = hpComp.currentValue + amount;
            let eMax = hpComp.effectiveMax || 20; 
            if (newHp > eMax) newHp = eMax;
            hpComp.setCurrentValue(newHp);
        }
    } catch(e) {}
}

const playerStates = new Map();         
const playerCombos = new Map();         
const playerActionTimers = new Map();   
const playerStateTimers = new Map();    
const playerClicking = new Map();       
const playerCastingData = new Map();    
const playerCooldownTimers = new Map(); 
const forcedEntityAnimations = new Map(); 
const playerHitCounts = new Map(); 
const playerPanicCooldowns = new Map(); 
const playerDeathDefianceCooldowns = new Map(); 
const playerSelectedSkill = new Map();

// Tracking sneak state for swap
const playerSneakState = new Map();
const playerSneakPref = new Map();

const activeComboEntities = new Map(); 
const activeSkillEntities = new Map(); 
const activeMinionEntities = new Map();
const entitySpawnPools = new Map(); 
const activeHoverEntities = new Map(); 
const activeRandomSpawners = new Map(); 
const pendingSecondarySpawns = new Map(); 
const activeHitSpawners = new Map(); 

const globalPlayerAllies = new Map(); 
const activeSkillBlocks = []; 

function cleanName(rawName) {
    if (!rawName) return "";
    return rawName.replace(/[\uE000-\uF8FF]/g, '').replace(/§./g, '').trim();
}

function getAllies(player) {
    if (!player || !player.isValid()) return new Map();
    if (globalPlayerAllies.has(player.id)) return globalPlayerAllies.get(player.id);
    const myAllies = new Map();
    
    if (!player.hasTag("tdc_ally_kicked_self")) {
        myAllies.set(player.id, cleanName(player.name));
    }
    
    try {
        for (const tag of player.getTags()) {
            if (tag.startsWith("tdc_ally:")) {
                const parts = tag.split(":");
                if (parts.length >= 3) {
                    const tId = parts[1];
                    const tName = parts.slice(2).join(":"); 
                    myAllies.set(tId, tName);
                }
            }
        }
    } catch(e){}
    globalPlayerAllies.set(player.id, myAllies);
    return myAllies;
}

function addAllyTag(player, tId, tName) {
    if (tId === player.id) {
        try { player.removeTag("tdc_ally_kicked_self"); } catch(e){}
    } else {
        try { player.addTag(`tdc_ally:${tId}:${cleanName(tName)}`); } catch(e){}
    }
    globalPlayerAllies.delete(player.id);
    getAllies(player);
}

function removeAllyTag(player, tId, tName) {
    if (tId === player.id) {
        try { player.addTag("tdc_ally_kicked_self"); } catch(e){}
    } else {
        try { player.removeTag(`tdc_ally:${tId}:${tName}`); } catch(e){}
    }
    globalPlayerAllies.delete(player.id);
    getAllies(player);
}

function clearPlayerSkills(player) {
    const mapsToClear = [activeComboEntities, activeSkillEntities, activeMinionEntities];
    for (const map of mapsToClear) {
        for (const [uid, data] of map.entries()) {
            if (data.playerId === player.id) {
                try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e){}
                freeRecycledId(data.poolKey, data.poolId);
                map.delete(uid);
            }
        }
    }
    for (const [key, uid] of activeHoverEntities.entries()) {
        if (key.startsWith(player.id)) activeHoverEntities.delete(key);
    }
    for (let i = 0; i < activeSkillBlocks.length; i++) {
        if (activeSkillBlocks[i].ownerId === player.id) activeSkillBlocks[i].forceClear = true;
    }
}

function cycleNextSkill(player) {
    let current = playerSelectedSkill.get(player.id) || (CONFIG.ENABLE_SPECIAL_ATTACK ? "special_attack" : "skill1");
    let sequence = [];
    if (CONFIG.ENABLE_SPECIAL_ATTACK) sequence.push("special_attack");
    for (let i = 1; i <= 3; i++) {
        if (CONFIG.SKILLS[`skill${i}`].enabled) sequence.push(`skill${i}`);
    }
    if (sequence.length <= 1) return; 

    let idx = sequence.indexOf(current);
    let nextIdx = (idx + 1) % sequence.length;
    let nextSkill = sequence[nextIdx];
    playerSelectedSkill.set(player.id, nextSkill);

    let sName = nextSkill === "special_attack" ? "โจมตีพิเศษ" : CONFIG.SKILLS[nextSkill].name;
    player.onScreenDisplay.setActionBar(`§l§a🔄 เปลี่ยนสกิลเป็น: ${sName}`);
    try { player.playSound("random.orb"); } catch(e){}
}

function getRecycledId(poolKey) {
    if (!entitySpawnPools.has(poolKey)) entitySpawnPools.set(poolKey, []);
    const activeIds = entitySpawnPools.get(poolKey);
    let id = 1;
    while (activeIds.includes(id)) id++;
    activeIds.push(id);
    return id;
}

function freeRecycledId(poolKey, id) {
    if (entitySpawnPools.has(poolKey)) {
        const activeIds = entitySpawnPools.get(poolKey);
        const idx = activeIds.indexOf(id);
        if (idx > -1) activeIds.splice(idx, 1);
    }
}

function generateUniqueName(playerId, typeStr) {
    const poolKey = `${playerId}_${typeStr}`;
    const assignedId = getRecycledId(poolKey);
    const itemName = CONFIG.TARGET_ITEM.split(":")[1] || "item";
    const fullName = `${itemName}_${typeStr}-${assignedId}`;
    return { poolKey, assignedId, fullName };
}

function playAnim(player, animName, force = false) {
    let finalAnim = animName; 
    if (!finalAnim || finalAnim.includes("????")) finalAnim = CONFIG.ANIMATIONS.idle; 
    if (!finalAnim || finalAnim.includes("????")) return; 
    
    const currentState = playerStates.get(player.id); 
    if (currentState !== finalAnim || force) { 
        try { player.playAnimation(finalAnim); } catch(e){}
        playerStates.set(player.id, finalAnim); 
        
        const tags = player.getTags();
        const wpPrefix = `wp_`;
        for (const tag of tags) if (tag.startsWith(wpPrefix)) { try { player.removeTag(tag); } catch(e){} }
        
        const parts = finalAnim.split(".");
        const stateName = parts[parts.length - 1]; 
        if (stateName && stateName !== "empty") { try { player.addTag(wpPrefix + stateName); } catch(e){} }
    }
}

function applyImpact(player, entity, skillCfg, trackingData) {
    try {
        const areaSettings = skillCfg.area_settings;
        const damageBonus = skillCfg.damage_bonus;
        
        const specEff = skillCfg.effects_special || {};
        const buffEff = skillCfg.effects_buffs || {};
        const debuffEff = skillCfg.effects_debuffs || {};
        
        const viewDir = entity.getViewDirection(); 
        const entityLoc = entity.location; 
        let rawCandidates = []; 
        let finalDamage = damageBonus;

        if (player && CONFIG.RPG_MECHANICS.critical_system.enabled) { 
            if (Math.random() < CONFIG.RPG_MECHANICS.critical_system.crit_chance) { 
                finalDamage *= CONFIG.RPG_MECHANICS.critical_system.crit_multiplier; 
                player.sendMessage("§l§c⚡ CRITICAL HIT! ⚡"); 
            }
        }

        if (areaSettings.use_around_radius) { 
            rawCandidates = entity.dimension.getEntities({ location: entityLoc, maxDistance: areaSettings.around_radius }); 
        } else { 
            const range = areaSettings.front_range; 
            const centerLoc = { x: entityLoc.x + (viewDir.x * (range.forward / 2)), y: entityLoc.y + (range.height / 4), z: entityLoc.z + (viewDir.z * (range.forward / 2)) };
            const maxRadius = Math.max(range.forward, range.width, range.height); 
            const initialList = entity.dimension.getEntities({ location: centerLoc, maxDistance: maxRadius }); 
            
            for (const target of initialList) { 
                const diffX = target.location.x - entityLoc.x, diffY = target.location.y - entityLoc.y, diffZ = target.location.z - entityLoc.z; 
                const dotForward = (diffX * viewDir.x) + (diffZ * viewDir.z); 
                const sideX = -viewDir.z, sideZ = viewDir.x; 
                const dotSide = Math.abs((diffX * sideX) + (diffZ * sideZ)); 

                if (dotForward >= 0 && dotForward <= range.forward && dotSide <= (range.width / 2) && Math.abs(diffY) <= (range.height / 2)) {
                    rawCandidates.push(target); 
                }
            }
        }

        let currentTick = system.currentTick, hitSuccess = false;
        let doVacuum = false, doKnockback = false, doFire = false, doSound = false;

        if (specEff.vacuum?.enabled && (currentTick - (trackingData.lastVacuumTick || 0) >= specEff.vacuum.delay_ticks || trackingData.lastVacuumTick === 0)) doVacuum = true;
        if (specEff.knockback?.enabled && (currentTick - (trackingData.lastKnockbackTick || 0) >= specEff.knockback.delay_ticks || trackingData.lastKnockbackTick === 0)) doKnockback = true;
        if (specEff.fire?.enabled && (currentTick - (trackingData.lastFireTick || 0) >= specEff.fire.delay_ticks || trackingData.lastFireTick === 0)) doFire = true;
        if (specEff.sounds?.enabled && (currentTick - (trackingData.lastSoundTick || 0) >= specEff.sounds.delay_ticks || trackingData.lastSoundTick === 0)) doSound = true;

        const allyMap = player ? getAllies(player) : new Map();

        for (const target of rawCandidates) { 
            try {
                if (target.id === entity.id || target.hasTag(SYS_TAGS.GLOBAL_IGNORE)) continue;

                const isAlly = allyMap.has(target.id);
                const targetHealth = target.getComponent("minecraft:health");

                if (isAlly) {
                    if (specEff.heal?.enabled && specEff.heal.is_buff) safeHeal(target, specEff.heal.amount);
                    
                    for (const effectId of Object.keys(buffEff)) {
                        const effSettings = buffEff[effectId];
                        if (effSettings?.enabled && effSettings.is_buff) {
                            target.addEffect(effectId, effSettings.duration * 20, { amplifier: effSettings.amplifier || 0, showParticles: false });
                        }
                    }
                    for (const effectId of Object.keys(debuffEff)) {
                        const effSettings = debuffEff[effectId];
                        if (effSettings?.enabled && effSettings.is_buff) {
                            target.addEffect(effectId, effSettings.duration * 20, { amplifier: effSettings.amplifier || 0, showParticles: false });
                        }
                    }
                } 
                else {
                    if (!targetHealth) continue; 
                    
                    let willDie = targetHealth.currentValue <= finalDamage;
                    let dmgOpts = { cause: "entityAttack" };
                    if (player) dmgOpts.damagingEntity = player;
                    target.applyDamage(finalDamage, dmgOpts); 
                    hitSuccess = true;

                    if (player && skillCfg.movement.mode_grappling_hook) {
                        const pLoc = player.location;
                        const vDir = player.getViewDirection();
                        const pullLoc = { x: pLoc.x + (vDir.x * 1.5), y: pLoc.y, z: pLoc.z + (vDir.z * 1.5) };
                        try { target.teleport(pullLoc, { dimension: player.dimension }); } catch(e){}
                        trackingData.remainingTicks = 0; 
                    }

                    if (player && willDie && CONFIG.RPG_MECHANICS.on_kill_perks.enabled) {
                        const kp = CONFIG.RPG_MECHANICS.on_kill_perks;
                        if (kp.heal_amount > 0) safeHeal(player, kp.heal_amount);
                        if (kp.trigger_sound && !kp.trigger_sound.includes("???")) try { player.playSound(kp.trigger_sound); } catch(e){}
                        if (kp.self_buffs.enabled) player.addEffect(kp.self_buffs.effect, kp.self_buffs.duration_ticks, { amplifier: kp.self_buffs.amplifier, showParticles: false });
                    }

                    if (target.typeId === "minecraft:player") {
                        if (specEff.title?.enabled) target.onScreenDisplay.setTitle(specEff.title.text);
                        if (specEff.camera_shake?.enabled) try { target.runCommandAsync(`camerashake add @s ${specEff.camera_shake.intensity} ${specEff.camera_shake.duration_seconds} rotational`); } catch(e){}
                    }
                    
                    if (specEff.forced_animation?.enabled) {
                        try { target.playAnimation(specEff.forced_animation.start_anim); } catch(e){}
                        forcedEntityAnimations.set(target.id, {
                            entity: target, anim: specEff.forced_animation.start_anim, endAnim: specEff.forced_animation.end_anim,
                            phase: 1, expireTick: system.currentTick + specEff.forced_animation.duration_ticks, endDurationTicks: specEff.forced_animation.end_duration_ticks
                        });
                    }

                    if (player && CONFIG.RPG_MECHANICS.hit_counter.enabled) {
                        let currentHits = (playerHitCounts.get(player.id) || 0) + 1;
                        const hc = CONFIG.RPG_MECHANICS.hit_counter;
                        if (currentHits >= hc.required_hits) {
                            currentHits = 0; 
                            if (hc.reduce_cooldown_ticks > 0 && playerCooldownTimers.has(player.id)) {
                                let activeSkill = playerSelectedSkill.get(player.id) || (CONFIG.ENABLE_SPECIAL_ATTACK ? "special_attack" : "skill1");
                                let cds = playerCooldownTimers.get(player.id);
                                if(cds[activeSkill] && activeSkill !== "special_attack") cds[activeSkill] = Math.max(0, cds[activeSkill] - hc.reduce_cooldown_ticks);
                            }
                            if (hc.heal_amount > 0) safeHeal(player, hc.heal_amount);
                            if (hc.trigger_sound && !hc.trigger_sound.includes("???")) try { player.playSound(hc.trigger_sound); } catch(e){}
                            if (hc.self_buffs.enabled) player.addEffect(hc.self_buffs.effect, hc.self_buffs.duration_ticks, { amplifier: hc.self_buffs.amplifier, showParticles: false });
                            
                            if (hc.aoe_burst_damage > 0) {
                                const aoeTargets = player.dimension.getEntities({ location: player.location, maxDistance: hc.burst_radius });
                                for (const aTarget of aoeTargets) {
                                    if (!allyMap.has(aTarget.id) && !aTarget.hasTag(SYS_TAGS.GLOBAL_IGNORE)) {
                                        aTarget.applyDamage(hc.aoe_burst_damage, { damagingEntity: player, cause: "entityAttack" });
                                    }
                                }
                            }
                            if (hc.apply_debuff_to_target.enabled) target.addEffect(hc.apply_debuff_to_target.effect, hc.apply_debuff_to_target.duration_ticks, { amplifier: hc.apply_debuff_to_target.amplifier, showParticles: false });
                            if (hc.run_command.enabled && !hc.run_command.command.includes("???")) try { player.runCommandAsync(hc.run_command.command); } catch(e){}
                        }
                        playerHitCounts.set(player.id, currentHits);
                    }

                    if (player && CONFIG.RPG_MECHANICS.life_steal.enabled) safeHeal(player, finalDamage * CONFIG.RPG_MECHANICS.life_steal.heal_percent); 

                    if (doVacuum) {
                        const vecX = entityLoc.x - target.location.x, vecY = entityLoc.y - target.location.y, vecZ = entityLoc.z - target.location.z; 
                        const len = Math.sqrt(vecX * vecX + vecY * vecY + vecZ * vecZ); 
                        if (len > 0.3) target.applyImpulse({ x: (vecX / len) * specEff.vacuum.strength, y: (vecY / len) * (specEff.vacuum.strength * 0.2), z: (vecZ / len) * specEff.vacuum.strength }); 
                    }

                    if (doKnockback && !specEff.vacuum?.enabled) target.applyKnockback(viewDir.x, viewDir.z, specEff.knockback.strength * 1.5, specEff.knockback.strength * 0.4);

                    if (doFire && !specEff.fire.is_buff) target.setOnFire(specEff.fire.duration, true);
                    if (specEff.heal?.enabled && !specEff.heal.is_buff) safeHeal(target, specEff.heal.amount); 

                    for (const effectId of Object.keys(buffEff)) { 
                        const effSettings = buffEff[effectId]; 
                        if (effSettings?.enabled && !effSettings.is_buff) { 
                            target.addEffect(effectId, effSettings.duration * 20, { amplifier: effSettings.amplifier || 0, showParticles: false }); 
                        }
                    }
                    for (const effectId of Object.keys(debuffEff)) { 
                        const effSettings = debuffEff[effectId]; 
                        if (effSettings?.enabled && !effSettings.is_buff) { 
                            target.addEffect(effectId, effSettings.duration * 20, { amplifier: effSettings.amplifier || 0, showParticles: false }); 
                        }
                    }
                }
            } catch(e) {}
        }
        
        if (hitSuccess && player) {
            if (skillCfg.movement.respawn_on_hit && !trackingData.isRespawned) {
                if (!trackingData.hasTriggeredRespawn) {
                    trackingData.hasTriggeredRespawn = true;
                    let spawnerId = player.id + "_hitSpawn_" + system.currentTick + "_" + Math.floor(Math.random() * 10000);
                    activeHitSpawners.set(spawnerId, {
                        playerId: player.id, configKey: trackingData.skillKey,
                        isCombo: trackingData.isCombo, stepNumber: trackingData.stepNumber,
                        isSecondary: trackingData.isSecondary, targetsLeft: skillCfg.movement.respawn_count,
                        interval: skillCfg.movement.respawn_interval_ticks, nextTick: system.currentTick + Math.max(1, skillCfg.movement.respawn_interval_ticks),
                        expireTick: system.currentTick + trackingData.remainingTicks 
                    });
                }
            }

            if (skillCfg.movement.mode_chain_ricochet) {
                if (trackingData.bouncesLeft === undefined) trackingData.bouncesLeft = skillCfg.movement.ricochet_bounces;
                if (trackingData.bouncesLeft > 0) {
                    if (!trackingData.hitEntities) trackingData.hitEntities = new Set();
                    for (const t of rawCandidates) trackingData.hitEntities.add(t.id);
                    
                    let nDist = Infinity, nTarget = null;
                    for (const t of entity.dimension.getEntities({ location: entityLoc, maxDistance: skillCfg.movement.ricochet_radius })) {
                        const isAlly = (player.id === t.id) || allyMap.has(t.id);
                        if (t.hasTag(SYS_TAGS.GLOBAL_IGNORE) || isAlly || trackingData.hitEntities.has(t.id)) continue;
                        const d = (t.location.x-entityLoc.x)**2 + (t.location.y-entityLoc.y)**2 + (t.location.z-entityLoc.z)**2;
                        if (d < nDist) { nDist = d; nTarget = t; }
                    }
                    if (nTarget) {
                        trackingData.targetId = nTarget.id; 
                        trackingData.bouncesLeft--;
                    } else {
                        trackingData.bouncesLeft = 0;
                    }
                }
            }

            if (skillCfg.movement.destroy_on_hit) {
                if (!skillCfg.movement.mode_chain_ricochet || trackingData.bouncesLeft <= 0) trackingData.remainingTicks = 0;
            }
        }

        if (doVacuum && hitSuccess) trackingData.lastVacuumTick = currentTick;
        if (doKnockback && hitSuccess) trackingData.lastKnockbackTick = currentTick;
        if (doFire && hitSuccess) trackingData.lastFireTick = currentTick;
        if (doSound && hitSuccess) {
            trackingData.lastSoundTick = currentTick;
            const validSounds = specEff.sounds.list.filter(s => s && !s.includes("???"));
            if (validSounds.length > 0) try { entity.dimension.playSound(validSounds[Math.floor(Math.random() * validSounds.length)], entityLoc); } catch(e){}
        }

    } catch (e) {} 
}

function spawnMagicEntity(player, configKey, isCombo, stepNumber = 0, isFromQueue = false, isSecondary = false, isRespawned = false) {
    try {
        const baseCfg = isCombo ? CONFIG.ATTACK_ENTITIES[configKey] : CONFIG.SKILLS[configKey];
        if (!baseCfg) return;

        const sCfg = isSecondary ? baseCfg.secondary_entity : baseCfg;
        if (!sCfg || !sCfg.enabled) return;

        if (!isSecondary && !isRespawned && baseCfg.secondary_entity && baseCfg.secondary_entity.enabled) {
            let spawnId = player.id + "_secSpawn_" + system.currentTick + "_" + Math.floor(Math.random() * 10000);
            pendingSecondarySpawns.set(spawnId, {
                playerId: player.id, configKey: configKey, isCombo: isCombo,
                stepNumber: stepNumber, triggerTick: system.currentTick + baseCfg.secondary_entity.spawn_delay_ticks
            });
        }

        if (!isFromQueue && sCfg.movement.mode_toggle_hover_on_head) {
            const toggleKey = player.id + "_" + configKey + (isSecondary ? "_sec" : "");
            if (activeHoverEntities.has(toggleKey)) {
                const uidToRemove = activeHoverEntities.get(toggleKey);
                const mapToUse = isCombo ? activeComboEntities : activeSkillEntities;
                if (mapToUse.has(uidToRemove)) {
                    const d = mapToUse.get(uidToRemove);
                    try { if(d.entity && d.entity.isValid()) d.entity.remove(); } catch(e){}
                    freeRecycledId(d.poolKey, d.poolId);
                    mapToUse.delete(uidToRemove);
                }
                activeHoverEntities.delete(toggleKey);
                player.sendMessage(`§l§cปิดการใช้งานออร่าเรียบร้อยแล้ว`);
                return; 
            }
        }

        const playerLoc = player.location; 
        const headLoc = player.getHeadLocation(); 
        const viewDir = player.getViewDirection(); 
        const rotation = player.getRotation(); 
        
        let prefixStr = isCombo ? `attack_entity${stepNumber}` : `skill_entity${configKey.replace("skill", "")}`;
        if (isSecondary) prefixStr += "_sec";
        let mainTag = isCombo ? SYS_TAGS.SUMMONED : SYS_TAGS.SKILL;
        let TrackerMap = isCombo ? activeComboEntities : activeSkillEntities;

        let targetLocations = []; 
        const mv = sCfg.movement;
        const allyMap = getAllies(player);
        let candidates = [];

        if (mv.mode_summon_closest || mv.mode_walk_to_closest || mv.mode_instant_teleport_attack) {
            for (const t of player.dimension.getEntities({ location: playerLoc, maxDistance: mv.shared_search_radius })) { 
                if (t.hasTag(SYS_TAGS.GLOBAL_IGNORE) || allyMap.has(t.id) || t.id === player.id) continue;
                candidates.push(t);
            }
            candidates.sort((a, b) => { return ((a.location.x - playerLoc.x)**2 + (a.location.z - playerLoc.z)**2) - ((b.location.x - playerLoc.x)**2 + (b.location.z - playerLoc.z)**2); });
            candidates = candidates.slice(0, mv.max_targets); 
        }

        if (mv.mode_random_around) {
            if (!isFromQueue && mv.max_targets > 1) {
                let interval = Math.max(1, Math.floor(sCfg.duration_ticks / mv.max_targets));
                let spawnerId = player.id + "_randSpawn_" + system.currentTick + "_" + Math.floor(Math.random() * 10000);
                activeRandomSpawners.set(spawnerId, {
                    playerId: player.id, configKey: configKey, isCombo: isCombo,
                    stepNumber: stepNumber, targetsLeft: mv.max_targets, interval: interval,
                    nextTick: system.currentTick, isSecondary: isSecondary 
                });
                if (!isCombo && !isSecondary) {
                    let cds = playerCooldownTimers.get(player.id) || { skill1: 0, skill2: 0, skill3: 0 };
                    cds[configKey] = sCfg.cooldown_duration_ticks || 0;
                    playerCooldownTimers.set(player.id, cds);
                }
                return; 
            } else {
                const angle = Math.random() * Math.PI * 2;
                const r = Math.random() * mv.shared_search_radius;
                let targetLoc = { x: playerLoc.x + Math.cos(angle) * r, y: playerLoc.y, z: playerLoc.z + Math.sin(angle) * r };
                targetLocations.push({ loc: targetLoc, dir: viewDir, targetId: null });
            }
        } else if (candidates.length > 0) {
            for (const t of candidates) targetLocations.push({ loc: t.location, dir: viewDir, targetId: t.id });
        } else {
            let dist = mv.mode_follow_cursor_distance ? mv.follow_distance : 1.5;
            const normalLoc = { x: headLoc.x + (viewDir.x * dist), y: headLoc.y + (viewDir.y * dist) - 0.5, z: headLoc.z + (viewDir.z * dist) }; 
            targetLocations.push({ loc: normalLoc, dir: viewDir }); 
        }

        for (const spawnData of targetLocations) { 
            let actualSpawnLoc = { ...spawnData.loc };
            let isSpawningPhase = false;

            if (mv.spawn_style === "from_player" && !mv.mode_random_around && !mv.mode_summon_closest && !mv.mode_instant_teleport_attack) actualSpawnLoc = { x: headLoc.x, y: headLoc.y - 0.5, z: headLoc.z };
            else if (mv.spawn_style === "ground") actualSpawnLoc.y = spawnData.loc.y; 
            else if (mv.spawn_style === "burrow") { actualSpawnLoc.y = spawnData.loc.y - mv.spawn_y_offset; isSpawningPhase = true; } 
            else if (mv.spawn_style === "sky") { actualSpawnLoc.y = spawnData.loc.y + mv.spawn_y_offset; isSpawningPhase = true; }

            const entity = player.dimension.spawnEntity(sCfg.type, actualSpawnLoc); 
            
            const spawnInfo = generateUniqueName(player.id, prefixStr);
            const uid = spawnInfo.fullName;

            if (sCfg.show_name) entity.nameTag = uid;
            
            entity.addTag("uid:" + uid);
            entity.addTag(mainTag); 
            entity.addTag(SYS_TAGS.GLOBAL_IGNORE);
            entity.addTag("owner:" + player.id); 

            entity.addEffect("resistance", 999999, { amplifier: 255, showParticles: false }); 
            entity.addEffect("weakness", 999999, { amplifier: 255, showParticles: false }); 
            if (sCfg.invisible) entity.addEffect("invisibility", 999999, { amplifier: 0, showParticles: false });

            let initialFacing = { x: actualSpawnLoc.x + spawnData.dir.x, y: actualSpawnLoc.y + spawnData.dir.y, z: actualSpawnLoc.z + spawnData.dir.z };
            if (spawnData.targetId) {
                const trg = world.getEntity(spawnData.targetId);
                if (trg && trg.isValid()) initialFacing = trg.location;
            }
            entity.teleport(actualSpawnLoc, { dimension: player.dimension, facingLocation: initialFacing }); 

            TrackerMap.set(uid, {
                entity: entity, uid: uid, playerId: player.id, skillKey: configKey,
                isSecondary: isSecondary, isRespawned: isRespawned, isCombo: isCombo, stepNumber: stepNumber,
                remainingTicks: sCfg.duration_ticks, nextDamageTick: system.currentTick,  
                forwardDirection: { x: spawnData.dir.x, y: spawnData.dir.y, z: spawnData.dir.z }, 
                targetId: spawnData.targetId, spawnStyle: mv.spawn_style, targetLoc: { ...spawnData.loc },
                isSpawningPhase: isSpawningPhase, lastVacuumTick: 0, lastKnockbackTick: 0, lastFireTick: 0, lastSoundTick: 0,
                lastHeadLoc: headLoc, lastRotation: rotation, lastViewDir: viewDir,
                poolKey: spawnInfo.poolKey, poolId: spawnInfo.assignedId, elapsedTicks: 0, spawnLoc: { ...actualSpawnLoc }
            });

            if (mv.mode_toggle_hover_on_head && !isFromQueue) {
                activeHoverEntities.set(player.id + "_" + configKey + (isSecondary ? "_sec" : ""), uid);
                player.sendMessage(`§l§aเปิดออร่าเรียบร้อยแล้ว!`);
            }

            if (sCfg.summon_minions?.enabled) {
                const validTypes = sCfg.summon_minions.types.filter(t => t && !t.includes("???"));
                if (validTypes.length > 0) {
                    for (let j = 0; j < sCfg.summon_minions.amount; j++) {
                        const rType = validTypes[Math.floor(Math.random() * validTypes.length)];
                        const rRadius = Math.random() * sCfg.summon_minions.spawn_radius;
                        const rAngle = Math.random() * Math.PI * 2;
                        const minionLoc = { x: actualSpawnLoc.x + Math.cos(rAngle) * rRadius, y: actualSpawnLoc.y, z: actualSpawnLoc.z + Math.sin(rAngle) * rRadius };
                        try {
                            const minion = player.dimension.spawnEntity(rType, minionLoc);
                            let mPrefix = isCombo ? `summon_minions_attack_${stepNumber}` : `summon_minions_skill_${configKey.replace("skill", "")}`;
                            if (isSecondary) mPrefix += "_sec";
                            const minionInfo = generateUniqueName(player.id, mPrefix);
                            const mUid = minionInfo.fullName;

                            if (sCfg.summon_minions.show_name) minion.nameTag = mUid;
                            minion.addTag("uid:" + mUid); minion.addTag(SYS_TAGS.MINION); minion.addTag(SYS_TAGS.GLOBAL_IGNORE); minion.addTag("owner:" + player.id);
                            if (sCfg.summon_minions.auto_tame) { try { const tameComp = minion.getComponent("minecraft:tameable"); if (tameComp) tameComp.tame(player); } catch(e) {} }
                            activeMinionEntities.set(mUid, { entity: minion, uid: mUid, playerId: player.id, remainingTicks: sCfg.summon_minions.duration_ticks, poolKey: minionInfo.poolKey, poolId: minionInfo.assignedId });
                        } catch(e) {}
                    }
                }
            }
        }
        
        if (!isCombo && !isFromQueue && !isSecondary) {
            let cds = playerCooldownTimers.get(player.id) || { skill1: 0, skill2: 0, skill3: 0 };
            cds[configKey] = sCfg.cooldown_duration_ticks || 0;
            playerCooldownTimers.set(player.id, cds);
        }

    } catch(e) {}
}

function triggerAttack(player) {
    let actionTimer = playerActionTimers.get(player.id) ?? 0; 
    if (actionTimer > 0) return; 
    
    // ดึงข้อมูลคอมโบเดิม หรือสร้างใหม่ (แยกระหว่างอนิเมชัน กับ Entity)
    let comboInfo = playerCombos.get(player.id);
    if (!comboInfo || comboInfo.animStep === undefined) {
        comboInfo = { animStep: 0, entityStep: 0, lastTick: 0 };
    }
    
    // รีเซ็ตคอมโบถ้าทิ้งช่วงการตีเกิน 40 Ticks (2 วินาที)
    if (system.currentTick - comboInfo.lastTick > 40) {
        comboInfo.animStep = 0;
        comboInfo.entityStep = 0;
    }

    // ==========================================
    // 🎬 ส่วนที่ 1: ระบบอนิเมชัน (วนลูป 1 ➔ 2 ➔ 3 เสมอ)
    // ==========================================
    let currentDuration = (Array.isArray(CONFIG.ATTACK_DURATION_TICKS) && CONFIG.ATTACK_DURATION_TICKS.length > comboInfo.animStep) 
        ? CONFIG.ATTACK_DURATION_TICKS[comboInfo.animStep] 
        : 10;
    
    playAnim(player, CONFIG.ANIMATIONS.attacks[comboInfo.animStep], true); 
    playerActionTimers.set(player.id, currentDuration); 

    // ==========================================
    // ⚔️ ส่วนที่ 2: ระบบเสก Entity (ตามที่มีการเปิดใช้งาน)
    // ==========================================
    let availableAttacks = [];
    if (CONFIG.ATTACK_ENTITIES["attack1"] && CONFIG.ATTACK_ENTITIES["attack1"].enabled) availableAttacks.push(1);
    if (CONFIG.ATTACK_ENTITIES["attack2"] && CONFIG.ATTACK_ENTITIES["attack2"].enabled) availableAttacks.push(2);
    if (CONFIG.ATTACK_ENTITIES["attack3"] && CONFIG.ATTACK_ENTITIES["attack3"].enabled) availableAttacks.push(3);

    // เช็คว่ามี Entity ที่เปิดใช้งานอย่างน้อย 1 ตัว
    if (availableAttacks.length > 0) {
        // คำนวณหาลำดับที่จะใช้เสกตาม Array เช่น [1, 2, 3] หรือ [1, 2] หรือ [1]
        let spawnIndex = comboInfo.entityStep % availableAttacks.length;
        let attackNum = availableAttacks[spawnIndex];
        
        spawnMagicEntity(player, `attack${attackNum}`, true, attackNum); 
        comboInfo.entityStep++; // ขยับคอมโบเสก Entity เป็นรอบถัดไป
    }

    // ==========================================
    // 🔄 ส่วนที่ 3: อัปเดตข้อมูลและบันทึกเวลา
    // ==========================================
    // ขยับคอมโบอนิเมชันไปสเต็ปถัดไป
    comboInfo.animStep = (comboInfo.animStep + 1) % (CONFIG.ANIMATIONS.attacks.length || 3); 
    comboInfo.lastTick = system.currentTick; 
    
    playerCombos.set(player.id, comboInfo); 
}

// ===================================================================================================
// UI SYSTEM 
// ===================================================================================================
function showMainMenu(player) {
    const uiCfg = CONFIG.UI_SETTINGS;
    if (uiCfg.ally_system.enabled) getAllies(player);

    const form = new ActionFormData().title(uiCfg.main_menu.title).body(uiCfg.main_menu.body);
    let activeSkill = playerSelectedSkill.get(player.id) || (CONFIG.ENABLE_SPECIAL_ATTACK ? "special_attack" : "skill1");
    let cds = playerCooldownTimers.get(player.id) || { skill1: 0, skill2: 0, skill3: 0 };
    let menuMap = [];

    if (CONFIG.ENABLE_SPECIAL_ATTACK) {
        let spText = activeSkill === "special_attack" ? "§l§a[กำลังใช้งาน]" : "§l§a[พร้อมใช้งาน]";
        form.button(`${uiCfg.main_menu.btn_special_attack_text}\n§r${spText}`, uiCfg.main_menu.icon_special_attack);
        menuMap.push({ action: "special_attack" });
    }

    for (let i = 1; i <= 3; i++) {
        let skKey = `skill${i}`;
        let sk = CONFIG.SKILLS[skKey];
        if (!sk.enabled) continue;
        let cdTicks = cds[skKey], statusText = "";
        let isHoverMode = sk.movement.mode_toggle_hover_on_head;
        let isHoverActive = isHoverMode && activeHoverEntities.has(player.id + "_" + skKey);

        if (activeSkill === skKey) statusText = "§l§a[กำลังใช้งาน]";
        else if (isHoverActive) statusText = "§l§a[คลิกเก็บออร่า]";
        else if (cdTicks > 0) statusText = `§l§c[ติดคูลดาวน์ ${(cdTicks / 20).toFixed(1)} วิ]`;
        else statusText = "§l§a[พร้อมใช้งาน]";

        form.button(`${uiCfg.main_menu.btn_skill_prefix} ${i} ${sk.name} ]\n§r${statusText}`, uiCfg.main_menu.icon_skill);
        menuMap.push({ action: "skill", key: skKey, index: i });
    }

    if (CONFIG.WEAPON_SWAP.enabled && CONFIG.WEAPON_SWAP.target_weapon_id !== "") {
        form.button(`${uiCfg.main_menu.btn_weapon_swap_text}\n§r§bคลิกเพื่อสลับอาวุธ`, uiCfg.main_menu.icon_weapon_swap);
        menuMap.push({ action: "swap" });
    }

    form.button(`§lตั้งค่าระบบ\n§r§8จัดการระบบและพันธมิตร`, "textures/ui/book_addtextpage_pressed");
    menuMap.push({ action: "system_settings" });

    form.show(player).then(resp => {
        if (resp.canceled) return;
        let mapData = menuMap[resp.selection];
        
        if (mapData.action === "special_attack") {
            playerSelectedSkill.set(player.id, "special_attack");
            player.sendMessage(`§l§a[System] เปลี่ยนเป็นโหมด [โจมตีพิเศษ] แล้ว!`);
        } else if (mapData.action === "skill") {
            let skillKey = mapData.key;
            let sCfg = CONFIG.SKILLS[skillKey];
            let isHoverMode = sCfg.movement.mode_toggle_hover_on_head;
            let isHoverActive = isHoverMode && activeHoverEntities.has(player.id + "_" + skillKey);
            if (cds[skillKey] > 0 && !isHoverActive) return player.sendMessage(`§l§c[System] สกิลนี้ยังติดคูลดาวน์!`);
            playerSelectedSkill.set(player.id, skillKey);
            if (!isHoverMode) player.sendMessage(`§l§a[System] เลือกสกิลที่ ${mapData.index} เรียบร้อยแล้ว!`);
        } else if (mapData.action === "swap") {
            system.run(() => {
                try {
                    const equippable = player.getComponent("minecraft:equippable");
                    if (equippable) {
                        const newItem = new ItemStack(CONFIG.WEAPON_SWAP.target_weapon_id, 1);
                        equippable.setEquipment(EquipmentSlot.Mainhand, newItem);
                        player.sendMessage(`§l§a[System] ทำการสลับอาวุธเรียบร้อยแล้ว!`);
                        try { player.playAnimation(CONFIG.ANIMATIONS.empty); } catch(e){}
                    }
                } catch(e) { player.sendMessage(`§l§c[System] ไม่สามารถสลับอาวุธได้ (โปรดเช็คไอดีอาวุธ)`); }
            });
        } else if (mapData.action === "system_settings") {
            system.run(() => showSystemSettings(player));
        }
    });
}

function showSystemSettings(player) {
    const uiCfg = CONFIG.UI_SETTINGS;
    const form = new ActionFormData().title("§l⚙️ ตั้งค่าระบบ").body("§l§eโปรดเลือกหมวดหมู่การตั้งค่า:");
    let menuMap = [];

    if (uiCfg.ally_system.enabled) {
        form.button(`ตั้งค่าพันธมิตร\n§r§2จัดการรายชื่อเพื่อน`, uiCfg.main_menu.icon_ally_menu);
        menuMap.push("ally");
    }

    form.button(`ตั้งค่าระบบสกิล\n§r§8จัดการการทำงานของสกิล`, "textures/ui/refresh_light");
    menuMap.push("skill_sys");

    form.button(uiCfg.ally_system.btn_back, uiCfg.ally_system.icon_back);
    menuMap.push("back");

    form.show(player).then(resp => {
        if (resp.canceled) return;
        let sel = menuMap[resp.selection];
        if (sel === "ally") system.run(() => showAllyMenu(player));
        else if (sel === "skill_sys") system.run(() => showSkillSystemSettings(player));
        else if (sel === "back") system.run(() => showMainMenu(player));
    });
}

function showSkillSystemSettings(player) {
    const form = new ActionFormData().title("§l⚙️ ตั้งค่าระบบสกิล");
    let isSneakSwap = playerSneakPref.get(player.id) ?? true;
    let sneakText = isSneakSwap ? "§aเปิด" : "§cปิด";

    form.button(`กดย่อทันทีเพื่อสลับสกิลอัตโนมัติ\n§rสถานะ: ${sneakText}`, "textures/ui/refresh_light");
    form.button(`ล้างสกิลที่ค้างอยู่ในแมพ\n§r§cยกเลิกสกิลทั้งหมดของคุณ`, "textures/ui/cancel");
    form.button(CONFIG.UI_SETTINGS.ally_system.btn_back, CONFIG.UI_SETTINGS.ally_system.icon_back);

    form.show(player).then(resp => {
        if (resp.canceled) return;
        if (resp.selection === 0) {
            playerSneakPref.set(player.id, !isSneakSwap);
            player.sendMessage(`§l§e[System] ตั้งค่าสลับสกิลด้วยการย่อเป็น: ${!isSneakSwap ? "§aเปิด" : "§cปิด"}`);
            system.run(() => showSkillSystemSettings(player));
        } else if (resp.selection === 1) {
            clearPlayerSkills(player);
            player.sendMessage("§l§a[System] ทำการล้างสกิลที่ค้างอยู่ทั้งหมดเรียบร้อยแล้ว!");
            system.run(() => showSkillSystemSettings(player));
        } else if (resp.selection === 2) {
            system.run(() => showSystemSettings(player));
        }
    });
}

function showAllyMenu(player) {
    const uiAlly = CONFIG.UI_SETTINGS.ally_system;
    getAllies(player);
    const form = new ActionFormData()
        .title(uiAlly.menu_title)
        .body(uiAlly.menu_body)
        .button(`${uiAlly.btn_list_ally}\n§r§9ดูรายชื่อ/จัดการเพื่อน`, uiAlly.icon_list_ally)
        .button(`${uiAlly.btn_add_ally}\n§r§aสแกนผู้เล่นระยะ 10 บล็อก`, uiAlly.icon_add_ally)
        .button(`${uiAlly.btn_remove_ally}\n§r§cเตะคนออกจากกลุ่ม`, uiAlly.icon_remove_ally)
        .button(uiAlly.btn_back, uiAlly.icon_back);
        
    form.show(player).then(resp => {
        if (resp.canceled) return;
        if (resp.selection === 0) showAllyList(player);
        else if (resp.selection === 1) showAddAlly(player);
        else if (resp.selection === 2) showRemoveAlly(player);
        else if (resp.selection === 3) showSystemSettings(player);
    });
}

function showAllyList(player) {
    const uiAlly = CONFIG.UI_SETTINGS.ally_system;
    const myAllies = getAllies(player);
    const allyArray = Array.from(myAllies.entries());
    
    const form = new ActionFormData()
        .title(`§l§9📋 ${uiAlly.btn_list_ally}`)
        .body("§l§eคลิกที่ชื่อผู้เล่นเพื่อเปิดเมนูจัดการ:");
        
    form.button(uiAlly.btn_back, uiAlly.icon_back);
    
   for (const [id, name] of allyArray) {
        let displayName = cleanName(name);
        if (id === player.id) {
            form.button(`§l✓ ${displayName} (ตัวคุณเอง)`, "textures/ui/icon_steve");
        } else {
            form.button(`§l✓ ${displayName}`, "textures/ui/icon_steve");
        }
    }

    form.show(player).then(resp => {
        if (resp.canceled) return;
        if (resp.selection === 0) return showAllyMenu(player);
        
        const selectedIdx = resp.selection - 1;
        const [targetId, targetName] = allyArray[selectedIdx];
        
        showKickMenu(player, targetId, targetName, showAllyList);
    });
}

function showAddAlly(player) {
    const uiAlly = CONFIG.UI_SETTINGS.ally_system;
    const myAllies = getAllies(player);
    const candidates = player.dimension.getPlayers({ location: player.location, maxDistance: 10 })
        .filter(p => !myAllies.has(p.id));
        
    const form = new ActionFormData()
        .title(`§l§a➕ ${uiAlly.btn_add_ally}`);
        
    if (candidates.length === 0) {
        form.body("§l§cไม่พบผู้เล่นอื่นในระยะ 10 บล็อก\n§e(หรือผู้เล่นทุกคนรอบตัวเป็นพันธมิตรอยู่แล้ว)");
        form.button(uiAlly.btn_back, uiAlly.icon_back);
        form.show(player).then(() => showAllyMenu(player));
        return;
    }
    
    form.body(`§l§eพบผู้เล่นใกล้เคียง ${candidates.length} คน\nคลิกที่ชื่อเพื่อเพิ่มเข้าสู่กลุ่มพันธมิตร:`);
    form.button(uiAlly.btn_back, uiAlly.icon_back);
    
    candidates.forEach(p => {
        form.button(`§l➕ เพิ่ม ${p.name}`, uiAlly.icon_add_ally);
    });

    form.show(player).then(resp => {
        if (resp.canceled || resp.selection === 0) return showAllyMenu(player);
        const targetPlayer = candidates[resp.selection - 1];
        addAllyTag(player, targetPlayer.id, targetPlayer.name);
        player.sendMessage(`§l§a[System] เพิ่ม ${targetPlayer.name} เป็นพันธมิตรเรียบร้อยแล้ว!`);
        showAddAlly(player); 
    });
}

function showRemoveAlly(player) {
    const uiAlly = CONFIG.UI_SETTINGS.ally_system;
    const myAllies = getAllies(player);
    const allyArray = Array.from(myAllies.entries());
    
    const form = new ActionFormData().title(`§l§c❌ ${uiAlly.btn_remove_ally}`);
        
    if (allyArray.length === 0) {
        form.body("§l§cคุณไม่มีรายชื่อพันธมิตรให้ลบเลย");
        form.button(uiAlly.btn_back, uiAlly.icon_back);
        form.show(player).then(() => showAllyMenu(player));
        return;
    }

    form.body("§l§eคลิกที่ชื่อผู้เล่นเพื่อเตะออกจากกลุ่มพันธมิตร:");
    form.button(uiAlly.btn_back, uiAlly.icon_back);
    
    allyArray.forEach(([id, name]) => {
        form.button(`§l§c❌ เตะ ${name}`, uiAlly.icon_remove_ally);
    });

    form.show(player).then(resp => {
        if (resp.canceled || resp.selection === 0) return showAllyMenu(player);
        const [targetId, targetName] = allyArray[resp.selection - 1];
        showKickMenu(player, targetId, targetName, showRemoveAlly);
    });
}

function showKickMenu(player, targetId, targetName, backFunc) {
    const uiAlly = CONFIG.UI_SETTINGS.ally_system;
    const form = new ActionFormData()
        .title("§l§cจัดการพันธมิตร")
        .body(`§l§eคุณต้องการเตะ §c${targetName} §eออกจากกลุ่มพันธมิตรหรือไม่?\n§7(เมื่อเตะออกแล้ว เขาจะได้รับดาเมจจากสกิลของคุณตามปกติ)`)
        .button("§l§cเตะออก (Kick)", uiAlly.icon_remove_ally)
        .button(uiAlly.btn_back, uiAlly.icon_back);
        
    form.show(player).then(resp => {
        if (resp.canceled || resp.selection === 1) return backFunc(player);
        if (resp.selection === 0) {
            removeAllyTag(player, targetId, targetName);
            player.sendMessage(`§l§c[System] เตะ ${targetName} ออกจากพันธมิตรแล้ว!`);
            backFunc(player);
        }
    });
}

// ===================================================================================================
// MINECRAFT WORLD EVENTS
// ===================================================================================================

world.afterEvents.itemUse.subscribe((event) => {
    const { source: player } = event; 
    const mainhandItem = player.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand);

    if (player?.typeId === "minecraft:player" && mainhandItem?.typeId === CONFIG.TARGET_ITEM) { 
        if (CONFIG.UI_SETTINGS.ally_system.enabled) getAllies(player); 

        if (player.isSneaking) {
            system.run(() => showMainMenu(player));
        } else {
            let activeSkill = playerSelectedSkill.get(player.id) || (CONFIG.ENABLE_SPECIAL_ATTACK ? "special_attack" : "skill1");
            
            if (activeSkill === "special_attack") {
                if (CONFIG.ENABLE_SPECIAL_ATTACK) { triggerAttack(player); playerClicking.set(player.id, system.currentTick); }
                return;
            }

            let sCfg = CONFIG.SKILLS[activeSkill];
            if (!sCfg || !sCfg.enabled) return; 

            let isHoverActive = sCfg.movement.mode_toggle_hover_on_head && activeHoverEntities.has(player.id + "_" + activeSkill);
            let cds = playerCooldownTimers.get(player.id) || { skill1: 0, skill2: 0, skill3: 0 };
            
            if (cds[activeSkill] > 0 && !isHoverActive) return; 
            if (playerCastingData.has(player.id) && !isHoverActive) return; 

            let currentSkillAnim = CONFIG.ANIMATIONS[`use_${activeSkill}`] || CONFIG.ANIMATIONS.idle;
            let currentTimeout = 15;
            if (activeSkill === "skill1") currentTimeout = CONFIG.USE_ITEM_1_TIMEOUT_TICKS;
            else if (activeSkill === "skill2") currentTimeout = CONFIG.USE_ITEM_2_TIMEOUT_TICKS;
            else if (activeSkill === "skill3") currentTimeout = CONFIG.USE_ITEM_3_TIMEOUT_TICKS;

            playAnim(player, currentSkillAnim, true); 
            playerActionTimers.set(player.id, currentTimeout); 
            
            playerCastingData.set(player.id, { 
                ticks: sCfg.cast_duration_ticks, 
                key: activeSkill, 
                lockLoc: { x: player.location.x, y: player.location.y, z: player.location.z } 
            }); 
        }
    }
});

world.afterEvents.entityHitEntity.subscribe((event) => {
    const damager = event.damagingEntity; 
    const target = event.hitEntity;

    if (damager && target && damager.hasTag(SYS_TAGS.MINION)) {
        let ownerId = null;
        for (const t of damager.getTags()) {
            if (t.startsWith("owner:")) { ownerId = t.split(":")[1]; break; }
        }
        if (ownerId) {
            const ownerEntity = world.getEntity(ownerId);
            const allyMap = ownerEntity ? getAllies(ownerEntity) : (globalPlayerAllies.get(ownerId) || new Map());
            if (target.id === ownerId || allyMap.has(target.id) || target.hasTag("owner:" + ownerId)) { safeHeal(target, 10); return; }
        }
    }

    const player = damager;
    if (player?.typeId !== "minecraft:player") return; 
    if (player.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId === CONFIG.TARGET_ITEM) {
        if (CONFIG.UI_SETTINGS.ally_system.enabled) getAllies(player);
        triggerAttack(player); playerClicking.set(player.id, system.currentTick); 
    }
});

world.beforeEvents.playerInteractWithBlock.subscribe((event) => {
    if (event.player.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId === CONFIG.TARGET_ITEM) { 
        system.run(() => { triggerAttack(event.player); playerClicking.set(event.player.id, system.currentTick); });
    }
});

world.beforeEvents.playerInteractWithEntity.subscribe((event) => {
    if (event.target.hasTag(SYS_TAGS.GLOBAL_IGNORE)) return; 
    if (event.player.getComponent("minecraft:equippable")?.getEquipment(EquipmentSlot.Mainhand)?.typeId === CONFIG.TARGET_ITEM) { 
        system.run(() => { triggerAttack(event.player); playerClicking.set(event.player.id, system.currentTick); });
    }
});

world.afterEvents.playerLeave.subscribe((event) => {
    const playerId = event.playerId; 
    for (const [uid, data] of activeComboEntities.entries()) {
        if (data.playerId === playerId) {
            try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e){}
            freeRecycledId(data.poolKey, data.poolId); activeComboEntities.delete(uid);
        }
    }
    for (const [uid, data] of activeSkillEntities.entries()) {
        if (data.playerId === playerId) {
            try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e){}
            freeRecycledId(data.poolKey, data.poolId); activeSkillEntities.delete(uid);
        }
    }
    for (const [uid, data] of activeMinionEntities.entries()) {
        if (data.playerId === playerId) {
            try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e){}
            freeRecycledId(data.poolKey, data.poolId); activeMinionEntities.delete(uid);
        }
    }
    for (let i = 0; i < activeSkillBlocks.length; i++) if (activeSkillBlocks[i].ownerId === playerId) activeSkillBlocks[i].forceClear = true; 
    
    playerStates.delete(playerId); playerCombos.delete(playerId); playerActionTimers.delete(playerId); playerStateTimers.delete(playerId);
    playerClicking.delete(playerId); playerCastingData.delete(playerId); playerCooldownTimers.delete(playerId); playerHitCounts.delete(playerId); 
    playerPanicCooldowns.delete(playerId); playerDeathDefianceCooldowns.delete(playerId); playerSelectedSkill.delete(playerId); globalPlayerAllies.delete(playerId);
    playerSneakState.delete(playerId); playerSneakPref.delete(playerId);
    for (const [key, uid] of activeHoverEntities.entries()) if (key.startsWith(playerId)) activeHoverEntities.delete(key);
    for (const [key, data] of activeRandomSpawners.entries()) if (data.playerId === playerId) activeRandomSpawners.delete(key);
    for (const [key, data] of pendingSecondarySpawns.entries()) if (data.playerId === playerId) pendingSecondarySpawns.delete(key);
    for (const [key, data] of activeHitSpawners.entries()) if (data.playerId === playerId) activeHitSpawners.delete(key);
});

// ===================================================================================================
// MASTER TICK ENGINE LOOP
// ===================================================================================================
function updateMagicEntities(TrackerMap, isCombo) {
    for (const [uid, data] of TrackerMap.entries()) {
        data.remainingTicks--;
        const baseCfg = isCombo ? CONFIG.ATTACK_ENTITIES[data.skillKey] : CONFIG.SKILLS[data.skillKey];
        const mySkillCfg = baseCfg ? (data.isSecondary ? baseCfg.secondary_entity : baseCfg) : null;

        if (data.remainingTicks <= 0) {
            if (data.entity && data.entity.isValid()) {
                const player = world.getEntity(data.playerId);
                if (player && player.isValid() && mySkillCfg) {
                    const mv = mySkillCfg.movement;
                    const lastLoc = data.entity.location;
                    if (mv.player_teleport_dash) {
                        try { player.teleport(lastLoc, { dimension: data.entity.dimension }); } catch(e){}
                    } else if (mv.player_dash) {
                        const pLoc = player.location, dx = lastLoc.x - pLoc.x, dy = lastLoc.y - pLoc.y, dz = lastLoc.z - pLoc.z;
                        const dist = Math.sqrt(dx*dx + dy*dy + dz*dz) || 1;
                        const dashSpeed = mv.speed > 0 ? mv.speed : 2.0; 
                        try { player.applyImpulse({ x: (dx/dist) * dashSpeed, y: Math.min((dy/dist) * dashSpeed, 1.5), z: (dz/dist) * dashSpeed }); } catch(e){}
                    }
                }
            }
            try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e) {}
            freeRecycledId(data.poolKey, data.poolId); TrackerMap.delete(uid); continue;
        } 

        if (!data.entity || !data.entity.isValid() || !mySkillCfg) continue;

        data.elapsedTicks = (data.elapsedTicks || 0) + 1;
        const player = world.getEntity(data.playerId);
        if (player && player.isValid()) {
            data.lastViewDir = player.getViewDirection();
            data.lastHeadLoc = player.getHeadLocation();
            data.lastRotation = player.getRotation();
        }
        
        const mv = mySkillCfg.movement, speed = mv.speed * 0.5, currentLoc = data.entity.location, dim = data.entity.dimension;
        const allyMap = player ? getAllies(player) : new Map();
        let nextLoc = { ...currentLoc }, facingLoc = { x: currentLoc.x + data.forwardDirection.x, y: currentLoc.y + data.forwardDirection.y, z: currentLoc.z + data.forwardDirection.z };

        if (data.isSpawningPhase) {
            let vecY = data.targetLoc.y - currentLoc.y, vecX = data.targetLoc.x - currentLoc.x, vecZ = data.targetLoc.z - currentLoc.z;
            let len = Math.sqrt(vecX*vecX + vecY*vecY + vecZ*vecZ);
            if (len > mv.spawn_approach_speed) {
                nextLoc = { x: currentLoc.x + (vecX/len)*mv.spawn_approach_speed, y: currentLoc.y + (vecY/len)*mv.spawn_approach_speed, z: currentLoc.z + (vecZ/len)*mv.spawn_approach_speed };
                facingLoc = { x: currentLoc.x + vecX, y: currentLoc.y + vecY, z: currentLoc.z + vecZ };
            } else data.isSpawningPhase = false; 
        } 
        
        if (!data.isSpawningPhase) {
            if (mv.mode_instant_teleport_attack) {
                if (data.targetId) {
                    const targetEntity = world.getEntity(data.targetId);
                    if (targetEntity && targetEntity.isValid()) { nextLoc = targetEntity.location; facingLoc = { x: player.location.x, y: player.location.y + 1, z: player.location.z }; }
                }
            } else if (mv.mode_toggle_hover_on_head) {
                data.remainingTicks = 100; 
                if (player) {
                    const hY = player.location.y + 2.0 + mv.hover_height;
                    facingLoc = { x: player.location.x + data.lastViewDir.x, y: hY, z: player.location.z + data.lastViewDir.z };
                    nextLoc = { x: player.location.x, y: hY, z: player.location.z };
                }
            } else if (mv.mode_delayed_homing && data.elapsedTicks < mv.delay_ticks) {
                nextLoc = { x: data.spawnLoc.x, y: data.spawnLoc.y + Math.sin(data.elapsedTicks*0.2)*0.2, z: data.spawnLoc.z };
            } else {
                let isHoming = mv.mode_summon_closest || mv.mode_walk_to_closest || mv.mode_delayed_homing || (mv.mode_chain_ricochet && data.targetId);
                let targetEntity = data.targetId ? world.getEntity(data.targetId) : null;

                if (mv.mode_delayed_homing && data.elapsedTicks > mv.delay_ticks && !targetEntity) {
                    let nDist = Infinity;
                    for (const t of dim.getEntities({ location: currentLoc, maxDistance: mv.shared_search_radius })) {
                        if (t.id === data.playerId || t.hasTag(SYS_TAGS.GLOBAL_IGNORE) || allyMap.has(t.id)) continue;
                        const d = (t.location.x-currentLoc.x)**2 + (t.location.y-currentLoc.y)**2 + (t.location.z-currentLoc.z)**2;
                        if (d < nDist) { nDist = d; targetEntity = t; }
                    }
                    if (targetEntity) data.targetId = targetEntity.id;
                }

                if (isHoming && targetEntity && targetEntity.isValid()) {
                    const fLoc = { x: targetEntity.location.x, y: targetEntity.location.y + 1.0, z: targetEntity.location.z };
                    const vecX = fLoc.x - currentLoc.x, vecY = fLoc.y - currentLoc.y, vecZ = fLoc.z - currentLoc.z;
                    const len = Math.sqrt(vecX*vecX + vecY*vecY + vecZ*vecZ);
                    if (len > 0) data.forwardDirection = { x: vecX/len, y: vecY/len, z: vecZ/len };
                    facingLoc = fLoc;
                } else if (mv.mode_follow_cursor) {
                    data.forwardDirection = data.lastViewDir;
                    facingLoc = { x: currentLoc.x + data.forwardDirection.x, y: currentLoc.y + data.forwardDirection.y, z: currentLoc.z + data.forwardDirection.z };
                } else if (mv.mode_boomerang) {
                    const distSq = (currentLoc.x - data.spawnLoc.x)**2 + (currentLoc.y - data.spawnLoc.y)**2 + (currentLoc.z - data.spawnLoc.z)**2;
                    if (distSq > mv.boomerang_distance*mv.boomerang_distance || data.remainingTicks <= mySkillCfg.duration_ticks / 2) {
                        if (player && player.isValid()) {
                            const vX = player.location.x - currentLoc.x, vY = (player.location.y + 1.0) - currentLoc.y, vZ = player.location.z - currentLoc.z;
                            const l = Math.sqrt(vX*vX + vY*vY + vZ*vZ);
                            if (l > 0.5) data.forwardDirection = { x: vX/l, y: vY/l, z: vZ/l };
                        }
                    }
                } else if (mv.mode_orbital) {
                    if (player) {
                        const angle = data.elapsedTicks * speed * 0.2;
                        const tX = player.location.x + Math.cos(angle) * mv.orbital_radius;
                        const tZ = player.location.z + Math.sin(angle) * mv.orbital_radius;
                        facingLoc = { x: tX - Math.sin(angle), y: player.location.y + 1.0, z: tZ + Math.cos(angle) };
                        nextLoc = { x: tX, y: player.location.y + 1.0, z: tZ };
                        data.forwardDirection = { x: 0, y: 0, z: 0 };
                    }
                } else if (mv.mode_follow_cursor_distance) {
                    nextLoc = { x: data.lastHeadLoc.x + (data.lastViewDir.x * mv.follow_distance), y: data.lastHeadLoc.y + (data.lastViewDir.y * mv.follow_distance) - 0.5, z: data.lastHeadLoc.z + (data.lastViewDir.z * mv.follow_distance) };
                    data.forwardDirection = { x: 0, y: 0, z: 0 };
                }
                
                nextLoc.x += data.forwardDirection.x * speed; nextLoc.y += data.forwardDirection.y * speed; nextLoc.z += data.forwardDirection.z * speed;

                if (mv.mode_parabola) {
                    if (data.velocityY === undefined) data.velocityY = speed;
                    data.velocityY -= mv.gravity_pull; nextLoc.y = currentLoc.y + data.velocityY;
                }
                if (mv.mode_sine_wave) {
                    if (!data.baseLoc) data.baseLoc = { ...currentLoc };
                    data.baseLoc.x += data.forwardDirection.x * speed; data.baseLoc.y += data.forwardDirection.y * speed; data.baseLoc.z += data.forwardDirection.z * speed;
                    const rx = -data.forwardDirection.z, rz = data.forwardDirection.x;
                    const rLen = Math.sqrt(rx*rx + rz*rz) || 1;
                    const offset = Math.sin(data.elapsedTicks * mv.wave_frequency) * mv.wave_amplitude;
                    nextLoc.x = data.baseLoc.x + (rx/rLen) * offset; nextLoc.y = data.baseLoc.y; nextLoc.z = data.baseLoc.z + (rz/rLen) * offset;
                }
            }
        }

        try {
            data.entity.teleport(nextLoc, { dimension: dim, facingLocation: facingLoc });
            if (mySkillCfg.particle_trail?.enabled && data.elapsedTicks <= (mySkillCfg.particle_trail.active_duration_ticks || 9999)) {
                if (system.currentTick % (mySkillCfg.particle_trail.spawn_interval_ticks || 1) === 0) {
                    const pt = mySkillCfg.particle_trail, pId = pt.particle_id;
                    if (pId && !pId.includes("???")) {
                        const cx = currentLoc.x, cy = currentLoc.y + pt.y_offset, cz = currentLoc.z, r = pt.radius;
                        
                        let vars = undefined;
                        if (pt.scale !== undefined && pt.scale !== 1.0) {
                            vars = new MolangVariableMap();
                            vars.setFloat("variable.scale", pt.scale);
                            vars.setFloat("variable.size", pt.scale);
                        }
                        
                        for(let i=0; i<pt.amount; i++) {
                            let px = cx, py = cy, pz = cz;
                            if (pt.mode_trail) { px += (Math.random() - 0.5) * r; py += (Math.random() - 0.5) * r; pz += (Math.random() - 0.5) * r; try { dim.spawnParticle(pId, {x:px, y:py, z:pz}, vars); } catch(e){} }
                            if (pt.mode_spiral) { const angle = data.elapsedTicks * 0.5 + (i * Math.PI * 2 / pt.amount); px += Math.cos(angle) * r; pz += Math.sin(angle) * r; py += Math.sin(data.elapsedTicks * 0.1) * r; try { dim.spawnParticle(pId, {x:px, y:py, z:pz}, vars); } catch(e){} }
                            if (pt.mode_aura) { const angle = Math.random() * Math.PI * 2; px += Math.cos(angle) * r; pz += Math.sin(angle) * r; try { dim.spawnParticle(pId, {x:px, y:py, z:pz}, vars); } catch(e){} }
                            if (pt.mode_sphere) { const theta = Math.random() * Math.PI * 2; const phi = Math.acos((Math.random() * 2) - 1); px += r * Math.sin(phi) * Math.cos(theta); py += r * Math.sin(phi) * Math.sin(theta); pz += r * Math.cos(phi); try { dim.spawnParticle(pId, {x:px, y:py, z:pz}, vars); } catch(e){} }
                            if (pt.mode_random_burst) { px += (Math.random() - 0.5) * r * 2; py += (Math.random() - 0.5) * r * 2; pz += (Math.random() - 0.5) * r * 2; try { dim.spawnParticle(pId, {x:px, y:py, z:pz}, vars); } catch(e){} }
                        }
                    }
                }
            }

            if (mySkillCfg.block_trail?.enabled) {
                const validBlocks = mySkillCfg.block_trail.blocks.filter(b => b && !b.includes("????") && !b.includes("???"));
                if (validBlocks.length > 0) {
                    const cx = Math.floor(currentLoc.x), cy = Math.floor(currentLoc.y), cz = Math.floor(currentLoc.z);
                    const rx = mySkillCfg.block_trail.radius_xz, ry = mySkillCfg.block_trail.radius_y;
                    for (let dx = -rx; dx <= rx; dx++) {
                        for (let dy = -ry; dy <= ry; dy++) {
                            for (let dz = -rx; dz <= rx; dz++) {
                                let inShape = false;
                                if (rx === 0 && ry === 0) inShape = (dx === 0 && dy === 0 && dz === 0);
                                else if (rx === 0) inShape = (dx === 0 && dz === 0 && Math.abs(dy) <= ry);
                                else if (ry === 0) inShape = (dy === 0 && (dx * dx + dz * dz <= rx * rx + 0.5));
                                else inShape = ((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) + (dz * dz) / (rx * rx) <= 1.2);

                                if (inShape) {
                                    try {
                                        const targetY = cy + dy;
                                        if (targetY < -64 || targetY > 320) continue;
                                        const blockLoc = {x: cx + dx, y: targetY, z: cz + dz};
                                        let isDuplicate = false;
                                        for (let b = 0; b < activeSkillBlocks.length; b++) {
                                            let ab = activeSkillBlocks[b];
                                            if (ab.loc.x === blockLoc.x && ab.loc.y === blockLoc.y && ab.loc.z === blockLoc.z && ab.dim.id === dim.id) {
                                                ab.expireTick = system.currentTick + mySkillCfg.block_trail.duration_ticks;
                                                ab.typeId = validBlocks[Math.floor(Math.random() * validBlocks.length)];
                                                ab.forceClear = false; isDuplicate = true; break;
                                            }
                                        }
                                        if (!isDuplicate) {
                                            const block = dim.getBlock(blockLoc);
                                            if (block && block.isAir) { 
                                                const randBlock = validBlocks[Math.floor(Math.random() * validBlocks.length)];
                                                block.setType(randBlock);
                                                activeSkillBlocks.push({ loc: blockLoc, dim: dim, expireTick: system.currentTick + mySkillCfg.block_trail.duration_ticks, typeId: randBlock, ownerId: data.playerId, forceClear: false });
                                            }
                                        }
                                    } catch(e) {}
                                }
                            }
                        }
                    }
                }
            }
            if (system.currentTick >= data.nextDamageTick) { applyImpact(player, data.entity, mySkillCfg, data); data.nextDamageTick = system.currentTick + mySkillCfg.damage_interval_ticks; }
        } catch (e) {}
    }
}

function tickLoop() {
    system.run(tickLoop); 
    for (const [sId, sData] of activeHitSpawners.entries()) {
        if (system.currentTick >= sData.expireTick) { activeHitSpawners.delete(sId); continue; }
        if (system.currentTick >= sData.nextTick) {
            const p = world.getEntity(sData.playerId);
            if (p && p.isValid()) spawnMagicEntity(p, sData.configKey, sData.isCombo, sData.stepNumber, true, sData.isSecondary, true);
            sData.targetsLeft--;
            if (sData.targetsLeft <= 0) activeHitSpawners.delete(sId);
            else sData.nextTick = system.currentTick + Math.max(1, sData.interval);
        }
    }

    for (const [sId, sData] of pendingSecondarySpawns.entries()) {
        if (system.currentTick >= sData.triggerTick) {
            const p = world.getEntity(sData.playerId);
            if (p && p.isValid()) spawnMagicEntity(p, sData.configKey, sData.isCombo, sData.stepNumber, true, true);
            pendingSecondarySpawns.delete(sId);
        }
    }

    for (const [sId, sData] of activeRandomSpawners.entries()) {
        if (system.currentTick >= sData.nextTick) {
            const p = world.getEntity(sData.playerId);
            if (p && p.isValid()) spawnMagicEntity(p, sData.configKey, sData.isCombo, sData.stepNumber, true, sData.isSecondary);
            sData.targetsLeft--;
            if (sData.targetsLeft <= 0) activeRandomSpawners.delete(sId);
            else sData.nextTick = system.currentTick + sData.interval;
        }
    }

    for (const [targetId, data] of forcedEntityAnimations.entries()) {
        if (data.entity && data.entity.isValid()) {
            if (system.currentTick >= data.expireTick) {
                if (data.phase === 1) {
                    data.phase = 2; data.expireTick = system.currentTick + data.endDurationTicks;
                    try { data.entity.playAnimation(data.endAnim); } catch(e){}
                } else forcedEntityAnimations.delete(targetId);
            }
        } else forcedEntityAnimations.delete(targetId);
    }
    
    updateMagicEntities(activeComboEntities, true); updateMagicEntities(activeSkillEntities, false);

    for (const [uid, data] of activeMinionEntities.entries()) {
        data.remainingTicks--;
        if (data.remainingTicks <= 0) {
            try { if (data.entity && data.entity.isValid()) data.entity.remove(); } catch(e) {}
            freeRecycledId(data.poolKey, data.poolId); activeMinionEntities.delete(uid); continue;
        }
        if (!data.entity || !data.entity.isValid()) continue;
        try {
            const minion = data.entity, ownerId = data.playerId, ownerEntity = world.getEntity(ownerId);
            const allyMap = ownerEntity ? getAllies(ownerEntity) : (globalPlayerAllies.get(ownerId) || new Map());
            const minionLoc = minion.location;
            
            let currentTarget = null;
            try { currentTarget = minion.target; } catch(e) {}
            let isInvalidTarget = false;
            if (currentTarget) {
                if (currentTarget.id === ownerId || allyMap.has(currentTarget.id) || currentTarget.hasTag("owner:" + ownerId) || currentTarget.hasTag(SYS_TAGS.SUMMONED) || currentTarget.hasTag(SYS_TAGS.SKILL)) {
                    isInvalidTarget = true;
                }
            }
            if (system.currentTick % 10 === 0 || (!data.nearestEnemy || !data.nearestEnemy.isValid())) {
                let nearestValid = null, minD = Infinity;
                for (const c of minion.dimension.getEntities({ location: minionLoc, maxDistance: 24 })) {
                    if (c.id === minion.id || c.id === ownerId || allyMap.has(c.id) || c.hasTag("owner:" + ownerId)) continue;
                    if (c.hasTag(SYS_TAGS.SUMMONED) || c.hasTag(SYS_TAGS.SKILL)) continue;
                    const hc = c.getComponent("minecraft:health");
                    if (!hc || hc.currentValue <= 0) continue;
                    const d = (c.location.x - minionLoc.x)**2 + (c.location.y - minionLoc.y)**2 + (c.location.z - minionLoc.z)**2;
                    if (d < minD) { minD = d; nearestValid = c; }
                }
                data.nearestEnemy = nearestValid;
            }
            if (isInvalidTarget) {
                try { minion.target = undefined; } catch(e) {} 
                if (data.nearestEnemy && data.nearestEnemy.isValid()) {
                    try { minion.target = data.nearestEnemy; } catch(e) {}
                    if (system.currentTick % 10 === 0) try { minion.applyDamage(0, { cause: 'entityAttack', damagingEntity: data.nearestEnemy }); } catch(e) {}
                    try { minion.removeEffect("slowness"); minion.removeEffect("weakness"); } catch(e) {}
                } else {
                    minion.addEffect("slowness", 5, { amplifier: 255, showParticles: false }); minion.addEffect("weakness", 5, { amplifier: 255, showParticles: false }); 
                    try { minion.clearVelocity(); } catch(e) {} 
                }
            } else if (!currentTarget && data.nearestEnemy && data.nearestEnemy.isValid()) {
                try { minion.target = data.nearestEnemy; } catch(e) {}
            }
        } catch(e) {}
    }

    for (let i = activeSkillBlocks.length - 1; i >= 0; i--) {
        const bData = activeSkillBlocks[i];
        if (system.currentTick >= bData.expireTick || bData.forceClear) {
            let isLoaded = false;
            try {
                const block = bData.dim.getBlock(bData.loc); isLoaded = true; 
                if (block && block.typeId === bData.typeId) block.setType("minecraft:air");
            } catch (e) {}
            if (isLoaded) activeSkillBlocks.splice(i, 1);
        }
    }

    if (system.currentTick % 100 === 0) {
        const cleanupTags = [SYS_TAGS.SKILL, SYS_TAGS.SUMMONED, SYS_TAGS.MINION];
        for (const dimName of ["overworld", "nether", "the_end"]) { 
            try {
                const dim = world.getDimension(dimName); 
                for (const tag of cleanupTags) {
                    for (const e of dim.getEntities({ tags: [tag] })) { 
                        let isTracked = false;
                        for (const t of e.getTags()) {
                            if (t.startsWith("uid:")) {
                                const uidString = t.substring(4);
                                if (activeSkillEntities.has(uidString) || activeComboEntities.has(uidString) || activeMinionEntities.has(uidString)) isTracked = true;
                            }
                        }
                        if (!isTracked) { try { e.remove(); } catch(err) {} }
                    }
                }
            } catch(e) {}
        }
    }

    for (const player of world.getAllPlayers()) {
        const playerId = player.id;
        const equippable = player.getComponent("minecraft:equippable"); 
        if (!equippable) continue; 
        
        if (!playerCooldownTimers.has(playerId)) playerCooldownTimers.set(playerId, { skill1: 0, skill2: 0, skill3: 0 });
        let cds = playerCooldownTimers.get(playerId);
        if (cds.skill1 > 0) cds.skill1--; if (cds.skill2 > 0) cds.skill2--; if (cds.skill3 > 0) cds.skill3--;

        const activeSkill = playerSelectedSkill.get(playerId) || (CONFIG.ENABLE_SPECIAL_ATTACK ? "special_attack" : "skill1");
        const sCfg = CONFIG.SKILLS[activeSkill];
        const mainhandItem = equippable.getEquipment(EquipmentSlot.Mainhand); 
        const isMainhand = mainhandItem?.typeId === CONFIG.TARGET_ITEM;
        const isHoldingWeapon = isMainhand || equippable.getEquipment(EquipmentSlot.Offhand)?.typeId === CONFIG.TARGET_ITEM || equippable.getEquipment(EquipmentSlot.Head)?.typeId === CONFIG.TARGET_ITEM || equippable.getEquipment(EquipmentSlot.Chest)?.typeId === CONFIG.TARGET_ITEM || equippable.getEquipment(EquipmentSlot.Legs)?.typeId === CONFIG.TARGET_ITEM || equippable.getEquipment(EquipmentSlot.Feet)?.typeId === CONFIG.TARGET_ITEM;
        
        // --- SNEAK SWAP LOGIC ---
        const isCurrentlySneaking = player.isSneaking;
        const wasSneaking = playerSneakState.get(playerId) || false;

        if (isCurrentlySneaking && !wasSneaking) {
            if (isHoldingWeapon) {
                const sneakSwapEnabled = playerSneakPref.get(playerId) ?? true;
                if (sneakSwapEnabled) {
                    cycleNextSkill(player);
                }
            }
        }
        playerSneakState.set(playerId, isCurrentlySneaking);
        // ------------------------

        if (isMainhand) {
            if (activeSkill === "special_attack" && CONFIG.ENABLE_SPECIAL_ATTACK) player.onScreenDisplay.setActionBar("§l§a[โจมตีพิเศษ] พร้อมใช้งาน!");
            else if (sCfg && sCfg.enabled) {
                let isHoverActive = sCfg.movement.mode_toggle_hover_on_head && activeHoverEntities.has(playerId + "_" + activeSkill);
                if (cds[activeSkill] > 0 && !isHoverActive) player.onScreenDisplay.setActionBar(sCfg.messages.cooldown.replace("{time}", (cds[activeSkill] / 20).toFixed(1))); 
                else if (isHoverActive) player.onScreenDisplay.setActionBar("§l§a[คลิกเพื่อเก็บออร่า]");
                else player.onScreenDisplay.setActionBar(sCfg.messages.ready); 
            }
        }

        if (playerCastingData.has(playerId)) {
            let castData = playerCastingData.get(playerId); 
            let castCfg = CONFIG.SKILLS[castData.key];
            if (castData.ticks > 0) { 
                castData.ticks--; 
                player.onScreenDisplay.setActionBar(castCfg.messages.casting.replace("{time}", (castData.ticks / 20).toFixed(1))); 
                
                if (castData.lockLoc) {
                    try { player.teleport(castData.lockLoc, { dimension: player.dimension }); } catch(e) {}
                }

                playerCastingData.set(playerId, castData);
                if (!isMainhand) playerCastingData.delete(playerId); 
                continue; 
            } else { 
                playerCastingData.delete(playerId); 
                spawnMagicEntity(player, castData.key, false); 
            }
        }

        if (!isHoldingWeapon) { 
            const tags = player.getTags();
            const wpPrefix = `wp_`;
            for (const tag of tags) if (tag.startsWith(wpPrefix)) { try { player.removeTag(tag); } catch(e){} }
            
            if (playerStates.has(playerId)) { 
                try { player.playAnimation(CONFIG.ANIMATIONS.empty); } catch(e){}
                playerHitCounts.delete(playerId);
                playerStates.delete(playerId); playerActionTimers.delete(playerId); 
                playerStateTimers.delete(playerId); playerClicking.delete(playerId); 
            }
            continue; 
        }

        if (CONFIG.RPG_MECHANICS.passive_buffs.enabled && system.currentTick % 20 === 0) {
            const pb = CONFIG.RPG_MECHANICS.passive_buffs, pOpts = { showParticles: false };
            const numBuffs = [{ k: "speed", v: pb.speed }, { k: "slowness", v: pb.slowness }, { k: "haste", v: pb.haste }, { k: "mining_fatigue", v: pb.mining_fatigue }, { k: "strength", v: pb.strength }, { k: "jump_boost", v: pb.jump_boost }, { k: "nausea", v: pb.nausea }, { k: "regeneration", v: pb.regeneration }, { k: "resistance", v: pb.resistance }, { k: "hunger", v: pb.hunger }, { k: "weakness", v: pb.weakness }, { k: "poison", v: pb.poison }, { k: "wither", v: pb.health_boost }, { k: "absorption", v: pb.absorption }, { k: "saturation", v: pb.saturation }, { k: "levitation", v: pb.levitation }, { k: "fatal_poison", v: pb.fatal_poison }, { k: "bad_omen", v: pb.bad_omen }, { k: "hero_of_the_village", v: pb.hero_of_the_village }];
            for (const b of numBuffs) if (b.v > 0) player.addEffect(b.k, 40, { amplifier: b.v - 1, ...pOpts });
            const boolBuffs = [{ k: "night_vision", v: pb.night_vision, dur: 300 }, { k: "fire_resistance", v: pb.fire_resistance, dur: 40 }, { k: "water_breathing", v: pb.water_breathing, dur: 40 }, { k: "invisibility", v: pb.invisibility, dur: 40 }, { k: "blindness", v: pb.blindness, dur: 40 }, { k: "darkness", v: pb.darkness, dur: 40 }, { k: "slow_falling", v: pb.slow_falling, dur: 40 }, { k: "conduit_power", v: pb.conduit_power, dur: 40 }, { k: "dolphins_grace", v: pb.dolphins_grace, dur: 40 }];
            for (const b of boolBuffs) if (b.v) player.addEffect(b.k, b.dur, { amplifier: 0, ...pOpts });
        }

        const tb = CONFIG.RPG_MECHANICS.time_based_passive;
        if (tb.enabled && system.currentTick % tb.interval_ticks === 0) {
            if (tb.clear_debuffs) DEBUFF_LIST.forEach(db => { try { player.removeEffect(db); } catch(e){} });
            if (tb.aoe_damage.enabled) {
                const allyMap = getAllies(player);
                const aoeTargets = player.dimension.getEntities({ location: player.location, maxDistance: tb.aoe_damage.radius });
                for (const aTarget of aoeTargets) if (aTarget.id !== playerId && !allyMap.has(aTarget.id) && !aTarget.hasTag(SYS_TAGS.GLOBAL_IGNORE)) aTarget.applyDamage(tb.aoe_damage.damage, { damagingEntity: player, cause: "entityAttack" });
            }
            if (tb.run_command.enabled && !tb.run_command.command.includes("???")) try { player.runCommandAsync(tb.run_command.command); } catch(e){}
        }

        if (CONFIG.RPG_MECHANICS.sneak_perks.enabled && player.isSneaking) {
            const sp = CONFIG.RPG_MECHANICS.sneak_perks;
            if (sp.invisibility_while_sneaking) player.addEffect("invisibility", 5, { amplifier: 0, showParticles: false });
        }

        if (CONFIG.RPG_MECHANICS.environment_adaptation.enabled && system.currentTick % 20 === 0) {
            const env = CONFIG.RPG_MECHANICS.environment_adaptation;
            if (env.in_water_buffs && player.isInWater) { player.addEffect("water_breathing", 40, { amplifier: 0, showParticles: false }); player.addEffect("dolphins_grace", 40, { amplifier: 1, showParticles: false }); }
            if (env.in_rain_buffs && player.isInWater && player.isOnGround) player.addEffect("speed", 40, { amplifier: 1, showParticles: false });
        }

        let lastClickTick = playerClicking.get(playerId) ?? 0, isClickingHeld = (system.currentTick - lastClickTick) <= 5, actionTimer = playerActionTimers.get(playerId) ?? 0; 
        if (actionTimer > 0) { playerActionTimers.set(playerId, actionTimer - 1); continue; } 

        const velocity = player.getVelocity();
        const horizontalSpeed = Math.sqrt(velocity.x ** 2 + velocity.z ** 2); 
        const isMoving = horizontalSpeed > 0.05; 
        const isSprinting = player.isSSprint; 
        const isJumping = velocity.y > 0.01 && !player.isOnGround; 
        const isFalling = velocity.y < -0.05 && !player.isOnGround; 
        const isValidAnim = (anim) => anim && anim !== "" && !anim.includes("????");

        let baseMoveAnim = CONFIG.ANIMATIONS.idle;
        let baseMoveDuration = CONFIG.IDLE_ANIMATION_LENGTH_TICKS;
        if (isMoving) {
            if (isSprinting && isValidAnim(CONFIG.ANIMATIONS.run)) { baseMoveAnim = CONFIG.ANIMATIONS.run; baseMoveDuration = CONFIG.RUN_DURATION_TICKS; } 
            else if (isValidAnim(CONFIG.ANIMATIONS.walk)) { baseMoveAnim = CONFIG.ANIMATIONS.walk; baseMoveDuration = CONFIG.WALK_DURATION_TICKS; } 
            else { baseMoveAnim = CONFIG.ANIMATIONS.idle; baseMoveDuration = CONFIG.IDLE_ANIMATION_LENGTH_TICKS; }
        }

        let targetAnim = null, targetDuration = 0; 
        if (player.getComponent("minecraft:riding")) { targetAnim = CONFIG.ANIMATIONS.sit; targetDuration = CONFIG.SIT_DURATION_TICKS; } 
        else if (player.isSneaking) { targetAnim = CONFIG.ANIMATIONS.sneak; targetDuration = CONFIG.SNEAK_DURATION_TICKS; } 
        else if (player.isInWater) { 
            if (isMoving || isJumping || isFalling) { targetAnim = CONFIG.ANIMATIONS.swimming; targetDuration = CONFIG.SWIMMING_DURATION_TICKS; } 
            else { targetAnim = CONFIG.ANIMATIONS.swim; targetDuration = CONFIG.SWIM_DURATION_TICKS; } 
        } 
        else if (!player.isOnGround) { 
            if (isJumping) { targetAnim = isValidAnim(CONFIG.ANIMATIONS.jump) ? CONFIG.ANIMATIONS.jump : baseMoveAnim; targetDuration = isValidAnim(CONFIG.ANIMATIONS.jump) ? CONFIG.JUMP_DURATION_TICKS : baseMoveDuration; } 
            else if (isFalling) { targetAnim = isValidAnim(CONFIG.ANIMATIONS.fall) ? CONFIG.ANIMATIONS.fall : baseMoveAnim; targetDuration = isValidAnim(CONFIG.ANIMATIONS.fall) ? CONFIG.FALL_DURATION_TICKS : baseMoveDuration; } 
            else if (isMoving) { targetAnim = isValidAnim(CONFIG.ANIMATIONS.flying) ? CONFIG.ANIMATIONS.flying : baseMoveAnim; targetDuration = isValidAnim(CONFIG.ANIMATIONS.flying) ? CONFIG.FLYING_DURATION_TICKS : baseMoveDuration; } 
            else { targetAnim = isValidAnim(CONFIG.ANIMATIONS.fly) ? CONFIG.ANIMATIONS.fly : baseMoveAnim; targetDuration = isValidAnim(CONFIG.ANIMATIONS.fly) ? CONFIG.FLY_DURATION_TICKS : baseMoveDuration; } 
        } 
        else { targetAnim = baseMoveAnim; targetDuration = baseMoveDuration; } 
        if (!isValidAnim(targetAnim)) { targetAnim = CONFIG.ANIMATIONS.idle; targetDuration = CONFIG.IDLE_ANIMATION_LENGTH_TICKS; }

        let stateTimer = playerStateTimers.get(playerId) ?? 0; 
        if (playerStates.get(playerId) !== targetAnim || (targetDuration > 0 && stateTimer <= 0)) { playAnim(player, targetAnim, true); playerStateTimers.set(playerId, targetDuration); } 
        else if (targetDuration > 0) { playerStateTimers.set(playerId, stateTimer - 1); }
    }
}
system.run(tickLoop);
"""

# ==================== CONFIG PARSER ====================
class ConfigParser:
    @staticmethod
    def read_config(js_path):
        try:
            with open(js_path, 'r', encoding='utf-8') as f: content = f.read()
            match = re.search(r'const\s+CONFIG\s*=\s*({[\s\S]*?});', content)
            if not match: return None
            config_str = match.group(1)
            config_str = re.sub(r'//.*?$', '', config_str, flags=re.MULTILINE)
            config_str = re.sub(r'([{,]\s*)([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:', r'\1"\2":', config_str)
            config_str = re.sub(r',\s*([}\]])', r'\1', config_str)
            return json.loads(config_str) if config_str else None
        except: return None
    
    @staticmethod
    def write_config(js_path, config):
        try:
            with open(js_path, 'r', encoding='utf-8') as f: content = f.read()
            config_str = "const CONFIG = " + json.dumps(config, ensure_ascii=False, separators=(',', ':')) + ";"
            new_content = re.sub(r'const\s+CONFIG\s*=\s*{[\s\S]*?};', lambda m: config_str, content, count=1)
            with open(js_path, 'w', encoding='utf-8') as f: f.write(new_content)
            return True
        except: return False

def format_key_label(key, prefix=""):
    eng_text = " ".join([word.capitalize() for word in key.split('_')])
    thai_text = TRANSLATIONS.get(key, key)
    return f"{prefix}{eng_text} \n{prefix}({thai_text})"

def get_identifier(item_path):
    try:
        with open(item_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('minecraft:item', {}).get('description', {}).get('identifier')
    except Exception: return None

# ==================== FILE MANIPULATIONS ====================
def update_manifest_dependencies(bp_path):
    manifest_path = os.path.join(bp_path, 'manifest.json')
    if not os.path.exists(manifest_path): return False, "ไม่พบ manifest.json"
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f: manifest = json.load(f)
        if 'dependencies' not in manifest: manifest['dependencies'] = []
        deps = {d.get('module_name'): d for d in manifest['dependencies']}
        if '@minecraft/server' not in deps: manifest['dependencies'].append({"module_name": "@minecraft/server", "version": "1.14.0"})
        if '@minecraft/server-ui' not in deps: manifest['dependencies'].append({"module_name": "@minecraft/server-ui", "version": "1.2.0"})
        with open(manifest_path, 'w', encoding='utf-8') as f: json.dump(manifest, f, indent="\t", ensure_ascii=False)
        return True, "Success"
    except Exception as e: return False, str(e)

def setup_main_script_and_manifest(bp_path, script_filenames):
    manifest_path = os.path.join(bp_path, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            
        if 'modules' not in manifest:
            manifest['modules'] = []
            
        manifest['modules'] = [m for m in manifest['modules'] if m.get('type') != 'script']
        manifest['modules'].append({
            "type": "script",
            "language": "javascript",
            "uuid": str(uuid.uuid4()),
            "entry": "scripts/main.js",
            "version": [1, 0, 0]
        })
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent="\t", ensure_ascii=False)

    scripts_dir = os.path.join(bp_path, 'scripts')
    os.makedirs(scripts_dir, exist_ok=True)
    main_js_path = os.path.join(scripts_dir, 'main.js')
    
    with open(main_js_path, 'w', encoding='utf-8') as f:
        f.write("// =========================================\n")
        f.write("// AUTO-GENERATED BY TDC MODEL SCRIPT SYSTEM\n")
        f.write("// =========================================\n\n")
        for script in script_filenames:
            f.write(f'import "./{script}";\n')

def create_bp_entity(bp_path, full_id):
    entities_dir = os.path.join(bp_path, 'entities')
    os.makedirs(entities_dir, exist_ok=True)
    filename = full_id.replace(":", "_") + ".json"
    entity_json = {
        "format_version": "1.12.0",
        "minecraft:entity": {
            "description": { "identifier": full_id, "is_spawnable": False, "is_summonable": True, "is_experimental": False },
            "components": {
                "minecraft:damage_sensor": { "triggers": [ { "deals_damage": False } ] },
                "minecraft:fire_immune": True,
                "minecraft:pushable": { "is_pushable": False },
                "minecraft:physics": { "has_collision": True, "has_gravity": True, "max_drop_speed": 0 },
                "minecraft:collision_box": { "width": 0.25, "height": 0.25 }
            },
            "events": { "despawn": { "add": { "component_groups": [ "despawn_group" ] } } },
            "component_groups": { "despawn_group": { "minecraft:instant_despawn": {} } }
        }
    }
    with open(os.path.join(entities_dir, filename), 'w', encoding='utf-8') as f: json.dump(entity_json, f, indent=4)

def create_dummy_entity(bp_path, dummy_id):
    entities_dir = os.path.join(bp_path, 'entities')
    os.makedirs(entities_dir, exist_ok=True)
    filename = dummy_id.replace(":", "_") + ".json"
    entity_json = {
        "format_version": "1.12.0",
        "minecraft:entity": {
            "description": { "identifier": dummy_id, "is_spawnable": False, "is_summonable": True, "is_experimental": False },
            "components": {
                "minecraft:damage_sensor": { "triggers": [ { "deals_damage": False } ] },
                "minecraft:fire_immune": True,
                "minecraft:pushable": { "is_pushable": False },
                "minecraft:physics": { "has_collision": False, "has_gravity": False, "max_drop_speed": 0 },
                "minecraft:collision_box": { "width": 0.25, "height": 0.25 }
            },
            "events": { "despawn": { "add": { "component_groups": [ "despawn_group" ] } } },
            "component_groups": { "despawn_group": { "minecraft:instant_despawn": {} } }
        }
    }
    with open(os.path.join(entities_dir, filename), 'w', encoding='utf-8') as f: json.dump(entity_json, f, indent=4)

def create_rp_entity(rp_path, full_id):
    entity_dir = os.path.join(rp_path, 'entity')
    models_dir = os.path.join(rp_path, 'models', 'entity')
    textures_dir = os.path.join(rp_path, 'textures', 'entity_tdcmodel')
    os.makedirs(entity_dir, exist_ok=True); os.makedirs(models_dir, exist_ok=True); os.makedirs(textures_dir, exist_ok=True)
    filename_base = full_id.replace(":", "_")
    texture_path = os.path.join(textures_dir, f"{filename_base}.png")
    if not os.path.exists(texture_path):
        pink_b64 = "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAKklEQVQokWNgYPjPgB8w0IEwzX/sajAZqgHjajSqwaiGAXQ1v0i2+M8AACgKEXH/b9qKAAAAAElFTkSuQmCC"
        with open(texture_path, "wb") as f: f.write(base64.b64decode(pink_b64))
            
    model_name = filename_base
    model_json = {
        "format_version": "1.12.0",
        "minecraft:geometry": [
            {
                "description": { "identifier": f"geometry.{model_name}", "texture_width": 16, "texture_height": 16, "visible_bounds_width": 2, "visible_bounds_height": 2, "visible_bounds_offset": [0, 0, 0] },
                "bones": [ { "name": "body", "pivot": [0, 2, 0], "cubes": [ { "origin": [-2, 0, -2], "size": [4, 4, 4], "uv": { "north": {"uv": [0, 0], "uv_size": [16, 16]}, "east": {"uv": [0, 0], "uv_size": [16, 16]}, "south": {"uv": [0, 0], "uv_size": [16, 16]}, "west": {"uv": [0, 0], "uv_size": [16, 16]}, "up": {"uv": [0, 0], "uv_size": [16, 16]}, "down": {"uv": [0, 0], "uv_size": [16, 16]} } } ] } ]
            }
        ]
    }
    with open(os.path.join(models_dir, f"{model_name}.geo.json"), 'w', encoding='utf-8') as f: json.dump(model_json, f, indent=4)
            
    client_entity = {
        "format_version": "1.10.0",
        "minecraft:client_entity": {
            "description": { "identifier": full_id, "materials": { "default": "entity_alphatest" }, "textures": { "default": f"textures/entity_tdcmodel/{filename_base}" }, "geometry": { "default": f"geometry.{model_name}" }, "render_controllers": [ "controller.render.default" ] }
        }
    }
    with open(os.path.join(entity_dir, f"{filename_base}.entity.json"), 'w', encoding='utf-8') as f: json.dump(client_entity, f, indent=4)

def generate_script(bp_path, identifier, entity_ids, dummy_id):
    scripts_dir = os.path.join(bp_path, 'scripts')
    os.makedirs(scripts_dir, exist_ok=True)
    
    current_config = copy.deepcopy(BASE_CONFIG)
    
    current_config["TARGET_ITEM"] = identifier
    current_config["WEAPON_SWAP"]["target_weapon_id"] = f"{identifier}_swap"
    current_config["DUMMY_TYPE"] = dummy_id
    
    for i in range(1, 4):
        atk_key = f"attack{i}"
        current_config["ATTACK_ENTITIES"][atk_key]["type"] = f"{identifier}_attack_cube_{i}"
        current_config["ATTACK_ENTITIES"][atk_key]["secondary_entity"]["type"] = f"{identifier}_attack_cube_{i}_sec"

    for i in range(1, 4):
        sk_key = f"skill{i}"
        current_config["SKILLS"][sk_key]["type"] = f"{identifier}_skill_cube_{i}"
        current_config["SKILLS"][sk_key]["secondary_entity"]["type"] = f"{identifier}_skill_cube_{i}_sec"

    config_json_str = json.dumps(current_config, separators=(',', ':'))
    content = JS_TEMPLATE.replace("__CONFIG_PLACEHOLDER__", config_json_str)
    
    filename = f"tdcmodel_{identifier.replace(':', '_')}.js"
    with open(os.path.join(scripts_dir, filename), 'w', encoding='utf-8') as f: f.write(content)
    return filename

