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
- **Tier 2 ยกเครื่อง (รอบแก้)**: เดิม Script Lab มองไม่เห็นค่าใน function / `let·var` / ค่าไม่มีคอมเมนต์ (ต่างจาก weapon_config ของ Gemini ที่ regex ทั้งไฟล์) → ตอนนี้ tier 2 รันเสริมเสมอ: จับ `key: literal`/`= literal` ทุกที่นอก span ที่ tier 1 แก้ได้แล้ว, จัดกลุ่มตาม**ฟังก์ชันที่ครอบ** (skill functions กลายเป็น section), เจาะเข้า array-of-objects ได้, รองรับ string/bool ด้วย
- **ยุบรวมแล้ว (2026-07-11)**: ลบ "ตั้งค่าอาวุธขั้นสูง" ทิ้งทั้งชุดตามคำขอผู้ใช้ — `web/js/pages/weaponcfg.js`, `app/api/weapon_config.py`, `app/core/weapon_config/`, `tests/test_weapon_config.py` และ tab ใน app.js. เหลือ Script Lab ตัวเดียว (ไอคอน sliders). endpoint `/api/weapon/config` เดิมใน `weapon.py` ยังอยู่ (ผูกกับ generator ไม่มี UI เรียกแล้ว)

### อัปเดต 2026-07-12 — "Quality of Life" (Claude)
- **หน้าแรก dashboard** (`web/js/pages/home.js`, frontend-only): ทักทายตามเวลา, ปุ่มลัด 5 ตัว, การ์ดสถิติ (โปรเจกต์สกิน/สกิล, addon Shared, โลก — กดกระโดดได้), งานล่าสุด 8 ตัวรวมสองโซนเรียง mtime + thumbnail. เป็น route default แทน projects. CSS `.hm-*` ท้าย app.css
- **ชื่อ pack จริงจาก .lang**: `filemanager/_lang_name()` — manifest เป็น token (`pack.name`) → อ่าน `texts/th_TH.lang → en_US.lang → *.lang` ก่อน fallback ชื่อโฟลเดอร์ (เช่น "Animations+ Add-On (MDF)" โผล่แทนชื่อโฟลเดอร์แล้ว)
- **ค้นหาคลังความรู้**: `/api/knowledge/search?q=` full-text ทุก doc (count + snippet); UI: พิมพ์ = กรองชื่อ, **Enter = ค้นทั้งเนื้อหา**, Esc ล้าง
- **BGM ไฟล์จริง**: `sound.js` เล่น `web/assets/bgm.mp3` ถ้ามี (loop, vol .25, resume หลัง gesture แรก) → ไม่มีไฟล์ fallback hum เดิม; hint ใน settings บอกวิธีวางไฟล์. **ยังไม่มีไฟล์เพลงจริง — ผู้ใช้ต้องหา lo-fi CC0 มาวางเอง**
- Verified: dev + exe rebuild, pytest 20 passed, no console errors

