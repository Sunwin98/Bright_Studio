# GEMINI_PLAN — Heaven Send Studio: สร้างภาพธีม + อัปเกรดเป็นโปรแกรม Neutralino

> เอกสารสั่งงานสำหรับ **Gemini** (หรือ AI ตัวถัดไป) — อ่านไฟล์นี้ + [HANDOFF.md](HANDOFF.md) แล้วทำงานได้เลยโดยไม่ต้องถามกลับ
> งานมี 3 ส่วน: **A) สร้างภาพ assets** · **B) แปลงเป็นโปรแกรม Neutralino standalone** · **C) อัปเกรดให้ดีกว่าเดิม**

---

## 0. ภาพรวมโปรเจกต์ + กติกา (อ่านก่อนแตะโค้ด)

**Heaven Send Studio** = เครื่องมือทำ Minecraft Bedrock addon ของร้าน Heaven Send
- Backend: **Python FastAPI** (`app/api/` = router บาง, `app/core/` = logic จริง) เสิร์ฟ SPA จาก `web/`
- Frontend: **vanilla JS ไม่มี build tool** — page module ที่ `web/js/pages/<id>.js` export `render(main)`, เพิ่ม tab ใน `TABS` ที่ `web/js/app.js`, helper กลาง `el()` / `api.get/post` / `pickSingle()` ที่ `web/js/api.js`
- ธีมปัจจุบัน: **"Neon Yokochō"** (retro-pixel ญี่ปุ่นกลางคืน ชิลๆ) — tokens ที่ `web/css/theme.css`, โครงที่ `web/css/app.css`
- ตอนนี้รันผ่าน `run.py` (pywebview) — **เป้าหมายคือเป็น standalone exe แบบโปรเจกต์อ้างอิง** `D:\Project Addon\Project Addon` (Neutralino.js)

### กติกาเหล็ก
1. **ห้ามเปลี่ยนชื่อ CSS class เดิม** — ทุกหน้าพึ่ง `.card .btn-primary .grid .log-box` ฯลฯ
2. **ห้ามแก้ logic ใน `app/core/`** — เป็นเครื่องมือที่ใช้งานจริงอยู่ ถ้าไม่จำเป็นอย่าแตะ
3. **ห้ามลบเส้นทาง pywebview (`run.py`)** จนกว่า Neutralino build จะรันผ่านครบ — เก็บไว้เป็น fallback
4. **Gotcha สำคัญ:** โปรเจกต์นี้มี starlette เวอร์ชันที่ `app.routes` introspect แล้วไม่เห็น router ที่ include — **ห้ามเช็คว่า route ลงทะเบียนจาก `app.routes` เด็ดขาด ให้รัน server แล้วยิง HTTP จริง**
5. **ห้ามเอาไฟล์ภาพ/เสียงจาก `D:\Project Addon` มาใช้** — เป็นงานของร้านอื่น ให้ gen ใหม่ทั้งหมด (ดู Part A)
6. Python ที่มี deps: `py -3.12` · dev server: `py -3.12 -m uvicorn app.main:app --port 8777`

---

## Part A — สร้างภาพ Assets (Gemini image generation)

สร้างโฟลเดอร์ `web/assets/` แล้ว gen ภาพตามตาราง. ทุก prompt ใช้ **STYLE BLOCK** ร่วมกันนี้ต่อท้ายเสมอ:

```
STYLE BLOCK:
32-bit pixel art, Japanese city street at night, chill lo-fi hip-hop mood,
deep indigo-navy sky (base color #0d1026), glowing neon signs in pink (#ff6ec7),
cyan (#5ce1e6) and purple (#a78bfa), warm paper lanterns, soft rain reflections
on wet pavement, gentle dithering, cozy and calm (NOT aggressive cyberpunk),
crisp pixel edges, no photorealism, no text unless specified
```

