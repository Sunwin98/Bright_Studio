"""Physics generator class extracted verbatim from cape_physics.py.
Only the tkinter CLI wrappers were dropped; the class logic is unchanged.
"""
import json
import os
import re


class CapePhysicsGenerator:
    def __init__(self):
        self.animation_data = None
        self.attachable_data = None
        self.bone_groups = []
        self.animation_path = None
        self.attachable_path = None
        self.cape_intensity = "medium"  # "light", "medium", "strong"
        
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
    
    def generate_cape_physics(self, bones, group_index=0, z_offset=0):
        """
        สร้าง Cape/Cloth Wave Physics v3.0
        สูตร: capeMoveVel * BASE + speed * SPEED_MULT
              + clamp(flap, 0, 1.0) * cos(PHASE - dist*18) * AMP
              + windSway * WIND
        Phase offset:
          - ระหว่าง group: +10° ต่อ group index
          - ระหว่าง root→tip ใน group เดียวกัน: +18° ต่อ bone
        """
        cape_bones = {}
        bone_count = len(bones)
        group_phase_offset = group_index * 10  # phase ต่างกันต่อ group

        # === ค่าตามความแรง ===
        if self.cape_intensity == "light":
            root_vel   = 0.8;  tip_vel   = 1.4
            root_speed = 10;   tip_speed = 20
            root_amp   = 6;    tip_amp   = 11
            root_wind  = 0.7;  tip_wind  = 1.2
            root_yaw   = 0.50; tip_yaw   = 0.80
        elif self.cape_intensity == "strong":
            root_vel   = 2.0;  tip_vel   = 3.5
            root_speed = 22;   tip_speed = 42
            root_amp   = 13;   tip_amp   = 24
            root_wind  = 1.5;  tip_wind  = 2.5
            root_yaw   = 0.75; tip_yaw   = 1.15
        else:  # medium
            root_vel   = 1.4;  tip_vel   = 2.4
            root_speed = 16;   tip_speed = 30
            root_amp   = 9;    tip_amp   = 17
            root_wind  = 1.0;  tip_wind  = 1.8
            root_yaw   = 0.62; tip_yaw   = 0.95

        for i, bone_name in enumerate(bones):
            # progress 0 = root, 1 = tip
            progress = i / max(1, bone_count - 1) if bone_count > 1 else 1.0

            vel   = root_vel   + (tip_vel   - root_vel)   * progress
            speed = root_speed + (tip_speed - root_speed) * progress
            amp   = root_amp   + (tip_amp   - root_amp)   * progress
            wind  = root_wind  + (tip_wind  - root_wind)  * progress
            yaw   = root_yaw   + (tip_yaw   - root_yaw)   * progress

            # phase: group offset + 18° ต่อ bone ใน chain
            phase = group_phase_offset + (i * 18)

            # Z offset ลดลงตามลำดับ
            cur_z = z_offset * (1 - progress * 0.4) if z_offset != 0 else 0
            z_part = f"v.capeYawVel * {yaw:.2f}"
            if cur_z > 0.01:
                z_part += f" + {cur_z:.2f}"
            elif cur_z < -0.01:
                z_part += f" - {abs(cur_z):.2f}"

            x_expr = (
                f"v.capeMoveVel * {vel:.1f} + (query.modified_move_speed * {speed})"
                f" + math.clamp(query.cape_flap_amount, 0, 1.0)"
                f" * math.cos({phase} - query.modified_distance_moved * 18) * {amp}"
                f" + v.windSway * {wind:.1f}"
            )

            cape_bones[bone_name] = {
                "rotation": [x_expr, 0, z_part]
            }

        return cape_bones
    
    def update_animation_file(self):
        """อัพเดทไฟล์ animation"""
        if "animations" not in self.animation_data:
            self.animation_data["animations"] = {}
        
        animations = self.animation_data["animations"]
        all_anim_refs = []
        
        # z_offset สลับซ้าย-ขวาต่อ group
        z_offsets = [0.5, -0.5, 0.3, -0.3, 0.2, -0.2, 0, 0]
        
        for idx, group in enumerate(self.bone_groups):
            prefix = group["prefix"]
            bones = group["bones"]
            z_offset = z_offsets[idx % len(z_offsets)]
            
            # Wave Physics — ชื่อใหม่ v3.0
            wave_anim_name = f"animation.{prefix.lower()}.wave_physics"
            wave_bones = self.generate_cape_physics(bones, group_index=idx, z_offset=z_offset)
            animations[wave_anim_name] = {
                "loop": True,
                "animation_length": 6,
                "bones": wave_bones
            }
            print(f"✅ สร้าง Wave Physics: {wave_anim_name} ({len(wave_bones)} bones, z={z_offset}, phase_start={idx*10}°)")
            
            all_anim_refs.append({
                "prefix": prefix,
                "cape": wave_anim_name
            })
        
        return all_anim_refs
    
    def get_attachable_scripts(self):
        """สร้าง scripts สำหรับ attachable (v3.0 — ค่าจาก coat_mkpj)"""

        # ค่าตามความแรง (อ้างอิงจาก coat_mkpj ที่ test แล้ว)
        if self.cape_intensity == "light":
            body_yaw_mult    = 0.4
            yaw_decay        = 0.95
            yaw_clamp        = 5
            yaw_lerp         = 0.04
            pitch_mult       = 2.0
            pitch_decay      = 0.96
            pitch_clamp      = 5
            pitch_lerp       = 0.03
            move_vel_mult    = 1.8
            pitch_smooth_mult= 0.25
            wind_time_add    = 0.055
            wind_sin1        = 0.35
            wind_sin2        = 0.18
            wind_sin2_freq   = 1.7
        elif self.cape_intensity == "strong":
            body_yaw_mult    = 0.6
            yaw_decay        = 0.95
            yaw_clamp        = 8
            yaw_lerp         = 0.04
            pitch_mult       = 3.5
            pitch_decay      = 0.96
            pitch_clamp      = 8
            pitch_lerp       = 0.025
            move_vel_mult    = 3.0
            pitch_smooth_mult= 0.35
            wind_time_add    = 0.065
            wind_sin1        = 0.55
            wind_sin2        = 0.28
            wind_sin2_freq   = 1.7
        else:  # medium
            body_yaw_mult    = 0.5
            yaw_decay        = 0.95
            yaw_clamp        = 6
            yaw_lerp         = 0.04
            pitch_mult       = 2.8
            pitch_decay      = 0.96
            pitch_clamp      = 6
            pitch_lerp       = 0.028
            move_vel_mult    = 2.4
            pitch_smooth_mult= 0.30
            wind_time_add    = 0.060
            wind_sin1        = 0.45
            wind_sin2        = 0.22
            wind_sin2_freq   = 1.7

        init_scripts = [
            "v.prevBodyYaw = 0;",
            "v.prevMoveSpeed = 0;",
            "v.capeYawTarget = 0;",
            "v.capeYawSmooth = 0;",
            "v.capePitchTarget = 0;",
            "v.capePitchSmooth = 0;",
            "v.windTime = 0;"
        ]

        pre_anim_scripts = [
            "v.bodyYawDelta = query.body_y_rotation - v.prevBodyYaw;",
            "v.bodyYawDelta = v.bodyYawDelta > 180 ? v.bodyYawDelta - 360 : (v.bodyYawDelta < -180 ? v.bodyYawDelta + 360 : v.bodyYawDelta);",
            "v.moveSpeedDelta = query.modified_move_speed - v.prevMoveSpeed;",
            # Yaw physics
            f"v.capeYawTarget = v.capeYawTarget - (v.bodyYawDelta * {body_yaw_mult});",
            f"v.capeYawTarget = v.capeYawTarget * {yaw_decay};",
            f"v.capeYawTarget = math.clamp(v.capeYawTarget, -{yaw_clamp}, {yaw_clamp});",
            f"v.capeYawSmooth = math.lerp(v.capeYawSmooth, v.capeYawTarget, {yaw_lerp});",
            # Pitch physics
            f"v.capePitchTarget = v.capePitchTarget + (v.moveSpeedDelta * {pitch_mult});",
            f"v.capePitchTarget = v.capePitchTarget * {pitch_decay};",
            f"v.capePitchTarget = math.clamp(v.capePitchTarget, -{pitch_clamp}, {pitch_clamp});",
            f"v.capePitchSmooth = math.lerp(v.capePitchSmooth, v.capePitchTarget, {pitch_lerp});",
            # Final vars
            f"v.capeMoveVel = query.modified_move_speed * {move_vel_mult} + v.capePitchSmooth * {pitch_smooth_mult};",
            "v.capeYawVel = v.capeYawSmooth;",
            # Wind
            f"v.windTime = v.windTime + {wind_time_add};",
            f"v.windSway = math.sin(v.windTime) * {wind_sin1} + math.sin(v.windTime * {wind_sin2_freq}) * {wind_sin2};",
            # Save prev
            "v.prevBodyYaw = query.body_y_rotation;",
            "v.prevMoveSpeed = query.modified_move_speed;"
        ]

        return init_scripts, pre_anim_scripts
    
    def update_attachable_file(self, anim_refs):
        """อัพเดทไฟล์ attachable ด้วย scripts สำหรับ cape physics"""
        if not self.attachable_data:
            print("ℹ️  ข้ามการแก้ไข attachable (ไม่มีไฟล์)")
            return
            
        desc = self.attachable_data["minecraft:attachable"]["description"]
        
        # === Scripts ===
        if "scripts" not in desc:
            desc["scripts"] = {}
        
        # Get scripts based on intensity
        init_scripts, pre_anim_scripts = self.get_attachable_scripts()
        
        # Initialize scripts
        if "initialize" not in desc["scripts"]:
            desc["scripts"]["initialize"] = []
        
        for script in init_scripts:
            if script not in desc["scripts"]["initialize"]:
                desc["scripts"]["initialize"].append(script)
        
        # Pre-animation scripts
        if "pre_animation" not in desc["scripts"]:
            desc["scripts"]["pre_animation"] = []
        
        # ลบ scripts เก่าที่เกี่ยวกับ cape
        cape_vars = [
            "v.bodyYawDelta", "v.capeYawTarget", "v.capeYawSmooth",
            "v.capePitchTarget", "v.capePitchSmooth", "v.capeMoveVel", "v.capeYawVel",
            "v.windTime", "v.windSway", "v.moveSpeedDelta",
            "v.prevBodyYaw", "v.prevMoveSpeed"
        ]
        
        desc["scripts"]["pre_animation"] = [
            script for script in desc["scripts"]["pre_animation"]
            if not any(script.strip().startswith(var) for var in cape_vars)
        ]
        
        # เพิ่ม scripts ใหม่
        for script in pre_anim_scripts:
            desc["scripts"]["pre_animation"].append(script)
        
        # Animate และ Animations
        if "animate" not in desc["scripts"]:
            desc["scripts"]["animate"] = []
        
        if "animations" not in desc:
            desc["animations"] = {}
        
        for ref in anim_refs:
            prefix = ref["prefix"]
            cape_key = f"{prefix.lower()}_cape"
            desc["animations"][cape_key] = ref["cape"]
            if cape_key not in desc["scripts"]["animate"]:
                desc["scripts"]["animate"].append(cape_key)
        
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