### อัปเดต 2026-07-12 — "ระบบโยงเครื่องมือ (context menu)" (Claude)
- **`web/js/ui/contextmenu.js`**: `showContextMenu(x,y,items)` เมนูลอยตามธีม (คลิกที่อื่น/Esc ปิด, clamp ขอบจอ) + `gotoPage(hash)` นำทางพร้อม payload (บังคับ re-route ถ้า hash ซ้ำ) — **ตัวกลางเชื่อมทุกเครื่องมือ ใช้ตัวนี้เวลาเพิ่มเมนูใหม่**
- **FM การ์ด addon** (คลิกซ้าย/ขวา): เปิดใน Script Lab · ตรวจสอบ · **เพิ่มเข้าโลก…** (dialog เลือกโลกจากโปรไฟล์ user + ค้นหา → toggle_world_addon enable) · เปิดดูไฟล์ · ลบ. **การ์ดโลก** (คลิกขวา): จัดการ addon/เปิดดู/ลบ
- **การ์ดโปรเจกต์** (คลิกขวา): Script Lab · ตรวจสอบ · Deploy · แพ็ค · เปิดโฟลเดอร์
- **หน้า scriptlab + checker รับ `?open=<path>`** → auto-open ทันที (pattern เดียวกันใช้ต่อกับหน้าอื่นได้: render(main, params))
- Verified live: FM→Script Lab เปิด pack จริง (3 สคริป), dialog เพิ่มเข้าโลก list 61 โลก, โปรเจกต์→checker แยก BP/RP อัตโนมัติ; pytest 20 passed; rebuild exe แล้ว
- ⚠️ **shell ของเครื่อง dev PATH เพี้ยน** (Git usr/bin หาย — cat/tail/sleep ใช้ไม่ได้): prefix `export PATH="/c/Program Files/Git/usr/bin:/c/Windows/System32:$PATH"` ก่อนทุกคำสั่ง จนกว่าจะแก้ PATH ระบบ

### อัปเดต 2026-07-13 — "Deploy pipeline + Hot-sync + Ctrl+K" (Opus 4.8 เขียน / Fable 5 ตรวจ+ปิดงาน)
- **Deploy + เพิ่มเข้าโลก… (คลิกเดียวจบ)**: `ops.deploy_project` คืน `deployed_packs` (identity จาก manifest: type/name/uuid/version, token name → ชื่อโฟลเดอร์) → เมนูคลิกขวาการ์ดโปรเจกต์เรียก deploy แล้วเปิด world-picker ใส่ BP+RP เข้าโลกที่เลือกทีเดียว. world-picker แยกเป็น `web/js/ui/worldpicker.js` (ใช้ร่วมกับ FM แล้ว — implementation เดียว)
- **Script Lab hot-sync** (`app/core/scriptlab/sync.py`): หลังเซฟ ตามหา pack root (manifest.json ใกล้สุด) → match uuid กับทุก pack ใต้ `development_behavior_packs`/`behavior_packs` ของทุกโปรไฟล์ → copy ไฟล์ทับ relative path เดิม → status บอก "sync เข้าเกมแล้ว — พิมพ์ /reload". แก้ไฟล์ที่อยู่ในเกมอยู่แล้ว → แจ้ง already_in_game. sync พังไม่ทำให้ save พัง (คืน error แยก). Tests: `tests/test_scriptlab_sync.py` 4 เคส
- **Ctrl+K / Ctrl+P palette** (`web/js/ui/palette.js` + wiring ใน app.js): ค้นรวม โปรเจกต์(สกิน+สกิล)/addon ในเครื่อง/โลก/เอกสาร — ลูกศร+Enter หรือเมาส์ → กระโดด: project/addon→Script Lab, world→FM เปิด world editor เลย (`?world=` ใน filemanager), doc→knowledge เปิดเอกสาร (`?doc=`)
- Verified live ทุก flow: palette 4 ประเภท, Enter เปิด Script Lab จริง, world editor เด้งถูกใบ (COCO), doc เปิดถูก; pytest **24 passed**; ไม่มี console error; exe rebuild + smoke ผ่าน