| # | ไฟล์ปลายทาง | ขนาด | พื้นหลัง | ใช้ทำอะไร |
|---|---|---|---|---|
| 1 | `web/assets/icons/appIcon.png` | 512×512 | ทึบ | ไอคอนโปรแกรม (ทำ `.ico` ด้วย) |
| 2 | `web/assets/cover.png` | 1024×1024 | **โปร่งใส** | โลโก้/ภาพหลัก intro + sidebar |
| 3 | `web/assets/mascot_idle.png` | 512×768 | **โปร่งใส** | มาสคอตท่าปกติ |
| 4 | `web/assets/mascot_happy.png` | 512×768 | **โปร่งใส** | มาสคอตท่าดีใจ |
| 5 | `web/assets/mascot_angry.png` | 512×768 | **โปร่งใส** | มาสคอตท่าโกรธ/error |
| 6 | `web/assets/bg_night_city.png` | 1920×1080 | ทึบ | พื้นหลัง main (ต้องมืดจาง ไม่แย่ง UI) |
| 7 | `web/assets/bg_intro.png` | 1600×900 | ทึบ | ฉาก intro boot |
| 8 | `web/assets/empty_state.png` | 512×512 | **โปร่งใส** | ภาพตอนไม่พบข้อมูล |

### Prompts (copy ใช้ได้เลย — ต่อท้ายด้วย STYLE BLOCK ทุกครั้ง)

**1. App icon** — `appIcon.png` (แล้วแปลงเป็น `icons/appIcon.ico`)
```
App icon, square 1:1. A glowing neon storefront sign shaped like a winged
letter "HS" (Heaven Send), hanging over a tiny pixel-art Japanese shop front
at night, framed inside a rounded-square dark indigo tile. Bold, readable
at small sizes. + STYLE BLOCK
```

**2. Cover / logo art** — `cover.png` (โปร่งใส)
```
Game logo emblem on transparent background. Neon sign lettering "HEAVEN SEND"
in pixel font, pink and cyan glow, small katakana subtitle "ヘブンセンド" beneath,
decorated with a tiny pixel angel wing and a paper lantern. Isolated object,
transparent background, PNG. + STYLE BLOCK
```

**3–5. Mascot 3 ท่า** — โปร่งใส, ตัวละครเดียวกันทั้ง 3 ภาพ (gen ต่อเนื่องใน chat เดียวเพื่อคุมหน้าตา)
```
Full-body chibi pixel-art mascot girl, shop-keeper of a night-market addon
studio: short dark-indigo hair with a glowing cyan hairpin, oversized pastel
hoodie with a small angel-wing logo, headphones around neck.
Pose: {idle / relaxed standing, gentle smile}. Isolated character,
transparent background, PNG, clean silhouette. + STYLE BLOCK
```
- ภาพ 4: เปลี่ยน Pose เป็น `happy / jumping cheerfully, eyes closed smiling, sparkles`
- ภาพ 5: เปลี่ยน Pose เป็น `angry / puffed cheeks, hands on hips, small red anger mark`

**6. พื้นหลัง main** — `bg_night_city.png` (สำคัญ: ต้อง**มืดและจาง** ใช้เป็น backdrop ใต้ UI)
```
Wide 16:9 background, very dark and subtle: a quiet Japanese alley (yokochō)
at night seen from street level, distant neon signs softly glowing, telephone
poles and cables, a vending machine light, light rain. Overall brightness LOW
(image will sit behind a UI at ~15% opacity), no focal character, no text.
+ STYLE BLOCK
```

**7. Intro boot art** — `bg_intro.png`
```
Wide 16:9 hero scene: the mascot girl from behind, standing under a glowing
neon shop gate "天送" (Heaven Send), rain-slick street reflecting pink and cyan
neon, night sky with tiny pixel stars. Cinematic but cozy. + STYLE BLOCK
```

**8. Empty state** — `empty_state.png` (โปร่งใส)
```
Small illustration, transparent background: a cardboard box with a sleepy
pixel cat inside, one paper lantern glowing above, symbolizing "nothing found
here". Cute, minimal, isolated object. + STYLE BLOCK
```

### หลัง gen เสร็จ
- วางไฟล์ตาม path ในตาราง → แก้ CSS/HTML ให้ใช้: intro ใช้ `bg_intro.png` + `cover.png`, `#main` ใส่ `bg_night_city.png` (opacity ต่ำผ่าน `::before`), empty-state ใน `.empty` ใช้ `empty_state.png`
- mascot ยังไม่ต้องผูก logic — เก็บไว้ให้ Part C ข้อ mascot

