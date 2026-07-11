# HANDOFF — Bright Studio (Neon Yokochō rework)

เอกสารส่งต่อสำหรับ AI/dev คนถัดไป. อ่านไฟล์นี้ + [README.md](README.md) ก่อนเริ่ม.

> **อัปเดต (2026-07-10)**: บัค 8 จุดจาก `GEMINI_FIX_PLAN.md` ได้ถูกแก้ไขเรียบร้อยแล้ว รวมถึง Part C เกือบทั้งหมด (C1-C8)

**สถานะ:** การย้ายมาใช้ Neutralino สมบูรณ์แบบ การตั้งค่าและ backend ไม่มีบัคแล้ว. ทุกหน้าและฟีเจอร์ใหม่ (มาสคอต, เสียง, ค้นหา/กรองใน FM) ทำงานได้ปกติ.

> **ผลตรวจซ้ำ (Claude, 2026-07-10 22:15):** ยืนยันบัค 8 จุดแก้จริง — รัน `backend.exe` จาก dist แล้วยิง HTTP: `/api/health` `/api/projects` `/api/fm/profiles` `/api/fm/worlds` `/api/settings` = **200 ทั้งหมด**, pytest 11 passed, `%APPDATA%\HeavenSendStudio` ถูกสร้าง, `resources.neu` build ทันโค้ดล่าสุด. **เหลือทดสอบมือ 1 อย่าง:** เปิด `dist\heaven-send-studio\heaven-send-studio-win_x64.exe` → กด ✕ ปิด → เช็ค Task Manager ว่า `backend.exe` ไม่ค้าง (ทำ 3 รอบ). จุดจิ๋วที่รู้ไว้: BGM ตอนนี้เป็นเสียง sine hum 110Hz ไม่ใช่เพลงจริง — ถ้าอยากได้ lo-fi จริงต้องหาไฟล์ CC0 มาใส่.

---

## 1. Environment / วิธีรัน (สำคัญ)

- Python: `C:/Users/ASUS/AppData/Local/Programs/Python/Python312/python.exe` (มี deps ครบ)
- รันแอปจริง: ดับเบิลคลิก `เปิด Studio.bat` หรือ `py -3.12 run.py` → เปิด pywebview window (frameless, titlebar เอง)
- Dev preview (browser): uvicorn ที่ `.claude/launch.json` (port 8777) — ปุ่ม titlebar จะซ่อนอัตโนมัติในโหมด browser (ไม่มี `window.pywebview`)
- Deps: `fastapi uvicorn pywebview Pillow send2trash`

### ⚠️ Gotcha ที่ต้องรู้
1. โปรเจกต์นี้มี `fastapi 0.139.0` + `starlette 1.3.1` (major แปลก). **การ introspect `app.routes` ไม่สะท้อน router ที่ include** — อย่าตัดสินว่า route ลงทะเบียนไหมจาก `[r.path for r in app.routes]` (จะเห็นแค่ `/api/health`). **ให้ยิง HTTP จริง** ที่ server port 8777 แทน. เสียเวลา debug มาแล้ว.
2. **Neutralino `tokenSecurity` ต้องเป็น `"none"` บนเครื่องนี้** (แก้เมื่อ 2026-07-10). ค่า `"one-time"` ทำให้เปิดแอปแล้วจอขาว error `NE_CL_IVCTOKN` — WebView2 บนเครื่องนี้ request หน้าเว็บซ้ำจน token โดนใช้ทิ้งก่อน client ต่อ WS. Trade-off ที่ยอมรับ: server ของ Neutralino (localhost, random port) ไม่มี token — process/เว็บ local อื่นในเครื่องเชื่อม WS ได้ตามทฤษฎี (`nativeAllowList` เปิด `os.*`). เครื่องมือส่วนตัว local-only ยอมรับได้; ถ้าจะแจกจ่ายจริงค่อยหาทางกลับไป one-time. **ห้ามสลับกลับโดยไม่ทดสอบเปิดแอปจริง.** อาการเดียวกันเกิดได้ถ้ามี instance เก่าค้าง — `taskkill /F /IM heaven-send-studio-win_x64.exe` + ลบ `.tmp` ข้าง exe ก่อน.

---

## 2. สถาปัตยกรรม (ต้องคงรูปแบบนี้)

