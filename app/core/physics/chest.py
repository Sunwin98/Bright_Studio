"""Physics generator class extracted verbatim from chest_physics.py.
Only the tkinter CLI wrappers were dropped; the class logic is unchanged.
"""
import json
import os
import re


class ChestPhysicsGenerator:
    """
    สร้าง Chest Physics แบบ Spring-Damping
    
    ตัวแปรที่ใช้ (ชื่อที่อ่านง่าย):
    - variable.chest_bounce        : ค่า Bounce หลัก (ใช้ใน animation)
    - variable.chest_velocity      : ความเร็วการเด้ง
    - variable.vertical_speed      : ความเร็วแนวตั้งของผู้เล่น
    - variable.sneak_change        : ตรวจจับการเปลี่ยนสถานะย่อ
    - variable.was_sneaking        : สถานะย่อก่อนหน้า
    """
    
    def __init__(self):
        self.animation_data = None
        self.attachable_data = None
        self.bone_groups = []
        self.animation_path = None
        self.attachable_path = None
        
        # =========================
        # Physics Parameters (ปรับได้)
        # =========================
        self.params = {
            # Spring-Damping
            "damping": 0.95,           # การลดความเร็ว (0.9-0.99, ยิ่งสูงยิ่งเด้งนาน)
            "spring_force": 0.05,      # แรงดึงกลับ (ยิ่งสูงยิ่งกลับเร็ว)
            
            # Force Multipliers
            "vertical_force": 0.05,    # แรงจากกระโดด/ตก
            "vertical_clamp": 2.5,     # จำกัดค่า vertical force
            "move_force": 1.0,         # แรงจากการเดิน (0-1)
            "sneak_force": 2.0,        # แรงจากการย่อ/ลุก
            
            # Position offset
            "position_multiplier": 0.08  # ขนาดการเลื่อน Y
        }
        
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
    
    def generate_initialize_scripts(self):
        """
        สร้าง initialize scripts (ตั้งค่าเริ่มต้น)
        ใช้ชื่อตัวแปรที่อ่านง่าย
        """
        return [
            "variable.chest_bounce=0;",       # ค่า Bounce หลัก
            "variable.chest_velocity=0;",     # ความเร็วการเด้ง
            "variable.vertical_speed=0;",     # ความเร็วแนวตั้ง
            "variable.sneak_change=0;",       # การเปลี่ยนสถานะย่อ
            "variable.was_sneaking=0;",       # สถานะย่อก่อนหน้า
        ]
    
    def generate_pre_animation_scripts(self):
        """
        สร้าง pre_animation scripts (คำนวณฟิสิกส์ทุก frame)
        
        สูตร Spring-Damping Physics:
        1. velocity = (velocity - vertical_force - spring_force) * damping
        2. bounce = bounce + velocity + move_force + sneak_force
        """
        p = self.params
        
        scripts = [
            # 1. เก็บค่า vertical_speed
            "variable.vertical_speed=query.vertical_speed;",
            
            # 2. ตรวจจับการเปลี่ยนสถานะย่อ (sneak toggle)
            "variable.sneak_change=math.abs(variable.was_sneaking-query.is_sneaking)*2;",
            
            # 3. อัพเดทสถานะย่อก่อนหน้า
            "variable.was_sneaking=query.is_sneaking;",
            
            # 4. คำนวณ Velocity (ความเร็วการเด้ง)
            # velocity = (velocity - vertical_force - spring_back) * damping
            f"variable.chest_velocity=(variable.chest_velocity-(math.clamp(variable.vertical_speed*2,-{p['vertical_clamp']},{p['vertical_clamp']})*{p['vertical_force']})-(variable.chest_bounce*{p['spring_force']}))*{p['damping']};",
            
            # 5. คำนวณ Bounce หลัก
            # bounce = bounce + velocity + move_force + sneak_force
            f"variable.chest_bounce=variable.chest_bounce+variable.chest_velocity+(query.is_moving*{p['move_force']})+(variable.sneak_change*{p['sneak_force']});",
        ]
        
        return scripts
    
    def generate_chest_physics(self, bones):
        """
        สร้าง Chest/Armor Physics Animation
        
        ใช้ variable.chest_bounce สำหรับ:
        - rotation X: หมุนก้ม-เงย
        - position Y: เลื่อนขึ้น-ลง
        """
        chest_bones = {}
        p = self.params
        
        for i, bone_name in enumerate(bones):
            chest_bones[bone_name] = {
                "rotation": [
                    "variable.chest_bounce",  # หมุนแกน X (ก้มเงย)
                    0,
                    0
                ],
                "position": [
                    0,
                    f"-variable.chest_bounce*{p['position_multiplier']}",  # เลื่อน Y ลงตามค่า bounce
                    0
                ]
            }
        
        return chest_bones
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        all_anim_refs = []
        
        for group in self.bone_groups:
            prefix = group["prefix"]
            bones = group["bones"]
            
            # สร้าง Chest Physics
            chest_anim_name = f"animation.{prefix.lower()}.chest_physics"
            chest_bones = self.generate_chest_physics(bones)
            animations[chest_anim_name] = {
                "loop": True,
                "bones": chest_bones
            }
            print(f"✅ สร้าง Chest Physics: {chest_anim_name} ({len(chest_bones)} bones)")
            
            all_anim_refs.append({
                "prefix": prefix,
                "chest": chest_anim_name
            })
        
        return all_anim_refs
    
    def update_attachable_file(self, anim_refs):
        """
        อัพเดทไฟล์ attachable
        เพิ่ม initialize, pre_animation, และ animation references
        """
        if not self.attachable_data:
            print("ℹ️  ข้ามการแก้ไข attachable (ไม่มีไฟล์)")
            return
            
        desc = self.attachable_data["minecraft:attachable"]["description"]
        
        # === Scripts ===
        if "scripts" not in desc:
            desc["scripts"] = {}
        
        # Initialize (ตั้งค่าเริ่มต้น)
        if "initialize" not in desc["scripts"]:
            desc["scripts"]["initialize"] = []
        
        init_scripts = self.generate_initialize_scripts()
        for script in init_scripts:
            if script not in desc["scripts"]["initialize"]:
                desc["scripts"]["initialize"].append(script)
        
        # Pre-animation (คำนวณทุก frame)
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        pre_anim_scripts = self.generate_pre_animation_scripts()
        for script in pre_anim_scripts:
            if script not in desc["scripts"]["pre_animation"]:
                desc["scripts"]["pre_animation"].append(script)
        
        # Animate และ Animations
        if "animate" not in desc["scripts"]:
            desc["scripts"]["animate"] = []
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        for ref in anim_refs:
            prefix = ref["prefix"]
            chest_key = f"{prefix.lower()}_chest"
            desc["animations"][chest_key] = ref["chest"]
            if chest_key not in desc["scripts"]["animate"]:
                desc["scripts"]["animate"].append(chest_key)
        
        print(f"✅ เพิ่ม scripts และ animations ใน attachable")
        print(f"   📌 Initialize: {len(init_scripts)} ตัวแปร")
        print(f"   📌 Pre-animation: {len(pre_anim_scripts)} สูตร")
        print(f"   📌 Animations: {len(anim_refs)} groups")
    
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