---

## Part B — แปลงเป็นโปรแกรม Neutralino (standalone, ดับเบิลคลิกรันได้)

### สถาปัตยกรรม hybrid (ตัดสินใจแล้ว — ทำตามนี้)
ตัวอ้างอิงเป็น JS ล้วน แต่ของเรามี Python core หนัก (skin_factory, physics, merger, checker) — **ไม่ย้ายเป็น JS**. ใช้:

```
[Neutralino window (UI จาก resources/)] ──HTTP──> [backend.exe (FastAPI, PyInstaller)]
        │ spawnProcess ตอนเปิด / kill ตอนปิด              127.0.0.1:<random port>
```

### ขั้นตอน (เรียงลำดับ ทำทีละข้อ)

**B1. เตรียม backend ให้รับ `--port`** — สร้าง `server.py` (entry ใหม่ ข้างๆ `run.py`):
```python
"""Headless server entry for the packaged app (no pywebview)."""
import argparse
import uvicorn
from app.main import app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
```

**B2. เปิด CORS localhost** ใน `app/main.py` (UI จะมาจาก origin ของ Neutralino):
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"], allow_headers=["*"],
)
```

**B3. `web/js/api.js` — เพิ่ม API_BASE:**
```js
export const API_BASE = window.HS_API_BASE || "";   // ตั้งโดย neutralino bootstrap
async function req(method, path, body) {
  // เปลี่ยน fetch(path, ...) เป็น fetch(API_BASE + path, ...)
```
และใน `pickPath()` เช็ค Neutralino ก่อน:
```js
if (window.Neutralino) {
  if (mode === "folder") { const d = await Neutralino.os.showFolderDialog("เลือกโฟลเดอร์"); return d ? [d] : []; }
  const f = await Neutralino.os.showOpenDialog("เลือกไฟล์", { multiSelections: mode === "open_files" });
  return f || [];
}
// เดิม: fallback POST /api/dialog (pywebview / browser dev)
```

**B4. ปุ่ม titlebar** ใน `web/js/app.js` — feature-detect 2 ชั้น: `window.Neutralino` → `Neutralino.window.minimize()/maximize()·unmaximize()/ close ผ่าน Neutralino.app.exit()`; ไม่มีก็ลอง `window.pywebview.api.*`; ไม่มีทั้งคู่ (browser) → ซ่อนปุ่ม (พฤติกรรมเดิม)

**B5. ติดตั้งโครง Neutralino** ที่ repo root:
```
npm i -g @neutralinojs/neu
neu update   # ดึง binaries ลง bin/
```
สร้าง `neutralino.config.json` (อิงค่าจากตัวอ้างอิง ปรับของเรา):
```json
{
  "applicationId": "th.heavensend.studio",
  "version": "2.0.0",
  "defaultMode": "window",
  "port": 0,
  "documentRoot": "/web/",
  "url": "/",
  "enableServer": true,
  "enableNativeAPI": true,
  "tokenSecurity": "one-time",
  "nativeAllowList": ["app.*", "os.*", "filesystem.*", "window.*", "events.*"],
  "modes": { "window": {
    "title": "Heaven Send Studio", "width": 1280, "height": 800,
    "minWidth": 960, "minHeight": 640, "center": true,
    "borderless": true, "resizable": true,
    "icon": "/web/assets/icons/appIcon.png", "enableInspector": false
  }},
  "cli": {
    "binaryName": "heaven-send-studio", "resourcesPath": "/web/",
    "extensionsPath": "/extensions/", "clientLibrary": "/web/js/neutralino.js",
    "binaryVersion": "5.5.0", "clientVersion": "5.4.0"
  }
}
```
หมายเหตุ: ใช้ `web/` เป็น resources ตรงๆ (ไม่ต้อง rename เป็น `resources/`) — ชี้ผ่าน `documentRoot`/`resourcesPath` แบบข้างบน. เพิ่ม `<script src="js/neutralino.js"></script>` ใน `web/index.html` (ก่อน `app.js`).

**B6. Bootstrap spawn backend** — สร้าง `web/js/boot-neutralino.js` โหลดก่อน `app.js`:
```js
// รันเฉพาะใน Neutralino: spawn backend.exe แล้วตั้ง HS_API_BASE
if (window.Neutralino) {
  Neutralino.init();
  const port = 20000 + Math.floor(Math.random() * 20000);
  window.HS_API_BASE = `http://127.0.0.1:${port}`;
  let proc = null;
  const exe = NL_PATH + "/backend/backend.exe";
  Neutralino.os.spawnProcess(`"${exe}" --port ${port}`).then(p => proc = p);
  // poll health สูงสุด ~20s ก่อนปล่อย app.js ทำงานต่อ (app.js รอ event 'hs-backend-ready')
  const t0 = Date.now();
  (async function poll() {
    try { const r = await fetch(window.HS_API_BASE + "/api/health"); if (r.ok) return dispatchEvent(new Event("hs-backend-ready")); } catch {}
    if (Date.now() - t0 < 20000) setTimeout(poll, 300); else dispatchEvent(new Event("hs-backend-failed"));
  })();
  Neutralino.events.on("windowClose", async () => {
    if (proc) await Neutralino.os.updateSpawnedProcess(proc.id, "exit").catch(() => {});
    await Neutralino.os.execCommand(`taskkill /F /PID ${proc?.pid} /T`).catch(() => {});
    Neutralino.app.exit();
  });
}
```
`app.js`: ถ้า `window.Neutralino` ให้รอ `hs-backend-ready` ก่อน `route()/checkConn()` (intro boot overlay กลบช่วงรอพอดี — ใช้ประโยชน์จากของที่มีแล้ว)

**B7. PyInstaller** — เพิ่ม dev-dep `pyinstaller`, สร้าง spec/คำสั่ง:
```
py -3.12 -m PyInstaller server.py --name backend --onedir --noconsole ^
  --add-data "web;web" --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.lifespan.on
```
เช็คว่า `config.py` resolve path แบบ frozen ได้ (`sys._MEIPASS` ไม่จำเป็นเพราะ `--onedir` + `WEB_DIR` ยังใช้ relative ได้ แต่**ต้องทดสอบ**; `settings.json` ควรย้ายไปเขียนที่ `%APPDATA%/HeavenSendStudio/` ตอน frozen — เช็ค `getattr(sys, "frozen", False)`)

**B8. `build.bat`** ที่ repo root:
```bat
@echo off
py -3.12 -m PyInstaller ... (ตาม B7)
call neu build --release
xcopy /E /I /Y dist\backend dist\heaven-send-studio\backend
echo Done: dist\heaven-send-studio\
```
ผลลัพธ์ `dist/heaven-send-studio/` = `heaven-send-studio-win_x64.exe` + `resources.neu` + `backend/` → zip แจกได้

### ลำดับทดสอบ Part B
1. `neu run` (dev, backend รันแยกด้วย uvicorn ก่อน) → UI ขึ้น, ปุ่ม window ทำงาน
2. `neu run` แบบ spawn backend.exe จริง → FM/ทุก tab ใช้ได้
3. `build.bat` → ไปรันบนเครื่อง (หรือ folder) ที่ไม่มี Python → ทุกอย่างครบ
4. ปิดหน้าต่าง → เช็ค Task Manager ว่า `backend.exe` ตายจริง (จุดพลาดบ่อยสุดของสถาปัตยกรรมนี้)

---

## Part C — อัปเกรดให้ดีกว่าเดิม + ดีกว่าตัวอ้างอิง

ตัวอ้างอิงจุดอ่อน (เห็นจากโค้ดจริง): inline style เต็ม HTML, logic กองใน `main.js` 2,100 บรรทัด, ไม่มี test, ไม่มี settings persist ที่ดี. **ของเราโครงดีกว่าอยู่แล้ว — คงไว้** (core+api แยก, page modules, tests) แล้วเพิ่มตามนี้ เรียง priority:

| # | งาน | รายละเอียด | ไฟล์เกี่ยวข้อง |
|---|---|---|---|
| C1 | **World addon editor** (เหนือกว่าอ้างอิง) | ใน FM world drill-in: toggle เปิด/ปิด pack ในโลกได้จริง (แก้ `world_behavior_packs.json`/`world_resource_packs.json` — backup ก่อนเขียนทุกครั้ง) | `app/core/filemanager/`, `app/api/filemanager.py`, `web/js/pages/filemanager.js` |
| C2 | **FM search/filter** | ช่องค้นหา + กรอง BP/RP + sort ตามชื่อ/ขนาด | `web/js/pages/filemanager.js` |
| C3 | **SFX/BGM แบบมี toggle** | เสียง hover/click เบาๆ + BGM lo-fi loop (gen หรือหา CC0) ปิดได้ใน settings — อ้างอิงมีแต่ปิดไม่ได้ถาวร | `web/js/sound.js` (ใหม่), `web/js/pages/settings.js` |
| C4 | **Mascot ลากได้ + คลิกพูด** | ใช้ mascot 3 ท่าจาก Part A, มีประโยคสุ่ม + เปลี่ยนท่าตามสถานะ (build สำเร็จ→happy, error→angry) | `web/js/mascot.js` (ใหม่) |
| C5 | **Theme toggle** | Night (default) / Day + สวิตช์ปิด CRT scanline — theme.css คุมด้วย vars อยู่แล้ว ทำง่าย | `web/css/theme.css`, `web/js/pages/settings.js` |
| C6 | **Skip intro setting** | ปิด intro boot ได้ (persist ใน settings.json) | `web/js/app.js`, settings |
| C7 | **conftest.py** | alias fixture `tmp = tmp_path` ให้ `pytest tests/` เขียวทั้งชุด (ตอนนี้ test เก่า 3 ไฟล์รันเป็น script เท่านั้น) | `tests/conftest.py` (ใหม่) |
| C8 | **Auto-update check** | เช็คเวอร์ชันจาก URL (GitHub release/gist) ตอนเปิดแอป แจ้งเฉยๆ ไม่บังคับ | `web/js/app.js` |
| C9 | **Deploy จาก FM** | ปุ่มส่ง addon จาก project store → com.mojang โดยตรง (มี `/api/projects` deploy logic แล้ว เชื่อมให้ถึงกัน) | `web/js/pages/filemanager.js`, `app/api/projects.py` |

ทำ C1–C2 ก่อน (ต่อยอด FM ที่เพิ่งเสร็จ), C3–C6 เป็นชุด "บรรยากาศ" ใช้ assets จาก Part A, C7–C9 เก็บท้าย.

---

## Verification Checklist (ก่อนถือว่างานเสร็จ)

- [ ] ภาพครบ 8 ไฟล์ตามตาราง Part A, โปร่ง/ทึบถูกต้อง, ถูก reference ใน CSS/HTML จริง
- [ ] `neu run` เปิดแอปได้, titlebar min/max/close ทำงาน (Neutralino API)
- [ ] `build.bat` ผ่าน → `dist/heaven-send-studio/` รันได้บนเครื่องไม่มี Python
- [ ] ทุก tab เดิมใช้งานได้ผ่าน backend.exe (โดยเฉพาะ FM: profiles/addons/worlds/world drill-in/ลบ→Recycle Bin/เปิดโฟลเดอร์)
- [ ] native dialog (เลือกไฟล์/โฟลเดอร์) ใช้ Neutralino dialog ได้จริงในหน้า skin/merger/checker
- [ ] ปิดหน้าต่างแล้ว `backend.exe` หายจาก Task Manager
- [ ] `py -3.12 -m pytest tests/` เขียวทั้งหมด (หลัง C7)
- [ ] `run.py` (pywebview) ยังรันได้เป็น fallback

## สิ่งที่ห้ามทำ (ย้ำ)
- ห้าม hardcode port — สุ่ม + poll health เสมอ
- ห้ามลบ `run.py` / `app/api/dialogs.py` จนกว่า checklist ข้างบนผ่านครบ
- ห้ามใช้ assets จาก `D:\Project Addon` — gen ใหม่ทั้งหมด
- ห้ามเช็ค route จาก `app.routes` — ยิง HTTP จริงเท่านั้น
