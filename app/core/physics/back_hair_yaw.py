"""Physics generator class extracted verbatim from back_hair_v2_yaw.py.
Only the tkinter CLI wrappers were dropped; the class logic is unchanged.
"""
import json
import os
import re


class BackHairYawOnlyGenerator:
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
    
    def generate_yaw_pitch_physics(self, bones, strength_multiplier=None):
        """
        สร้าง Yaw + Pitch Physics สำหรับผมหลัง
        - Yaw: หันซ้าย-ขวา พลิ้วอ่อนนุ่ม
        - Pitch: ก้ม/เงยหน้า ผมตกตามแรงโน้มถ่วง
        - ❌ ไม่มี Wave (ไม่ปลิ้วตอนเดิน)
        
        Auto-calculate strength based on bone count:
        - 1-5 bones: strength_factor = 1.2
        - 6-10 bones: strength_factor = 1.0
        - 11-15 bones: strength_factor = 0.8
        - 16+ bones: strength_factor = 0.6
        """
        bone_count = len(bones)
        
        # คำนวณ strength factor ตามจำนวน bones
        if bone_count <= 5:
            auto_strength_factor = 1.2
        elif bone_count <= 10:
            auto_strength_factor = 1.0
        elif bone_count <= 15:
            auto_strength_factor = 0.8
        else:
            auto_strength_factor = 0.6
        
        # ใช้ค่าที่ผู้ใช้กำหนด หรือใช้ค่าอัตโนมัติ
        strength_factor = strength_multiplier if strength_multiplier is not None else auto_strength_factor
        
        print(f"   📊 Bones: {bone_count}, Strength Factor: {strength_factor:.1f} {'(auto)' if strength_multiplier is None else '(custom)'}")
        
        physics_bones = {}
        
        for i, bone_name in enumerate(bones):
            # Yaw multiplier: ไล่จากโคน (น้อย) ไปปลาย (มาก)
            if i == 0:
                yaw_mult = 0.20 * strength_factor
            elif i == bone_count - 1:
                yaw_mult = 1.0 * strength_factor
            else:
                progress = i / max(1, bone_count - 1)
                yaw_mult = (0.20 + (progress * 0.80)) * strength_factor
            
            if i == 0:
                # bone แรก (โคน): ใช้ pitch ด้วย (ก้ม/เงยหน้า)
                physics_bones[bone_name] = {
                    "rotation": [
                        f"-v.headPitch",
                        0,
                        f"v.hairYawPhysics * {yaw_mult:.2f}"
                    ]
                }
            else:
                # bone ถัดไป: ใช้แค่ yaw (ไม่มี wave)
                physics_bones[bone_name] = {
                    "rotation": [
                        0,
                        0,
                        f"v.hairYawPhysics * {yaw_mult:.2f}"
                    ]
                }
        
        return physics_bones
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        all_anim_refs = []
        
        for group in self.bone_groups:
            prefix = group["prefix"]
            bones = group["bones"]
            strength_mult = group.get("strength_multiplier", None)
            
            # สร้าง Yaw + Pitch Physics (รวมเป็น animation เดียว)
            anim_name = f"animation.{prefix.lower()}.yaw_physics"
            physics_bones = self.generate_yaw_pitch_physics(bones, strength_mult)
            animations[anim_name] = {
                "loop": True,
                "bones": physics_bones
            }
            print(f"✅ สร้าง Yaw+Pitch Physics: {anim_name} ({len(physics_bones)} bones)")
            
            all_anim_refs.append({
                "prefix": prefix,
                "yaw": anim_name
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
        
        # Initialize scripts
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
        
        # Pre-animation scripts
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        pre_anim_scripts = [
            # คำนวณ delta และ wrap around
            "v.headYawDelta = query.head_y_rotation(0) - v.prevHeadYaw;",
            "v.headYawDelta = v.headYawDelta > 180 ? v.headYawDelta - 360 : (v.headYawDelta < -180 ? v.headYawDelta + 360 : v.headYawDelta);",
            # Clamp input delta
            "v.headYawDelta = math.clamp(v.headYawDelta, -8.0, 8.0);",
            # Yaw Physics
            "v.hairYawVel = v.hairYawVel + (v.headYawDelta * 0.018);",
            "v.hairYawVel = v.hairYawVel - (v.hairYawPhysics * 0.015);",
            "v.hairYawVel = v.hairYawVel * 0.88;",
            "v.hairYawPhysics = v.hairYawPhysics + v.hairYawVel;",
            "v.hairYawPhysics = math.clamp(v.hairYawPhysics, -4, 4);",
            "v.prevHeadYaw = query.head_y_rotation(0);",
            # Pitch Physics - ผมตกเมื่อก้ม/เงยหน้า
            "v.pitchDelta = query.target_x_rotation - v.headPitch;",
            "v.pitchVel = v.pitchVel + (v.pitchDelta * 0.08);",
            "v.pitchVel = v.pitchVel * 0.85;",
            "v.headPitch = v.headPitch + v.pitchVel;"
        ]
        
        # ลบ scripts เก่าที่เกี่ยวข้อง
        hair_physics_keywords = [
            "v.headYawDelta",
            "v.hairYawVel", 
            "v.hairYawPhysics",
            "v.prevHeadYaw",
            "v.headPitch",
            "v.pitchVel",
            "v.pitchDelta"
        ]
        
        desc["scripts"]["pre_animation"] = [
            script for script in desc["scripts"]["pre_animation"]
            if not any(keyword in script for keyword in hair_physics_keywords)
        ]
        
        for script in reversed(pre_anim_scripts):
            desc["scripts"]["pre_animation"].insert(0, script)
        
        # เรียงลำดับ
        def get_script_priority(script):
            s = script.strip()
            if s.startswith("v.headYawDelta"):
                return 10
            if s.startswith("v.hairYawVel") or s.startswith("v.frontHairVel"):
                return 20
            if s.startswith("v.hairYawPhysics") or s.startswith("v.frontHairYaw"):
                return 30
            if s.startswith("v.prevHeadYaw"):
                return 90
            if s.startswith("variable."):
                return 100
            return 50
        
        desc["scripts"]["pre_animation"].sort(key=get_script_priority)
        
        # Animate และ Animations
        if "animate" not in desc["scripts"]:
            desc["scripts"]["animate"] = []
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        for ref in anim_refs:
            prefix = ref["prefix"]
            
            # Yaw Physics (animation เดียว)
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

