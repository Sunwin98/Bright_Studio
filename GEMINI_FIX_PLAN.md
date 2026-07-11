# GEMINI_FIX_PLAN — แก้บัครอบ Neutralino (ตรวจเมื่อ 2026-07-10)

> ต่อจาก [GEMINI_PLAN.md](GEMINI_PLAN.md). ตรวจงานแล้ว: ภาพครบ, โครง Neutralino ครบ, build ผ่าน, pytest เขียว (11 passed) — **แต่มีบัค 8 จุด เรียงตามความร้ายแรง แก้ตามลำดับ**.
> กติกาเดิมยังบังคับ: ห้ามเช็ค route จาก `app.routes` (ยิง HTTP จริง), ห้ามแตะ `app/core/`, ห้ามลบ `run.py`.

---

## ✅ สิ่งที่ทำไปแล้วและใช้ได้ (อย่าแตะซ้ำ)

- ภาพ 8 ไฟล์ใน `web/assets/` + ผูก CSS/HTML ครบ (bg, intro, empty state, mascot)
- โครง Neutralino: `neutralino.config.json`, `bin/`, `web/js/boot-neutralino.js`, `server.py`, `backend.spec`, `build.bat`, CORS ใน `app/main.py`
- `web/js/api.js` มี `API_BASE` + Neutralino dialog ใน `pickPath()`
- Part C: sound.js (SFX), mascot.js (ลาก+คลิกพูด), theme/CRT/skip-intro/SFX/BGM toggles ใน settings, `tests/conftest.py` (pytest เขียวหมด)
- pywebview fallback (`run.py`) ยังรันได้

---

## 🔴 BUG 1 (วิกฤต): backend.exe มีแค่ 2 route — ทุก tab ใช้ไม่ได้ในโปรแกรมจริง

**อาการ (ยืนยันจากการรัน `dist/heaven-send-studio/backend/backend.exe` จริง):**
- `/api/health` → 200 ✓ แต่ `/api/fm/profiles` → 404, `/api/projects` → 404, `/api/dialog` → 501 (อันนี้มี)

**สาเหตุ:** `app/main.py` โหลด router แบบ dynamic (`importlib.util.find_spec` + `__import__` ใน loop) — PyInstaller วิเคราะห์ static เท่านั้น เลย**ไม่ bundle** `app.api.projects/skin/physics/weapon/checker/merger/settings/knowledge/filemanager` และ `app.core.*` เข้า exe → `find_spec` คืน None → โดนข้ามเงียบๆ ทุกตัว. (`dialogs` รอดเพราะ import ตรง)

**วิธีแก้:** เพิ่ม hiddenimports ใน `backend.spec` ให้เก็บทั้งแพ็กเกจ `app`:
```python
# backend.spec (แก้ส่วน Analysis)
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['server.py'],
    ...
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on',
        *collect_submodules('app'),
    ],
    ...
)
```

**ทดสอบ (บังคับ ก่อนถือว่าแก้เสร็จ):**
```
dist\heaven-send-studio\backend\backend.exe --port 18921
curl http://127.0.0.1:18921/api/fm/profiles   → ต้อง 200 (ไม่ใช่ 404)
curl http://127.0.0.1:18921/api/projects      → ต้อง 200
taskkill /F /IM backend.exe
```

---

## 🔴 BUG 2 (วิกฤต): ปิดแอปแล้ว backend.exe ค้างใน Task Manager ทุกครั้ง

**สาเหตุ:** หน้าต่างเป็น borderless (ไม่มีปุ่ม OS) — ทางปิดเดียวคือปุ่ม `tb-close` ใน `web/js/app.js` ซึ่งเรียก `Neutralino.app.exit()` **ตรงๆ** ไม่ผ่าน handler `windowClose` ใน `boot-neutralino.js` → backend.exe ไม่ถูก kill กลายเป็น orphan process สะสมทุกครั้งที่เปิด-ปิด.

**วิธีแก้:** รวม logic ปิดเป็นฟังก์ชันเดียวใน `boot-neutralino.js` แล้ว expose:
```js
// boot-neutralino.js — แทน handler เดิม
window.hsShutdown = async () => {
  if (proc) {
    await Neutralino.os.updateSpawnedProcess(proc.id, "exit").catch(() => {});
    if (proc.pid) await Neutralino.os.execCommand(`taskkill /F /PID ${proc.pid} /T`).catch(() => {});
  }
  await Neutralino.app.exit();
};
Neutralino.events.on("windowClose", () => window.hsShutdown());
```
และใน `app.js` ปุ่ม close ฝั่ง Neutralino:
```js
document.getElementById("tb-close")?.addEventListener("click", () =>
  window.hsShutdown ? window.hsShutdown() : Neutralino.app.exit());
```
(สังเกต: guard `proc.pid` ด้วย — โค้ดเดิมมีเคส `taskkill /PID undefined`)