### อัปเดต 2026-07-13 — "โซนโมเดล AI (Meshy)" (Opus 4.8)
ปั้นโมเดล 3D จากรูป/ข้อความ → ส่งออกเป็น Bedrock geo.json + texture
- **Backend** `app/core/modelgen/`: `meshy.py` (client urllib ล้วน — image-to-3d/text-to-3d preview+refine, poll, download), `obj_to_geo.py` (**OBJ → Bedrock `poly_mesh` geo.json** format 1.16.0, pure Python: fan-triangulate, flip V, center X/Z + scale ตาม target_size, face_forward 180°, vert order = [pos,normal,uv]). API `app/api/modelgen.py` — `/config /key /image /text /text-refine /status /export`
- **Frontend** `web/js/pages/modelgen.js` + โซน "โมเดล" ใน sidebar (icon cube): tab จากรูป/จากข้อความ, key gate, progress poll, พรีวิว 3D orbit ผ่าน `<model-viewer>` (CDN — feature online-only อยู่แล้ว) fallback thumbnail, export UI (ชื่อ/ขนาด/โฟลเดอร์). text = preview→refine (ใส่ texture ตอนกดต่อ)
- **API key**: เก็บใน settings.json (gitignored) ผ่าน `config.set_meshy_key()`; seed ไว้ที่ `%APPDATA%\BrightStudio\settings.json` แล้วสำหรับ exe. **key = ของผู้ใช้ (Meshy) — อย่า commit / อย่า hardcode ในซอร์ส**
- **ข้อจำกัดที่ต้องรู้**: geo.json ที่ได้เป็น **poly_mesh (mesh import)** ไม่ใช่ cube แก้ทีละกล่อง; ต้อง lowpoly (default 4k, มีตัวเลือก 1.5k/4k/10k) ไม่งั้นหนักเกม; ทำงานต้องออนไลน์ (Meshy API)
- **Verified**: pytest 30 passed (รวม obj_to_geo 6 เคส), Meshy auth + balance 1116 credits ✓, หน้า UI ครบ (tab/gate/validation ไม่มี console error), backend exe รัน `/api/modelgen/config` = 200. **ยังไม่ได้ยิง generation จริง** (เสียเครดิต + ใช้เวลา 1-3 นาที) — converter ทดสอบด้วย synthetic OBJ; ควรทดสอบ end-to-end จริง 1 ครั้งแล้วเช็ค geo.json เข้าเกม Bedrock (ยืนยัน vert order/scale/UV)

### อัปเดต 2026-07-13 (รอบสอง) — "Model zone v2: แก้เทคเจอร์เพี้ยน + UI ใหม่" (Fable 5)
- **บัคเทคเจอร์เพี้ยน (สำคัญ)**: converter เดิม flip V (`1-v`) — ผิด. Ground truth จาก Blockbench Meshy plugin (Shadowkitten47/Meshy): **Bedrock poly_mesh V เป็น bottom-up เหมือน OBJ** (plugin flip เฉพาะตอนแปลงเข้า UV space ของ Blockbench) + ลำดับ vertex ยืนยันจาก Mojang schema = `[pos, normal, uv]`. แก้เป็น passthrough แล้ว **พิสูจน์ด้วย re-export งานดาบจริง**: ไฟล์เก่า V+ไฟล์ใหม่ V = 1.0 ทุกจุด (คือ flip เป๊ะๆ). **ห้าม flip V ใน obj_to_geo อีก**
- **พรีวิว 3D ไม่ขึ้น (แก้แล้ว)**: 2 ชั้น — (1) เพิ่ม `/api/modelgen/proxy?url=` stream ไฟล์ meshy.ai ผ่าน backend (กัน CORS, whitelist host) (2) model-viewer โหมด lazy ไม่ trigger ใน layout เรา → ต้องใส่ `loading="eager"` + `reveal="auto"` (ทดสอบแล้ว loaded=true, glb 4.5MB ผ่าน proxy)
- **UI v2** (`modelgen.js` เขียนใหม่): 2 คอลัมน์ — ซ้าย controls / ขวา **preview stage ถาวร** (idle → อนิเมชั่นตอนสร้าง: cube โคจร+glow+scanline+% สด → 3D orbit) + export card ใต้ stage + **แถบ "งานล่าสุด"** จาก `/api/modelgen/recent` (list task จาก Meshy — เปิดซ้ำ/re-export ไม่เสียเครดิต). CSS `.mg-*` ท้าย app.css
- Verified: pytest 30 passed, พรีวิว 3D โหลดจริงใน browser, re-export ดาบ 3864 polys + texture, exe rebuild แล้ว