- **core + api แยกกัน**: logic บริสุทธิ์อยู่ `app/core/<tool>/`, router บางอยู่ `app/api/<tool>.py` แล้วเพิ่มชื่อ module ใน loop ที่ [app/main.py](app/main.py) (บรรทัด ~25)
- **Frontend vanilla** (ไม่มี build tool): page module ที่ `web/js/pages/<id>.js` export `async function render(main)`. เพิ่ม tab ที่ `TABS` ใน [web/js/app.js](web/js/app.js)
- **helper กลาง**: `el()` + `api.get/post` + `pickSingle` ที่ [web/js/api.js](web/js/api.js) — ใช้ตัวนี้ อย่าเขียน DOM/fetch เอง
- **ธีม**: tokens อยู่ [web/css/theme.css](web/css/theme.css), โครง component [web/css/app.css](web/css/app.css). **ห้ามเปลี่ยนชื่อ class เดิม** (หน้าเพจพึ่งพา)
- **reusable window**: `openWindow()` / `confirmDialog()` ที่ [web/js/ui/window.js](web/js/ui/window.js) — ใช้ทำ modal/หน้าต่างลอย

---

## 3. งานรอบนี้ทำอะไรไป

| ส่วน | ไฟล์ | หมายเหตุ |
|---|---|---|
| ธีม Neon Yokochō | `web/css/theme.css` (ใหม่), `web/css/app.css` (rewrite) | night gradient, neon, pixel font, CRT, katakana |
| Titlebar + intro | `web/index.html`, `web/js/app.js`, `run.py` | frameless + `WindowApi` (min/max/close) |
| FM backend | `app/core/filemanager/__init__.py`, `app/api/filemanager.py`, `config.py:find_profiles()` | scan com.mojang, path guard, send2trash |
| FM frontend | `web/js/pages/filemanager.js`, `web/js/ui/window.js` | addon/world grid + world drill-in |
| Tests | `tests/test_filemanager.py` | 4 ผ่าน (scanner + guard) |

**FM ทำได้:** ดู/ลบ addon (BP/RP), ดู/ลบโลก, กดเข้าโลกดู addon ที่ใช้ (resolve ชื่อข้ามโปรไฟล์), เปิดโฟลเดอร์. ลบ = ลง Recycle Bin.

### ยัง verify ไม่ครบ (คนถัดไปช่วยเช็ค)
- **delete flow live**: ยังไม่กดลบจริง (กันลบโลก/addon ของ user). ควรทดสอบด้วย addon/โลกที่ทิ้งได้

---

### อัปเดต 2026-07-11 — รอบ "in-app explorer + โซน"
- **In-app file explorer** (`web/js/ui/explorer.js` + `/api/fs/*` ใน `app/api/fsbrowse.py`): `pickPath()` ทุกหน้าเปิดตัวนี้แทน native dialog; ปุ่ม 📂 ใน FM เปิดดูในแอป ไม่เด้ง Windows Explorer
- **FM auto profile**: แท็บ ADD-ONS → "Shared Add-ons", แท็บ WORLDS → โปรไฟล์ User อัตโนมัติ (dropdown ยัง override ได้)
- **World editor**: หน้าต่างโลกแยก "ใช้อยู่ในโลกนี้ / เพิ่มเข้าโลกได้" + ค้นหา + ปุ่ม เพิ่ม/เอาออก
- **packio** (`app/core/packio.py` + `/api/packio/inspect`): รับ .mcaddon/.mcpack/.zip/โฟลเดอร์ → แยก BP/RP อัตโนมัติจาก manifest modules; หน้า checker ใช้แล้ว (เลือกไฟล์เดียวจบ)
- **โซน sidebar**: โซนสกิน (โปรเจกต์สกิน=`Heaven_Send_Factory\Projects`, สร้างสกิน, ฟิสิกส์) / โซนสกิล (โปรเจกต์สกิล=`Projects Sillkes`, อาวุธ, ไอเทม, weaponcfg) / จัดการ / อื่นๆ — path โซนแก้ได้ผ่าน `zone_stores` ใน settings.json; **ลบ Geo Swap แล้ว**
- **อนิเมชั่น**: page-enter stagger, card fade-in, tab slide+glow, button press, title glow — ท้าย `app.css`
- **บัคแฝงที่แก้**: `window.Neutralino` มีเสมอแม้ใน browser (neutralino.js define global) → เช็คผ่าน `window.HS_IS_NEU` (`typeof NL_PORT !== "undefined"`) + `HS_BACKEND_READY` flag กัน race ที่ event `hs-backend-ready` ยิงก่อน app.js ติด listener — **ห้ามเช็ค `window.Neutralino` ตรงๆ อีก**
- pytest 16 passed · exe rebuild แล้ว endpoint ใหม่ครบ (fs/packio/projects?zone)

