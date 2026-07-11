"""Physics generator class extracted verbatim from back_hair_v2.py.
Only the tkinter CLI wrappers were dropped; the class logic is unchanged.
"""
import json
import os
import re


class BackHairPhysicsGeneratorV2:
    def __init__(self):
        self.animation_data = None
        self.model_data = None
        self.attachable_data = None
        self.bone_groups = []
        self.animation_path = None
        self.model_path = None
        self.attachable_path = None
        
    def load_files(self, animation_path, model_path, attachable_path):
        """โหลดไฟล์ animation, model และ attachable"""
        self.animation_path = animation_path
        self.model_path = model_path
        self.attachable_path = attachable_path
        
        # โหลด Animation
        try:
            with open(animation_path, 'r', encoding='utf-8') as f:
                self.animation_data = json.load(f)
            print(f"✅ โหลดไฟล์ Animation สำเร็จ: {animation_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถโหลดไฟล์ Animation: {e}")
            return False
        
        # โหลด Model
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                self.model_data = json.load(f)
            print(f"✅ โหลดไฟล์ Model สำเร็จ: {model_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถโหลดไฟล์ Model: {e}")
            return False
        
        # โหลด Attachable
        try:
            with open(attachable_path, 'r', encoding='utf-8') as f:
                self.attachable_data = json.load(f)
            print(f"✅ โหลดไฟล์ Attachable สำเร็จ: {attachable_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถโหลดไฟล์ Attachable: {e}")
            return False
            
        return True
    
    def find_bones_with_prefix(self, prefix):
        """ค้นหา bone ทั้งหมดที่ขึ้นต้นด้วย prefix จากไฟล์ Model"""
        found_bones = []
        
        # อ่าน bones จาก model file
        geometries = self.model_data.get("minecraft:geometry", [])
        for geo in geometries:
            bones = geo.get("bones", [])
            for bone in bones:
                bone_name = bone.get("name", "")
                if bone_name.startswith(prefix):
                    if bone_name not in found_bones:
                        found_bones.append(bone_name)
        
        # เรียงตามหมายเลข
        def sort_key(bone_name):
            match = re.search(r'\d+$', bone_name)
            if match:
                return int(match.group())
            return 0
        
        found_bones.sort(key=sort_key)
        return found_bones
    
    def generate_wave_physics(self, bones, strength_multiplier=None):
        """
        สร้าง Wave Physics สำหรับผมหลัง
        - ใช้ v.hairYawPhysics
        - คลื่นตอนเดิน + กระโดด
        
        Auto-calculate strength based on bone count:
        - 1-5 bones: strength_factor = 1.2 (เพิ่มแรงเพราะผมสั้น)
        - 6-10 bones: strength_factor = 1.0 (ปกติ)
        - 11-15 bones: strength_factor = 0.8 (ลดแรงเพราะผมยาว)
        - 16+ bones: strength_factor = 0.6 (ลดแรงมากเพราะผมยาวมาก)
        """
        bone_count = len(bones)
        
        # คำนวณ strength factor ตามจำนวน bones
        if bone_count <= 5:
            auto_strength_factor = 1.2  # ผมสั้น ต้องเพิ่มแรง
        elif bone_count <= 10:
            auto_strength_factor = 1.0  # ผมปานกลาง
        elif bone_count <= 15:
            auto_strength_factor = 0.8  # ผมยาว
        else:
            auto_strength_factor = 0.6  # ผมยาวมาก
        
        # ใช้ค่าที่ผู้ใช้กำหนด หรือใช้ค่าอัตโนมัติ
        strength_factor = strength_multiplier if strength_multiplier is not None else auto_strength_factor
        
        print(f"   📊 Bones: {bone_count}, Strength Factor: {strength_factor:.1f} {'(auto)' if strength_multiplier is None else '(custom)'}")
        
        # ค่าเริ่มต้นสำหรับ wave (ปรับใหม่ให้สมจริง)
        base_wave_strength = 3.5 * strength_factor  # เริ่มที่ 3.5 แล้วเพิ่มขึ้นเรื่อยๆ
        wave_speed = 18  # ความเร็ว wave
        cape_clamp = 0.55 * strength_factor
        phase_offset = 0
        
        wave_bones = {}
        bone_count = len(bones)
        
        for i, bone_name in enumerate(bones):
            # Wave strength: ไล่จากโคน (น้อย) ไปปลาย (มาก)
            wave_strength = base_wave_strength + (i * 1.0 * strength_factor)
            
            # Yaw multiplier: ไล่จาก 0.12 -> 1.0
            if i == 0:
                yaw_mult = 0.12 * strength_factor
            else:
                # ไล่จาก 0.20 ขึ้นไปถึง 1.0
                yaw_mult = min(1.0, (0.20 + (i * 0.10)) * strength_factor)
            
            if i == 0:
                # bone แรก (โคน): ใช้ pitch + lerp และ move_speed
                wave_bones[bone_name] = {
                    "rotation": [
                        f"-v.headPitch + (-math.clamp(math.lerp(0, {-55 * strength_factor:.0f}, query.cape_flap_amount) - ({13 * strength_factor:.0f} * query.modified_move_speed), {-70 * strength_factor:.0f}, 0))",
                        0,
                        f"v.hairYawPhysics * {yaw_mult:.2f}"
                    ]
                }
            else:
                # bone ถัดไป: cosine wave
                wave_bones[bone_name] = {
                    "rotation": [
                        f"math.clamp(query.cape_flap_amount, 0, {cape_clamp:.2f}) * math.cos({phase_offset} - query.modified_distance_moved * {wave_speed}) * {wave_strength:.1f}",
                        0,
                        f"v.hairYawPhysics * {yaw_mult:.2f}"
                    ]
                }
                phase_offset += 12
        
        return wave_bones

    
    def generate_yaw_physics(self, bones, strength_multiplier=None):
        """
        สร้าง Yaw Physics สำหรับผมหลัง (Back)
        - อ่อนนุ่ม นิ่มนวล
        - ใช้ v.hairYawPhysics
        
        Auto-calculate strength based on bone count (same as wave_physics)
        """
        bone_count = len(bones)
        
        # คำนวณ strength factor ตามจำนวน bones
        if bone_count <= 5:
            auto_strength_factor = 1.2  # ผมสั้น ต้องเพิ่มแรง
        elif bone_count <= 10:
            auto_strength_factor = 1.0  # ผมปานกลาง
        elif bone_count <= 15:
            auto_strength_factor = 0.8  # ผมยาว
        else:
            auto_strength_factor = 0.6  # ผมยาวมาก
        
        # ใช้ค่าที่ผู้ใช้กำหนด หรือใช้ค่าอัตโนมัติ
        strength_factor = strength_multiplier if strength_multiplier is not None else auto_strength_factor
        
        yaw_bones = {}
        bone_count = len(bones)
        
        for i, bone_name in enumerate(bones):
            # ผมหลัง: ไล่จากโคน (น้อย) ไปปลาย (มาก) เหมือนผมจริง
            if i == 0:
                # โคนสุด
                multiplier = 0.20 * strength_factor
            elif i == bone_count - 1:
                # ปลายสุด
                multiplier = 1.0 * strength_factor
            else:
                # ส่วนกลาง: ไล่ขึ้นจาก 0.35 -> 0.98
                progress = i / max(1, bone_count - 1)
                multiplier = (0.20 + (progress * 0.80)) * strength_factor
            
            yaw_bones[bone_name] = {
                "rotation": [0, 0, f"v.hairYawPhysics * {multiplier:.2f}"]
            }
        
        return yaw_bones
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        all_anim_refs = []
        
        for group in self.bone_groups:
            prefix = group["prefix"]
            bones = group["bones"]
            strength_mult = group.get("strength_multiplier", None)  # ดึงค่า strength ถ้ามี
            
            # สร้าง Wave Physics
            wave_anim_name = f"animation.{prefix.lower()}.wave_physics"
            wave_bones = self.generate_wave_physics(bones, strength_mult)
            animations[wave_anim_name] = {
                "loop": True,
                "animation_length": 6,
                "bones": wave_bones
            }
            print(f"✅ สร้าง Wave Physics: {wave_anim_name} ({len(wave_bones)} bones)")
            
            # สร้าง Yaw Physics (Back)
            yaw_anim_name = f"animation.{prefix.lower()}.yaw_physics"
            animations[yaw_anim_name] = {
                "loop": True,
                "bones": self.generate_yaw_physics(bones, strength_mult)
            }
            print(f"✅ สร้าง Yaw Physics (ผมหลัง): {yaw_anim_name}")
            
            all_anim_refs.append({
                "prefix": prefix,
                "wave": wave_anim_name,
                "yaw": yaw_anim_name
            })
        
        return all_anim_refs
    
    def update_attachable_file(self, anim_refs):
        """อัพเดทไฟล์ attachable ด้วย scripts สำหรับผมหลัง"""
        if not self.attachable_data:
            print("ℹ️  ข้ามการแก้ไข attachable (ไม่มีไฟล์)")
            return
            
        desc = self.attachable_data["minecraft:attachable"]["description"]
        
        # === Scripts ===
        if "scripts" not in desc:
            desc["scripts"] = {}
        
        # Initialize scripts (เฉพาะที่ต้องใช้สำหรับผมหลัง)
        if "initialize" not in desc["scripts"]:
            desc["scripts"]["initialize"] = []
        
        init_scripts = [
            "v.hairYawPhysics = 0;",
            "v.hairYawVel = 0;",
            "v.prevHeadYaw = 0;",
            "v.headPitch = 0;",
            "v.pitchVel = 0;"
        ]
        
        for script in init_scripts:
            if script not in desc["scripts"]["initialize"]:
                desc["scripts"]["initialize"].append(script)
        
        # Pre-animation scripts (เฉพาะที่ต้องใช้สำหรับผมหลัง)
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        # ผมหลัง - ค่าใหม่ที่สมจริงกว่า (ปรับจาก purple_head)
        pre_anim_scripts = [
            # คำนวณ delta และ wrap around
            "v.headYawDelta = query.head_y_rotation(0) - v.prevHeadYaw;",
            "v.headYawDelta = v.headYawDelta > 180 ? v.headYawDelta - 360 : (v.headYawDelta < -180 ? v.headYawDelta + 360 : v.headYawDelta);",
            # Clamp input delta (±8 ให้ตอบสนองมากขึ้น)
            "v.headYawDelta = math.clamp(v.headYawDelta, -8.0, 8.0);",
            # Back Hair Physics - ค่าใหม่ที่สมจริง
            "v.hairYawVel = v.hairYawVel + (v.headYawDelta * 0.018);",  # sensitivity: 0.018
            "v.hairYawVel = v.hairYawVel - (v.hairYawPhysics * 0.015);", # stiffness: 0.015 (นุ่มนวลขึ้น)
            "v.hairYawVel = v.hairYawVel * 0.88;",                       # damping: 0.88 (พลิ้วนานขึ้น)
            "v.hairYawPhysics = v.hairYawPhysics + v.hairYawVel;",
            "v.hairYawPhysics = math.clamp(v.hairYawPhysics, -4, 4);",  # ±4 พลิ้วได้มากขึ้น
            "v.prevHeadYaw = query.head_y_rotation(0);",
            # Pitch Physics - ผมตกเมื่อก้ม/เงยหน้า (spring-damping)
            "v.pitchDelta = query.target_x_rotation - v.headPitch;",
            "v.pitchVel = v.pitchVel + (v.pitchDelta * 0.08);",  # sensitivity
            "v.pitchVel = v.pitchVel * 0.85;",                    # damping (smooth)
            "v.headPitch = v.headPitch + v.pitchVel;"
        ]
        
        # ลบ scripts เก่าที่เกี่ยวกับ hair physics ทั้งหมด (ลบแล้วใส่ใหม่ทั้งหมด)
        hair_physics_keywords = [
            "v.headYawDelta",
            "v.hairYawVel", 
            "v.hairYawPhysics",
            "v.prevHeadYaw",
            "v.headPitch",
            "v.pitchVel",
            "v.pitchDelta"
        ]
        
        # ลบ scripts เก่าที่เกี่ยวข้อง
        desc["scripts"]["pre_animation"] = [
            script for script in desc["scripts"]["pre_animation"]
            if not any(keyword in script for keyword in hair_physics_keywords)
        ]
        
        # เพิ่ม scripts ใหม่ทั้งหมด (ใส่ที่ต้นของ list เพื่อให้ทำงานก่อน)
        for script in reversed(pre_anim_scripts):
            desc["scripts"]["pre_animation"].insert(0, script)
        
        # === เรียงลำดับ pre_animation ให้ถูกต้อง ===
        def get_script_priority(script):
            s = script.strip()
            # กลุ่ม 1: คำนวณ delta (ต้องมาก่อน)
            if s.startswith("v.headYawDelta"):
                return 10
            # กลุ่ม 2: ใช้ delta คำนวณ velocity
            if s.startswith("v.hairYawVel") or s.startswith("v.frontHairVel"):
                return 20
            # กลุ่ม 3: ใช้ velocity คำนวณ position
            if s.startswith("v.hairYawPhysics") or s.startswith("v.frontHairYaw"):
                return 30
            # กลุ่ม 4: บันทึกค่าเดิม (ต้องมาท้าย)
            if s.startswith("v.prevHeadYaw"):
                return 90
            # กลุ่ม 5: head rotation variables
            if s.startswith("variable."):
                return 100
            return 50
        
        desc["scripts"]["pre_animation"].sort(key=get_script_priority)
        
        # Animate และ Animations
        if "animate" not in desc["scripts"]:
            desc["scripts"]["animate"] = []
        elif isinstance(desc["scripts"]["animate"], str):
            desc["scripts"]["animate"] = [desc["scripts"]["animate"]]
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        for ref in anim_refs:
            prefix = ref["prefix"]
            
            # Wave Physics
            wave_key = f"{prefix.lower()}_wave"
            desc["animations"][wave_key] = ref["wave"]
            if wave_key not in desc["scripts"]["animate"]:
                desc["scripts"]["animate"].append(wave_key)
            
            # Yaw Physics
            yaw_key = f"{prefix.lower()}_yaw"
            desc["animations"][yaw_key] = ref["yaw"]
            if yaw_key not in desc["scripts"]["animate"]:
                desc["scripts"]["animate"].append(yaw_key)
        
        print(f"✅ เพิ่ม scripts และ animations ใน attachable ({len(anim_refs)} groups)")
    
    def save_files(self):
        """บันทึกไฟล์"""
        # บันทึก animation
        try:
            with open(self.animation_path, 'w', encoding='utf-8') as f:
                json.dump(self.animation_data, f, indent=2, ensure_ascii=False)
            print(f"✅ บันทึกไฟล์ Animation: {self.animation_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกไฟล์ Animation: {e}")
            return False
        
        # บันทึก attachable
        try:
            # จัดเรียง description
            desc = self.attachable_data["minecraft:attachable"]["description"]
            ordered_desc = {}
            
            for key in ["identifier", "materials", "textures", "geometry"]:
                if key in desc:
                    ordered_desc[key] = desc[key]
            
            if "scripts" in desc:
                ordered_desc["scripts"] = desc["scripts"]
            
            if "animations" in desc:
                ordered_desc["animations"] = desc["animations"]
            
            if "render_controllers" in desc:
                ordered_desc["render_controllers"] = desc["render_controllers"]
            
            for key, value in desc.items():
                if key not in ordered_desc:
                    ordered_desc[key] = value
            
            self.attachable_data["minecraft:attachable"]["description"] = ordered_desc
            
            with open(self.attachable_path, 'w', encoding='utf-8') as f:
                json.dump(self.attachable_data, f, indent=2, ensure_ascii=False)
            print(f"✅ บันทึกไฟล์ Attachable: {self.attachable_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกไฟล์ Attachable: {e}")
            return False
        
        return True