**ทดสอบ:** เปิดแอปจาก dist → ใช้งาน 1 tab → กด ✕ → เปิด Task Manager ต้อง**ไม่มี** `backend.exe` เหลือ. ทำซ้ำ 3 รอบ.

---

## 🟠 BUG 3 (สูง): icon ใน File Manager พังหมดเมื่อรันเป็นโปรแกรม

**สาเหตุ:** `web/js/pages/filemanager.js` บรรทัด ~16:
```js
function iconUrl(path) { return "/api/fm/icon?path=" + encodeURIComponent(path); }
```
ไม่ได้ prefix `API_BASE` → ในแอปจริง `<img src="/api/fm/icon...">` ยิงเข้า Neutralino static server (ไม่ใช่ backend) → 404 ทุกรูป. (fetch อื่นรอดเพราะผ่าน `api.get`)

**วิธีแก้:**
```js
import { api, el, API_BASE } from "../api.js";
function iconUrl(path) { return API_BASE + "/api/fm/icon?path=" + encodeURIComponent(path); }
```
แล้ว **grep ทั้ง `web/js/pages/`** หา `src="/api/` หรือ `"/api/` ที่ประกอบ URL ตรงๆ นอก `api.js` — เจอที่ไหน prefix `API_BASE` ให้หมด.

**ทดสอบ:** เปิดแอปจาก dist → tab จัดการไฟล์ → รูป pack_icon/world icon ต้องขึ้น (dev browser ก็ต้องยังขึ้น เพราะ `API_BASE` = "" ตอนไม่มี Neutralino).

---

## 🟠 BUG 4 (กลาง): `neu run` (โหมด dev) ค้าง 20 วิแล้ว fail เสมอ

**สาเหตุ:** `boot-neutralino.js` spawn `NL_PATH + "/backend/backend.exe"` — ตอน dev NL_PATH = repo root ซึ่งไม่มี `backend/backend.exe` → poll จนหมดเวลา → "Backend Start Failed".

**วิธีแก้:** ก่อน spawn ให้ลองต่อ dev server ที่ port 8777 ก่อน:
```js
// ใน boot-neutralino.js ก่อน spawn:
try {
  const dev = await fetch("http://127.0.0.1:8777/api/health");
  if (dev.ok) {
    window.HS_API_BASE = "http://127.0.0.1:8777";
    window.dispatchEvent(new Event("hs-backend-ready"));
    return;  // ไม่ spawn ไม่ kill (dev server เป็นของ dev เอง)
  }
} catch {}
// ...ค่อย spawn backend.exe ตามเดิม
```
(ต้องห่อทั้งบล็อกเป็น async IIFE เพราะใช้ await — ระวังให้ `HS_API_BASE` ถูกตั้ง**ก่อน** module `api.js` ถูก import; ถ้าจับลำดับไม่ได้ ให้เปลี่ยน `api.js` จาก const เป็น getter: `export const API_BASE = () => window.HS_API_BASE || ""` แล้วไล่แก้จุดใช้ — หรือง่ายสุด: ให้ `req()` อ่าน `window.HS_API_BASE` สดทุกครั้งแทน const)

**หมายเหตุสำคัญ:** ตอนนี้ `api.js` capture `API_BASE` ตอน import ซึ่ง**บังเอิญ**ทันเพราะ boot ตั้งค่า sync — แต่พอเพิ่ม await ใน BUG 4 จะไม่ทันแล้ว → **แนะนำแก้ `req()` ให้อ่าน `window.HS_API_BASE` สดทุกครั้ง** ปลอดภัยสุด:
```js
const base = () => window.HS_API_BASE || "";
const res = await fetch(base() + path, opts);
```

**ทดสอบ:** รัน `py -3.12 -m uvicorn app.main:app --port 8777` แล้ว `neu run` → แอปต้องใช้งานได้ทันทีไม่รอ 20 วิ.

---

## 🟡 BUG 5 (กลาง): build.bat เขียนทับ backend.spec ทุกครั้ง — แก้ spec แล้วสูญเปล่า

**สาเหตุ:** `build.bat` เรียก `PyInstaller server.py --name backend ...` (CLI mode) ซึ่ง **regenerate `backend.spec` ทับของเดิม** — พอแก้ BUG 1 ใน spec แล้วรัน build.bat จะโดนทับหาย.

**วิธีแก้:** ให้ build.bat ใช้ spec ตรงๆ:
```bat
py -3.12 -m PyInstaller backend.spec --noconfirm
```
และกัน dist ชนกันระหว่าง PyInstaller กับ neu: เพิ่ม `--distpath build_pyi` แล้ว xcopy จาก `build_pyi\backend`:
```bat
py -3.12 -m PyInstaller backend.spec --noconfirm --distpath build_pyi
call neu build --release
xcopy /E /I /Y build_pyi\backend dist\heaven-send-studio\backend
```