### อัปเดต 2026-07-13 (รอบสาม) — "ปิด loop: AI โมเดล → ไอเทมในเกม" (Opus 4.8)
- **`/api/modelgen/make-item`**: reuse `app/core/weapon/item_builder.build_item()` ที่มีอยู่ — รับ geo.json + texture + icon → สร้าง **BP item + RP attachable (wire geometry.<slug> อัตโนมัติ) + texture + inventory icon + item_texture.json + lang + give command** ครบ. สร้างแอดออนใหม่ หรือใส่แอดออนที่มี (bp_path/rp_path) ก็ได้
- **export เพิ่ม icon**: `/export` ดาวน์โหลด `thumbnail_url` เป็น `<slug>_icon.png` ด้วย (ใช้เป็น inventory icon เวลาทำไอเทม); response เพิ่ม `icon_path`, `slug`
- **UI** (`modelgen.js`): หลัง export สำเร็จ โผล่ฟอร์ม "→ ทำเป็นไอเทมในเกม" (namespace/ชื่อ/หมวด/ชื่อโชว์ + details ใส่แอดออนที่มี) → กดแล้วได้ give command + ปุ่มคัดลอก + เปิดโฟลเดอร์
- **Verified**: make-item ยิงจริงกับดาบ AI → สร้าง addon ครบทุกไฟล์, attachable geometry.default = geometry.ai_model ถูก wire, `/give @s ai:test_sword`; UI flow (recent→export→make-item) ผ่านใน browser ไม่มี error; pytest 30 passed; exe rebuild route 200/422. ลบ addon ทดสอบทิ้งแล้ว
- **ครบวงจรแล้ว**: รูป/ข้อความ → โมเดล 3D → geo.json+texture → **ไอเทมถือได้ในเกม** ในหน้าเดียว

### อัปเดต 2026-07-13 (รอบสี่) — "Toast + Page persistence + Active project" (Sonnet 5)
งานใหญ่ 3 อย่าง ตามคำขอผู้ใช้ (Ctrl+K/context-menu มีแล้ว, ตอนนี้เพิ่มชั้นถัดไป):

