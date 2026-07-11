"""Physics generator class extracted verbatim from head_rotation.py.
Only the tkinter CLI wrappers were dropped; the class logic is unchanged.
"""
import json
import os
import re


class HeadRotationGenerator:
    def __init__(self):
        self.animation_data = None
        self.attachable_data = None
        self.head_bone_name = None
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
    
    def generate_head_rotation(self, bone_name):
        """
        สร้าง Head Rotation Animation
        - Y rotation: variable.z (เอียงซ้าย-ขวาตามหัว)
        - Z rotation: -variable.rot (หมุนตาม target)
        """
        head_rotation = {
            bone_name: {
                "rotation": [0, "variable.z", "-variable.rot"]
            }
        }
        return head_rotation
    
    def generate_smooth_head(self, bone_name):
        """
        สร้าง Smooth Head Animation
        - X rotation: v.BrightSmoothHeadX * 0.4 (ก้ม/เงย)
        - Y rotation: v.BrightSmoothHeadY * 0.4 (หันซ้าย/ขวา)
        - Z rotation: v.BrightSmoothHeadZ * 0.4 (เอียงหัว)
        """
        smooth_head = {
            bone_name: {
                "rotation": [
                    "v.BrightSmoothHeadX * 0.4",
                    "v.BrightSmoothHeadY * 0.4",
                    "v.BrightSmoothHeadZ * 0.4"
                ]
            }
        }
        return smooth_head
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        
        # สร้าง Head Rotation Animation
        head_anim_name = "animation.Bright.head.rotation"
        head_bones = self.generate_head_rotation(self.head_bone_name)
        animations[head_anim_name] = {
            "loop": True,
            "bones": head_bones
        }
        print(f"✅ สร้าง Head Rotation: {head_anim_name} (bone: {self.head_bone_name})")
        
        # สร้าง Smooth Head Animation
        smooth_anim_name = "animation.Bright.head.smooth"
        smooth_bones = self.generate_smooth_head(self.head_bone_name)
        animations[smooth_anim_name] = {
            "loop": True,
            "bones": smooth_bones
        }
        print(f"✅ สร้าง Smooth Head: {smooth_anim_name} (bone: {self.head_bone_name})")
        
        return head_anim_name, smooth_anim_name
    
    def update_attachable_file(self, head_anim_name, smooth_anim_name):
        """อัพเดทไฟล์ attachable ด้วย scripts สำหรับ head rotation และ smooth head"""
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
            # Smooth Head variables
            "v.BrightLastHead = query.head_y_rotation(0);",
            "v.BrightSmoothHeadX = q.head_x_rotation(0);",
            "v.BrightSmoothHeadY = q.head_y_rotation(0) - q.body_y_rotation;",
            "v.BrightSmoothHeadZ = 0;",
            # Head Rotation variables
            "variable.p=0;",
            "variable.Xt=0;",
            "variable.pas=0;",
            "variable.nine=9;"
        ]
        
        for script in init_scripts:
            if script not in desc["scripts"]["initialize"]:
                desc["scripts"]["initialize"].append(script)
        
        # Pre-animation scripts
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        pre_anim_scripts = [
            # Smooth Head calculations
            "v.BrightRawHead = query.head_y_rotation(0);",
            "v.BrightLastHead = v.BrightRawHead;",
            "v.BrightTargetSmoothHeadX = q.head_x_rotation(0);",
            "v.BrightTargetSmoothHeadY = q.head_y_rotation(0) - q.body_y_rotation;",
            "v.BrightSmoothDeltaX = v.BrightTargetSmoothHeadX - v.BrightSmoothHeadX;",
            "v.BrightSmoothDeltaY = v.BrightTargetSmoothHeadY - v.BrightSmoothHeadY;",
            "v.BrightSmoothDeltaY = v.BrightSmoothDeltaY - math.floor((v.BrightSmoothDeltaY + 180) / 360) * 360;",
            "v.BrightSmoothHeadX = v.BrightSmoothHeadX + v.BrightSmoothDeltaX / 25;",
            "v.BrightSmoothHeadY = v.BrightSmoothHeadY + v.BrightSmoothDeltaY / 25;",
            "v.BrightSmoothHeadY = v.BrightSmoothHeadY - math.floor((v.BrightSmoothHeadY + 180) / 360) * 360;",
            "v.BrightSmoothHeadZ = v.BrightSmoothHeadY * 0.05;",
            "v.BrightSmoothHeadX = math.clamp(v.BrightSmoothHeadX, -30, 30);",
            "v.BrightSmoothHeadY = math.clamp(v.BrightSmoothHeadY, -30, 30);",
            # Head Rotation calculations
            "variable.center=query.head_y_rotation(0)-variable.p;",
            "variable.center>90?{variable.center=variable.center-360;};",
            "variable.center<-90?{variable.center=variable.center+360;};",
            "variable.Xt=(variable.Xt-(math.clamp(variable.center,-4.5,4.5)*0.02)-(variable.pas*0.08))*0.75;",
            "variable.pas=variable.pas+variable.Xt;",
            "variable.p=query.head_y_rotation(0);",
            "variable.z=math.clamp(variable.pas,-4.5,4.5);",
            "variable.rot=-query.target_y_rotation/variable.nine;"
        ]
        
        # ลบ scripts เก่าที่เกี่ยวกับ head rotation และ smooth head
        head_vars = [
            "variable.center", "variable.Xt", "variable.pas", 
            "variable.p", "variable.z", "variable.rot",
            "v.BrightRawHead", "v.BrightLastHead", "v.BrightTargetSmoothHeadX",
            "v.BrightTargetSmoothHeadY", "v.BrightSmoothDeltaX", "v.BrightSmoothDeltaY",
            "v.BrightSmoothHeadX", "v.BrightSmoothHeadY", "v.BrightSmoothHeadZ"
        ]
        
        desc["scripts"]["pre_animation"] = [
            script for script in desc["scripts"]["pre_animation"]
            if not any(script.strip().startswith(var) for var in head_vars)
        ]
        
        # เพิ่ม scripts ใหม่
        for script in pre_anim_scripts:
            desc["scripts"]["pre_animation"].append(script)
        
        # Animate และ Animations
        if "animate" not in desc["scripts"]:
            desc["scripts"]["animate"] = []
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        # เพิ่ม smooth head animation (ต้องมาก่อน)
        smooth_key = "Bright_head_smooth"
        desc["animations"][smooth_key] = smooth_anim_name
        if smooth_key not in desc["scripts"]["animate"]:
            # Insert at beginning
            desc["scripts"]["animate"].insert(0, smooth_key)
        
        # เพิ่ม head rotation animation
        head_key = "Bright_head_rotation"
        desc["animations"][head_key] = head_anim_name
        if head_key not in desc["scripts"]["animate"]:
            desc["scripts"]["animate"].append(head_key)
        
        print(f"✅ เพิ่ม scripts และ animations ใน attachable")
    
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

