"""Physics generator class extracted verbatim from front_hair.py.
Only the tkinter CLI wrappers were dropped; class logic is unchanged.
"""
import json
import os
import re


class FrontHairPhysicsGenerator:
    def __init__(self):
        self.animation_data = None
        self.attachable_data = None
        self.bone_groups = []
        self.animation_path = None
        self.attachable_path = None
        
    def load_files(self, animation_path, attachable_path=None):
        """โหลดไฟล์ animation และ attachable"""
        self.animation_path = animation_path
        self.attachable_path = attachable_path
        
        try:
            with open(animation_path, 'r', encoding='utf-8') as f:
                self.animation_data = json.load(f)
            print(f"✅ โหลดไฟล์ animation สำเร็จ: {animation_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถโหลดไฟล์ animation: {e}")
            return False
        
        if attachable_path:
            try:
                with open(attachable_path, 'r', encoding='utf-8') as f:
                    self.attachable_data = json.load(f)
                print(f"✅ โหลดไฟล์ attachable สำเร็จ: {attachable_path}")
            except Exception as e:
                print(f"❌ ไม่สามารถโหลดไฟล์ attachable: {e}")
                return False
        else:
            print("ℹ️  ข้ามการโหลด attachable (Animation เท่านั้น)")
            
        return True
    
    def find_bones_with_prefix(self, prefix):
        """ค้นหา bone ทั้งหมดที่ขึ้นต้นด้วย prefix"""
        found_bones = []
        
        if "animations" in self.animation_data:
            for anim_name, anim_data in self.animation_data["animations"].items():
                if "bones" in anim_data:
                    for bone_name in anim_data["bones"].keys():
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
    
    def generate_yaw_physics(self, bones):
        """
        สร้าง Yaw Physics สำหรับผมหน้า (Front)
        - ไหวแรง ตอบสนองเร็ว
        - ใช้ v.frontHairYaw
        """
        yaw_bones = {}
        
        for i, bone_name in enumerate(bones):
            # ผมหน้า: เริ่มที่ 0.50 แล้วเพิ่มขึ้นถึง 1.00
            if i == 0:
                multiplier = 0.50
            else:
                multiplier = min(1.00, 0.50 + (i * 0.25))
            
            yaw_bones[bone_name] = {
                "rotation": [0, 0, f"v.frontHairYaw * {multiplier:.2f}"]
            }
        
        return yaw_bones
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation - สร้างแค่ Yaw Physics"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        all_anim_refs = []
        
        for group in self.bone_groups:
            prefix = group["prefix"]
            bones = group["bones"]
            
            # สร้าง Yaw Physics (Front) เท่านั้น
            yaw_anim_name = f"animation.{prefix.lower()}.yaw_physics"
            yaw_bones = self.generate_yaw_physics(bones)
            animations[yaw_anim_name] = {
                "loop": True,
                "bones": yaw_bones
            }
            print(f"✅ สร้าง Yaw Physics (ผมหน้า): {yaw_anim_name} ({len(yaw_bones)} bones)")
            
            all_anim_refs.append({
                "prefix": prefix,
                "yaw": yaw_anim_name
            })
        
        return all_anim_refs
    
    def update_attachable_file(self, anim_refs):
        """อัพเดทไฟล์ attachable ด้วย scripts สำหรับผมหน้า"""
        if not self.attachable_data:
            print("ℹ️  ข้ามการแก้ไข attachable (ไม่มีไฟล์)")
            return
            
        desc = self.attachable_data["minecraft:attachable"]["description"]
        
        # === Scripts ===
        if "scripts" not in desc:
            desc["scripts"] = {}
        
        # Initialize scripts (เฉพาะที่ต้องใช้สำหรับผมหน้า)
        if "initialize" not in desc["scripts"]:
            desc["scripts"]["initialize"] = []
        
        init_scripts = [
            "v.frontHairYaw = 0;",
            "v.frontHairVel = 0;",
            "v.prevHeadYaw = 0;"
        ]
        
        for script in init_scripts:
            if script not in desc["scripts"]["initialize"]:
                desc["scripts"]["initialize"].append(script)
        
        # Pre-animation scripts (เฉพาะที่ต้องใช้สำหรับผมหน้า)
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        pre_anim_scripts = [
            # คำนวณ delta และ wrap around
            "v.headYawDelta = query.head_y_rotation(0) - v.prevHeadYaw;",
            "v.headYawDelta = v.headYawDelta > 180 ? v.headYawDelta - 360 : (v.headYawDelta < -180 ? v.headYawDelta + 360 : v.headYawDelta);",
            # Clamp input delta
            "v.headYawDelta = math.clamp(v.headYawDelta, -4.0, 4.0);",
            # Front Hair Physics - ไหวแรง ตอบสนองเร็ว
            "v.frontHairVel = v.frontHairVel + (v.headYawDelta * 0.04);",   # sensitivity: 0.04
            "v.frontHairVel = v.frontHairVel - (v.frontHairYaw * 0.03);",   # stiffness: 0.03
            "v.frontHairVel = v.frontHairVel * 0.95;",                       # damping: 0.95
            "v.frontHairYaw = v.frontHairYaw + v.frontHairVel;",
            "v.frontHairYaw = math.clamp(v.frontHairYaw, -5.5, 5.5);",
            "v.prevHeadYaw = query.head_y_rotation(0);"
        ]
        
        # ลบ scripts เก่าที่เกี่ยวกับ front hair เท่านั้น (ไม่ลบของ back hair)
        front_hair_only_vars = [
            "v.frontHairVel", "v.frontHairYaw"
        ]
        
        # ลบเฉพาะ front hair vars
        desc["scripts"]["pre_animation"] = [
            script for script in desc["scripts"]["pre_animation"]
            if not any(script.strip().startswith(var) for var in front_hair_only_vars)
        ]
        
        # เพิ่ม scripts ใหม่ (ข้าม v.headYawDelta และ v.prevHeadYaw ถ้ามีอยู่แล้ว)
        for script in pre_anim_scripts:
            var_name = script.split("=")[0].strip() if "=" in script else ""
            # ตรวจสอบว่ามี script ที่ใช้ตัวแปรนี้อยู่แล้วหรือไม่
            exists = any(s.strip().startswith(var_name) for s in desc["scripts"]["pre_animation"])
            if not exists:
                desc["scripts"]["pre_animation"].append(script)
        
        # === เรียงลำดับ pre_animation ให้ถูกต้อง ===
        # v.headYawDelta ต้องมาก่อน v.hairYawVel และ v.frontHairVel
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
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        for ref in anim_refs:
            prefix = ref["prefix"]
            
            # Yaw Physics เท่านั้น (ไม่มี Wave)
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
            print(f"✅ บันทึกไฟล์ animation: {self.animation_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกไฟล์ animation: {e}")
            return False
        
        # บันทึก attachable
        if not self.attachable_data or not self.attachable_path:
            print("ℹ️  ข้ามการบันทึก attachable")
            return True
        
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
            print(f"✅ บันทึกไฟล์ attachable: {self.attachable_path}")
        except Exception as e:
            print(f"❌ ไม่สามารถบันทึกไฟล์ attachable: {e}")
            return False
        
        return True