### อัปเดต 2026-07-11 (รอบค่ำ) — "Smart Workspaces + Rebranding & Minimize Fix"
- **วิดีโอพื้นหลังลูป (Countryside Morning Theme)**: เปลี่ยนพื้นหลังหน้าจอบู๊ตและเวิร์กสเปซหลักให้ใช้วิดีโออนิเมะตอนเช้าของชนบทและรางรถไฟในสายหมอก (.mp4) ย้ายป้ายวิดีโอออกนอก main layout เพื่อป้องกันการโดนลบขณะสลับหน้าเว็บ
- **ระบบนำร่องไดเรกทอรีอัจฉริยะ (Directory Memory)**: ปุ่มเปิดเลือกโฟลเดอร์/ไฟล์ในหน้า อาวุธ, สกิน, ไอเทม และฟิสิกส์ จะจดจำไดเรกทอรีล่าสุด (Parent Directory Memory) และเมื่อเปิดอีกครั้งจะส่องไปในโฟลเดอร์แม่ทันที
- **เวิร์กสเปซระบบฟิสิกส์อัจฉริยะ (Smart Physics)**:
  * สร้าง [inspector.py (Physics)](file:///d:/heaven%20send/heaven_send_studio/app/core/physics/inspector.py) สแกนโมเดล อนิเมชั่น และ Attachable เพื่อวิเคราะห์ข้อต่อกระดูก (Bones Tree) และตรวจจับกลุ่มกระดูกที่มีความต่อเนื่องเป็นสายโซ่ (e.g. `hair_1` -> `hair_2`) ที่ตรงเกณฑ์ฟิสิกส์อัตโนมัติ
  * ออกแบบ UI [physics.js](file:///d:/heaven%20send/heaven_send_studio/web/js/pages/physics.js) ใหม่ทั้งหมด เพิ่ม Intake Card สำหรับเลือกไฟล์แอดออน/ไฟล์เดียวจบ, เพิ่มฟิลด์แก้ไขกลุ่มกระดูกที่ยืดหยุ่นแสดงผลแยกบรรทัด, และสร้างแผงค้นหารายชื่อกระดูกทั้งหมดในโมเดล (Model Bones Reference List) ที่กดคลิกเพื่อเอาคำใส่กล่องอินพุตได้ทันที
- **เวิร์กสเปซอาวุธและสกิลอัจฉริยะ (Smart Weapon & Skill)**:
  * สร้าง [inspector.py (Weapon)](file:///d:/heaven%20send/heaven_send_studio/app/core/weapon/inspector.py) สแกนหาไฟล์ไอเทม JSON ภายใน Behavior Pack อัตโนมัติ พร้อมเปิด Endpoint `/api/weapon/inspect`
  * อัปเดตหน้า [weapon.js](file:///d:/heaven%20send/heaven_send_studio/web/js/pages/weapon.js) ให้มี Intake Card เช่นเดียวกับหน้าฟิสิกส์ โดยเมื่อเลือกไฟล์แอดออน/โฟลเดอร์ จะเติมข้อมูลพาธ BP, RP และข้อมูลพาธไฟล์ไอเทมทั้ง 5 ชิ้นให้อัตโนมัติโดยสมบูรณ์
- **แก้บัคระบบย่อแอปพลิเคชัน (Borderless Window Minimize Fix)**: เพิ่มการตรวจจับอีเวนต์ `before_show` ใน [run.py](file:///d:/heaven%20send/heaven_send_studio/run.py) เพื่อฉีดสไตล์ระบบ `WS_MINIMIZEBOX` และ `WS_SYSMENU` เข้าไปใน Windows HWND ทำให้สามารถกดย่อหน้าต่าง (Minimize) ตัวแอปไร้ขอบ (Frameless) และคลิกกู้คืน (Restore) จาก Taskbar ได้อย่างสมบูรณ์แบบโดยหน้าต่างไม่ค้างหรือหายไป
- **การเปลี่ยนชื่อระบบอย่างสมบูรณ์ (Rebranding to Bright Studio)**:
  * เปลี่ยนชื่อแอปและแบรนด์ทั้งหมดจาก Heaven Send Studio ไปเป็น **Bright Studio**
  * อัปเดตการตั้งค่าใน [neutralino.config.json](file:///d:/heaven%20send/heaven_send_studio/neutralino.config.json), [run.py](file:///d:/heaven%20send/heaven_send_studio/run.py), และ [web/index.html](file:///d:/heaven%20send/heaven_send_studio/web/index.html)
  * ปรับโครงสร้างระบบบิลด์ [build.bat](file:///d:/heaven%20send/heaven_send_studio/build.bat) และ [ล้างระบบ.bat](file:///d:/heaven%20send/heaven_send_studio/%E0%B8%A5%E0%B9%8Dynamic%20%E0%B8%A3%E0%B8%B0%E0%B8%9A%E0%B8%9A.bat) เพื่อรวบรวมไฟล์เข้าสู่โฟลเดอร์บิลด์ปลายทาง `dist\bright-studio` โดยลบโปรเซสค้างและโฟลเดอร์ตัวเก่าออกทั้งหมดเรียบร้อย

### อัปเดต 2026-07-11 (รอบดึก) — "Script Lab" (Claude)
ระบบแก้ config อาวุธ/สกิลตัวใหม่ แยกไฟล์ทั้งหมด (แทน weaponcfg ในระยะยาว — weaponcfg เดิมยังอยู่):
- `app/core/scriptlab/parser.py` — **span-preserving JS parser** (tokenizer เขียนเอง ไม่มี dep ใหม่): จับ `const X = {...}` / `export const` ทุกก้อน + คอมเมนต์ไทยเป็น label + section header; **เขียนกลับแบบ splice เฉพาะ span ของค่า** → format/คอมเมนต์เดิมอยู่ครบ byte-identical (ต่างจาก tdcmodel ConfigParser เดิมที่ minify ทับทั้งก้อน). Tier 2 fallback สำหรับไฟล์ inline (ตัวเลข+คอมเมนต์). อ่าน/เขียนแบบ surrogateescape → BOM/CRLF รอด
- `app/core/scriptlab/analyzer.py` — สรุปไฟล์จาก docblock (ชื่อสกิลไทยขึ้น sidebar), kind (config/skill/main/util/inline), tag+unit heuristic (`*_ticks` → โชว์แปลงเป็นวินาทีสด)
- `app/api/scriptlab.py` — `/api/sl/open` (รับ .mcaddon/.zip/โฟลเดอร์ ผ่าน packio) · `/api/sl/parse` · `/api/sl/save` (mtime stale check → 409, สำรอง `.bak` ทุกครั้ง)
- `web/js/pages/scriptlab.js` + `web/css/scriptlab.css` + tab "Script Lab" ในโซนสกิล
- **Verified live**: Night_skills (11 ไฟล์, 136 fields), .mcaddon จริง, save round-trip บนสำเนาไฟล์จริง = แก้ค่าเดียว ที่เหลือ identical, stale → 409; UI ครบ (search/dirty/save counter/tick hint); pytest **22 passed**; exe rebuild แล้ว `/api/sl/*` = 200

### ค้างคา (ถ้าอยากทำต่อ)
1. **FM: ปุ่ม Deploy addon จาก store → เข้าโลก/com.mojang (C9)** — เชื่อม FM กับ tab โปรเจกต์ (มี `/api/projects/deploy` อยู่แล้ว) ให้ครบวงจร
2. **Cache/Backup tab ใน FM** — ผู้ใช้ไม่ได้เน้นรอบนี้ แต่ reference มี; ล้าง cache com.mojang ได้จะช่วยพื้นที่
3. **manifest name localization** — ตอนนี้ถ้าชื่อเป็น token (`pack.name`) fallback เป็นชื่อโฟลเดอร์. ถ้าจะโชว์ชื่อจริง ต้องอ่าน `texts/*.lang`

### เทคนิค — หนี้ที่ควรจ่าย
4. **ติดตั้ง httpx** เพื่อใช้ `fastapi.testclient.TestClient` (ตอนนี้ใช้ไม่ได้ ต้องยิง urllib) — ช่วยเขียน integration test ของ API ง่ายขึ้น

---

## 5. Verify checklist (ทำก่อน merge งานใหม่)
```
# 1. backend เขียว (รันเทสต์ทั้งหมด)
pytest

# 2. live server (ยิง HTTP จริง — อย่าเชื่อ app.routes)
py -3.12 -m uvicorn app.main:app --port 8777
#   -> GET /api/health, /api/fm/profiles, /api/fm/worlds?profile=0  ต้อง 200

# 3. desktop จริง
py -3.12 run.py   # เช็ค intro, ธีม, titlebar min/max/close, FM ครบ flow
```

Memory ของโปรเจกต์อยู่ที่ `.claude/projects/.../memory/` (มี note เรื่อง starlette gotcha).
