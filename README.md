# Heaven Send Studio

พื้นที่ทำงานรวมสำหรับสร้าง Minecraft Bedrock addon — รวมเครื่องมือเดิมทั้งหมดไว้ในหน้าต่างเดียว ธีม **"Neon Yokochō"** (retro-pixel ญี่ปุ่นกลางคืน): titlebar เอง, intro boot, CRT scanline จางๆ, ป้าย katakana เรืองแสง (แท็บเครื่องมือซ้าย, ระบบขวาเต็มจอ)

> ธีมคุมด้วย CSS variables ใน `web/css/theme.css` (tokens/fonts/effects) — `web/css/app.css` เป็นโครงสร้าง component ที่คงชื่อ class เดิมไว้ทั้งหมด

## เปิดใช้งาน

ดับเบิลคลิก **`เปิด Studio.bat`**

หรือรันเอง:
```
py -3.12 run.py
```
โปรแกรมจะเปิดเป็นหน้าต่าง desktop (pywebview). ปิดหน้าต่าง = ปิดโปรแกรม

## เครื่องมือ (แท็บ)

| แท็บ | ทำอะไร |
|---|---|
| **โปรเจกต์** | ดูงานทั้งหมดใน `Projects` + `Projects Sillkes` (จัดกลุ่ม BP/RP/.mcaddon), ค้นหา, เปิดโฟลเดอร์, **แพ็ค `.mcaddon`**, **Deploy เข้าเกม** |
| **สร้างสกิน** | Skin Factory (v3) — สร้าง skin addon ครบชุด, preview icon, Normal/Special/No UI, Xbox lock |
| **ฟิสิกส์** | ใส่ฟิสิกส์ผมหลัง/cape/chest/head ให้ animation+attachable (สำรอง `.bak` ก่อนทุกครั้ง, dry-run ดู bones ก่อน) |
| **อาวุธ & สกิล** | TDC Generator — สร้าง entity + สคริปต์ combat/skill ลง BP/RP ที่มีอยู่ |
| **สร้างไอเทม/อาวุธ** | เพิ่มไอเทมถือได้ลง BP/RP — ใส่โมเดล + texture แล้วเชื่อม attachable อัตโนมัติ (อ่าน geometry id จากไฟล์เอง) |
| **Geo Swap** | ฝัง bone อาวุธในโมเดลผู้เล่น — ถืออาวุธแล้ว geometry สลับ (registry-based idempotent, merge player.entity.json + สำรอง .bak, สร้าง BP tag driver) |
| **แก้ Config อาวุธ** | เปิด `tdcmodel_*.js` แก้ค่าผ่านฟอร์ม, ผูก animation อัตโนมัติ, บันทึกกลับ |
| **ตรวจสอบ Addon** | validate ก่อนเข้าเกม — JSON เสีย, UUID ซ้ำ, manifest, script entry, icon/geometry ที่อ้างไฟล์ไม่มี |
| **รวม Addon** | รวมหลาย skin addon เป็นชุดเดียว (wrap skin_merger.py) |
| **ล้างขยะ** | หาโฟลเดอร์ backup/สำเนาซ้อน/cache ใน stores — dry-run report, ลบเฉพาะที่เลือกเอง |
| **จัดการไฟล์** | File Manager ของ `com.mojang` — สแกนทุกโปรไฟล์ (UWP/Preview/launcher users), ดู addon (BP/RP มี icon+version) และโลก (world icon + เล่นล่าสุด), **กดเข้าโลกดูว่ามี addon อะไรใช้อยู่**, เปิดในโฟลเดอร์, ลบลง Recycle Bin |
| **คลังความรู้** | อ่านเอกสาร SKILL-01..10 + คู่มือ SafeZoneCraft |
| **ตั้งค่า** | แก้พาธที่ทั้งแอปใช้ (project stores, master assets, output dir, knowledge dirs, com.mojang override) จากในแอป — มีผลทันที ไม่ต้องรีสตาร์ท |

Physics มี 6 tools: ผมหลัง (wave+yaw / yaw-only), ผมหน้า (front), cape, chest, head

### Export / Import / Deploy
- **แพ็ค .mcaddon**: zip BP+RP เป็นไฟล์เดียว วางข้างโปรเจกต์
- **Import .mcaddon**: ปุ่ม 📥 ในหน้าโปรเจกต์ — unzip .mcaddon กลับเข้า project store (ครบวงจรกับ Export)
- **Deploy**: copy BP/RP เข้า `com.mojang/development_*_packs` เทสต์ในเกมได้เลย — auto-detect ตำแหน่ง Minecraft (UWP/Preview) หรือกำหนดเองที่แท็บ **ตั้งค่า**

### Auto-validate
Skin build / Weapon generate / Item creator รัน Addon Checker ให้อัตโนมัติหลังสร้างเสร็จ — เห็น error/warning ทันทีในผลลัพธ์ ไม่ต้องสลับไปแท็บตรวจสอบเอง

## สถาปัตยกรรม

- **Backend**: FastAPI (`app/main.py`) — routers ต่อเครื่องมือใน `app/api/`
- **Core logic**: `app/core/` — คัดลอก logic จากสคริปต์เดิม (ต้นฉบับไม่ถูกแตะ, สคริปต์ CLI เดิมยังใช้ได้)
  - `skin_factory/builder.py` ← factory_skin_v3.py
  - `physics/` ← 5 physics scripts (ตัด tkinter)
  - `weapon/tdc_source.py` ← สร้างท่าโจมตี+สกิลอาวุธ.py (verbatim, byte-identical JS)
  - `filemanager/` ← สแกน com.mojang (packs/worlds/world-addons); path guard อยู่ที่ `app/api/filemanager.py`
- **Frontend**: HTML/CSS/JS vanilla ใน `web/` (ไม่มี build toolchain) — page module ใน `web/js/pages/`, reusable window ที่ `web/js/ui/window.js`
- **หน้าต่าง**: pywebview frameless (`run.py` รัน uvicorn แล้วเปิด window) — titlebar เองผ่าน `WindowApi` (min/max/close)

## Path ที่ใช้

ตั้งค่าได้จากแท็บ **ตั้งค่า** ในแอป (บันทึกลง `settings.json`, มีผลทันที) — ถ้ายังไม่เคยเซฟ ใช้ default ใน `config.py`:

- Projects: `D:\heaven send\Heaven_Send_Factory\Projects`, `...\Projects Sillkes`
- Master assets: `D:\heaven send\Heaven_Send_Factory\master_assets`
- Knowledge: `D:\Bedrock_Addon_Skills`, SafeZoneCraft docs
- com.mojang: auto-detect (UWP/Preview) หรือ override ที่ตั้งค่า

## ทดสอบ

```
py -3.12 tests/test_skin.py
py -3.12 tests/test_physics.py
py -3.12 tests/test_weapon.py
py -3.12 tests/test_config.py
```
ทุกตัวเทียบผลกับสคริปต์ต้นฉบับ (byte-identical) เพื่อยืนยันว่า logic ไม่เพี้ยน

## Requirements

Python 3.12 + `fastapi uvicorn pywebview Pillow send2trash` (ดู `requirements.txt`)