**ทดสอบ:** รัน `build.bat` 2 รอบติด → รอบสองต้องไม่พัง และ `backend.spec` เนื้อหาไม่เปลี่ยน (hiddenimports จาก BUG 1 ยังอยู่).

---

## 🟡 BUG 6 (เบา): toggle BGM เป็นปุ่มหลอก — ไม่มีไฟล์เสียง

`sound.js` สร้าง `new Audio()` เปล่า (`// We just mock it here`) → เปิด BGM แล้วเงียบ.

**วิธีแก้ (เลือกอย่างใดอย่างหนึ่ง):**
- หาเพลง lo-fi **CC0/public domain** (เช่นจาก freepd.com หรือ gen เอง) วางที่ `web/assets/bgm.mp3` แล้ว `bgm.src = "/assets/bgm.mp3";`
- หรือถ้าไม่มีไฟล์: ซ่อน toggle BGM ใน settings ไปก่อน (อย่าปล่อยปุ่มหลอกไว้)

---

## 🟡 BUG 7 (เบา): settings.json เขียนลง `_internal/` ตอนเป็น exe

`config.py` เขียน `SETTINGS_FILE = STUDIO_ROOT / "settings.json"` — ตอน frozen STUDIO_ROOT ชี้เข้า `dist\...\backend\_internal\` → ถ้า user ย้ายโปรแกรมไปที่ write-protected (Program Files) การ Save ตั้งค่าจะพัง + ตั้งค่าหายเวลาอัปเดตโปรแกรม.

**วิธีแก้** ใน `config.py`:
```python
import sys
if getattr(sys, "frozen", False):
    _cfg_dir = Path(_os.environ.get("APPDATA", str(STUDIO_ROOT))) / "HeavenSendStudio"
    _cfg_dir.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE = _cfg_dir / "settings.json"
else:
    SETTINGS_FILE = STUDIO_ROOT / "settings.json"
```

**ทดสอบ:** รัน exe → tab ตั้งค่า → Save → ต้องมี `%APPDATA%\HeavenSendStudio\settings.json` และค่าคงอยู่หลังปิด-เปิดใหม่.

---

## 🟡 BUG 8 (เบา): เช็คของแถม

- `boot-neutralino.js`: spawn ไม่เช็คว่า exe มีจริง — เพิ่ม `Neutralino.filesystem.getStats(exe)` ก่อน spawn, ถ้าไม่มีให้ dispatch `hs-backend-failed` ทันที (ไม่ต้องรอ 20 วิ) พร้อมข้อความบอกว่า "ไม่พบ backend/backend.exe — รัน build.bat ก่อน"
- `app.js` ตัวแปร `isMax` ใน `wireTitlebar()` ไม่ได้ใช้ในทาง Neutralino ปกติ (dead code ใน catch) — ลบได้
- หน้า `intro-logs` ตอน `hs-backend-failed`: ใช้ `.innerHTML +=` กับ id ที่อาจถูก `boot.remove()` ไปแล้วถ้า skip intro เปิดอยู่ → เช็ค null ก่อน

---

## ลำดับทำงาน + Definition of Done

1. แก้ BUG 1 → 5 (โค้ด) → รัน `build.bat` ใหม่ (**ทุกครั้งที่แก้ web/ ต้อง `neu build` ใหม่ด้วย** เพราะ UI ถูกอัดใน `resources.neu`)
2. แก้ BUG 6–8
3. Checklist สุดท้าย (ทำครบทุกข้อ):
   - [ ] `backend.exe --port X` → `/api/health`, `/api/projects`, `/api/fm/profiles`, `/api/fm/worlds?profile=0` = 200 ทั้งหมด
   - [ ] เปิดแอปจาก `dist/heaven-send-studio/heaven-send-studio-win_x64.exe` → ทุก tab โหลดได้, FM เห็นรูป icon
   - [ ] กด ✕ ปิดแอป 3 รอบ → Task Manager ไม่มี `backend.exe` ค้าง
   - [ ] `neu run` + dev uvicorn:8777 → ใช้ได้ทันที ไม่รอ 20 วิ
   - [ ] `run.py` (pywebview fallback) ยังเปิดได้
   - [ ] `py -3.12 -m pytest tests/ -q` → เขียวทั้งหมด
   - [ ] `build.bat` รันซ้ำได้ ไม่ทับ spec
4. อัปเดต [HANDOFF.md](HANDOFF.md): ติ๊กว่าบัคชุดนี้แก้แล้ว + ระบุอะไรยังเหลือจาก Part C (C1 world addon editor, C2 FM search, C8 auto-update, C9 deploy จาก FM — ยังไม่ได้ทำ)