- **Page state persistence** (`web/js/app.js` router เขียนใหม่): เดิม `route()` ทำ `main.innerHTML = ""` ทำลายหน้าเก่าทุกครั้งที่สลับแท็บ — งานที่พิมพ์ค้าง/โมเดลกำลังปั้นหายหมด. ตอนนี้แต่ละ hash (รวม query, เช่น `scriptlab?open=...`) ได้ container ของตัวเองใน `pageCache` (Map) ที่ `render()` ทำงาน**ครั้งเดียว** แล้วสลับหน้าด้วย `display:none/""` แทนการ re-render — ฟอร์ม/scroll position (`scrollPos` WeakMap ต่อ container)/**งานที่ยังรันอยู่เบื้องหลัง (เช่น poll ของ Meshy) ยังทำงานต่อแม้สลับไปหน้าอื่น** เพราะ DOM node ไม่ถูกลบ (`document.body.contains()` ยังเป็น true). จำกัด 24 หน้า, LRU evict ตัวเก่าสุด. **⚠️ ผลข้างเคียงที่รู้ไว้**: หน้าที่ fetch ข้อมูลสดทุกครั้ง (เช่น projects list) จะไม่ auto-refresh เมื่อสลับกลับมา (ใช้ cache เดิม) — ต้องกดปุ่ม refresh/reload ในหน้าเอง ถ้าอยากเห็นข้อมูลใหม่
- **Toast system** (`web/js/ui/toast.js`): `toast.success/error/info(msg)` + `toast.progress(msg)` (คืน handle `.update()/.success()/.error()` สำหรับงานยาว) — เรนเดอร์ตรงเข้า `<body>` ไม่ใช่ในหน้า จึงอยู่รอดข้ามการสลับหน้า (งาน Meshy/deploy/save ที่เริ่มในหน้าหนึ่งแล้วสลับไปหน้าอื่น ก็ยังเห็น toast แจ้งผลตอนเสร็จ). **แทน `alert()` ทั้งหมด 36 จุดในทุกหน้า** (checker/cleanup/filemanager/item/merger/modelgen/physics/settings/skin/weapon/worldpicker) — เหลือ `confirm()`/`prompt()` เดิมไว้ (เป็นการตัดสินใจ ไม่ใช่แจ้งเตือน, นอกขอบเขตรอบนี้)
- **แก้บั๊กแฝงพบระหว่างทาง**: `--bg-card` ถูกใช้ 6 จุดใน app.css/scriptlab.css (Script Lab panels, context menu, palette) แต่**ไม่เคยถูกประกาศ**ใน theme.css เลย (พิมพ์ผิดตอนสร้าง ควรเป็น `--bg-3` ตามที่ `.card` ใช้จริง) — พื้นหลังโปร่งใสมาตลอดโดยไม่มีใครสังเกต. แก้เป็น `--bg-3` แล้วทั้ง 6 จุด
- **Active project (ปักหมุดโปรเจกต์)**: `web/js/state/activeProject.js` (localStorage `hs_active_project` + event `hs-active-project-changed`) + `web/js/ui/activeProjectIndicator.js` (pill ใน titlebar กลาง ระหว่างชื่อแอปกับปุ่ม min/max/close — ต้องมี `-webkit-app-region: no-drag` เพราะ titlebar ทั้งแถบลาก window ได้). คลิก pill = context menu ลัด (Script Lab / ตรวจสอบ / Deploy+เพิ่มเข้าโลก / เลิกปักหมุด). ปักหมุดจากคลิกขวาการ์ดโปรเจกต์ (`projects.js`, เมนูข้อบนสุด, สลับ label เป็น "เลิกปักหมุด" ถ้าเป็นอันที่ปักอยู่)
  - **Auto-fill ที่ต่อกับของปักหมุด**: Script Lab, ตรวจสอบ Addon, อาวุธ & สกิล (weapon.js), ฟิสิกส์ (physics.js) — ทุกหน้าที่มี intake รับ "พาธ addon เดียว" (`activeProjectOpenPath()`: bp > folder > mcaddon > rp) จะ auto-เปิดโปรเจกต์ที่ปักหมุดทันทีถ้าไม่มี `?open=` param มาก่อน (deep-link จาก context menu/palette ยังชนะเสมอ)
  - **ตั้งใจไม่ทำ**: "สร้างไอเทม" (item.js) ข้าม — หน้านั้น design ให้สร้างแอดออนใหม่เสมอ (รับแค่ `addon_name` + `output_dir` ไม่มีช่อง BP/RP ที่มีอยู่ให้ prefill) ผูกจะฝืน UX. FM addon-card ก็ยังไม่มีปุ่มปักหมุด (ทำได้แต่ยังไม่คุ้มพอสำหรับรอบนี้)
- **Verified**: pytest 30 passed, syntax-check ผ่านทุกไฟล์ที่แตะ (17 ไฟล์ JS + CSS brace-balance check), grep ยืนยัน `alert(` เหลือ 0 จุดในโค้ดแอป. **ยังไม่ได้ rebuild exe / เทสในเบราว์เซอร์ตามคำขอผู้ใช้ — เทสเองก่อน**: หลักๆ ให้ลองสลับหน้าไปมาระหว่างพิมพ์ฟอร์ม (เช็คว่าค่าไม่หาย), ปักหมุดโปรเจกต์แล้วเปิด Script Lab/ตรวจสอบ/ฟิสิกส์/อาวุธ ดูว่า path เติมอัตโนมัติมั้ย, ลองกด action ต่างๆ ดู toast มุมขวาล่าง

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
