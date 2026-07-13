// Script Lab — smart config editor for addon scripts.
// Open .mcaddon/.zip/folder → pick a .js file → edit values in a table →
// save writes ONLY the changed value spans (formatting/comments preserved).
import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

let bpPath = "";
let scripts = [];
let curScript = null;   // {path, name, ...}
let parsed = null;      // /api/sl/parse result
let dirty = new Map();  // fieldId -> {field, newText, display}

const KIND_ICON = { config: "settings", skill: "swords", main: "rocket", util: "wrench", inline: "code", script: "document" };
const TAG_ICON = { damage: "swords", cooldown: "refresh", range: "search", duration: "refresh", speed: "waves", heal: "heart", item: "dagger", sound: "music", particle: "image" };

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "Script Lab · スクリプト"),
    el("div", { class: "page-desc" },
      "เปิด .mcaddon/โฟลเดอร์ → เลือกสคริป → ปรับค่าดาเมจ/คูลดาวน์/สกิลในตาราง — เซฟแล้วคอมเมนต์และ format เดิมอยู่ครบ (สำรอง .bak ทุกครั้ง)")
  ));

  // ── Intake ──
  const srcInput = el("input", { type: "text", placeholder: "ไฟล์ .mcaddon/.zip หรือโฟลเดอร์ addon/BP" });
  const pickFileBtn = el("button", { class: "btn-ghost btn-sm" }, icon("document", { size: 15 }), " เลือกไฟล์");
  const pickDirBtn = el("button", { class: "btn-ghost btn-sm" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const openBtn = el("button", { class: "btn-primary btn-sm" }, icon("folder-open", { size: 15 }), " เปิด");
  const openStatus = el("div", { class: "field-hint", style: "min-height:18px" }, "");

  const doOpen = async () => {
    const p = srcInput.value.trim();
    if (!p) { openStatus.textContent = "เลือกไฟล์หรือโฟลเดอร์ก่อน"; return; }
    openStatus.textContent = "กำลังแยกไฟล์...";
    openBtn.disabled = true;
    try {
      const r = await api.post("/api/sl/open", { path: p });
      bpPath = r.bp_path;
      scripts = r.scripts;
      openStatus.textContent = `พบ ${scripts.length} สคริปใน BP`;
      openStatus.className = "field-hint log-ok";
      curScript = null; parsed = null; dirty.clear();
      drawFileList();
      drawTable();
      const first = scripts.find(s => s.field_count > 0) || scripts[0];
      if (first) selectScript(first);
    } catch (e) {
      openStatus.textContent = "เปิดไม่ได้: " + e.message;
      openStatus.className = "field-hint log-err";
    } finally { openBtn.disabled = false; }
  };
  pickFileBtn.addEventListener("click", async () => {
    const p = await pickSingle({ mode: "open_file", filters: [".mcaddon", ".mcpack", ".zip"] });
    if (p) { srcInput.value = p; doOpen(); }
  });
  pickDirBtn.addEventListener("click", async () => {
    const p = await pickSingle({ mode: "folder" });
    if (p) { srcInput.value = p; doOpen(); }
  });
  openBtn.addEventListener("click", doOpen);
  srcInput.addEventListener("keydown", (e) => { if (e.key === "Enter") doOpen(); });

  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "เลือก Addon"),
    el("div", { class: "file-pick" }, srcInput, pickFileBtn, pickDirBtn, openBtn),
    openStatus,
    el("div", { class: "field-hint", style: "margin-top:6px" },
      "เคล็ดลับ: ถ้าเปิดโฟลเดอร์ที่ deploy อยู่ใน development_behavior_packs แล้วพิมพ์ /reload ในเกม ค่าที่แก้จะมีผลทันที"),
  ));

  // ── Workspace ──
  const fileList = el("div", { class: "sl-files" });
  const table = el("div", { class: "sl-table" });
  const ws = el("div", { class: "sl-layout" }, fileList, table);
  main.append(ws);

  function drawFileList() {
    fileList.innerHTML = "";
    if (!scripts.length) { ws.style.display = "none"; return; }
    ws.style.display = "";
    fileList.append(el("div", { class: "sl-files-head" }, `ไฟล์สคริป (${scripts.length})`));
    for (const s of scripts) {
      const item = el("div", { class: "sl-file" + (curScript && curScript.path === s.path ? " active" : "") },
        el("div", { class: "sl-file-row" },
          icon(KIND_ICON[s.kind] || "document", { size: 15 }),
          el("span", { class: "sl-file-name" }, s.name),
          s.field_count ? el("span", { class: "sl-file-count" }, String(s.field_count)) : null,
        ),
        s.summary ? el("div", { class: "sl-file-sum", title: s.summary }, s.summary) : null,
      );
      item.addEventListener("click", () => selectScript(s));
      fileList.append(item);
    }
  }

  async function selectScript(s) {
    if (dirty.size && !confirm("มีค่าแก้ค้างยังไม่เซฟ — ทิ้งการแก้ไข?")) return;
    dirty.clear();
    curScript = s;
    drawFileList();
    table.innerHTML = '<div class="loading">กำลังอ่านสคริป...</div>';
    try {
      parsed = await api.get("/api/sl/parse?js_path=" + encodeURIComponent(s.path));
      drawTable();
    } catch (e) {
      table.innerHTML = "";
      table.append(el("div", { class: "log-err", style: "padding:14px" }, "อ่านไม่ได้: " + e.message));
    }
  }

  function drawTable() {
    table.innerHTML = "";
    if (!curScript || !parsed) {
      table.append(el("div", { class: "empty" }, "เลือกไฟล์สคริปทางซ้าย"));
      return;
    }

    const search = el("input", { type: "text", placeholder: "ค้นหาค่า / คอมเมนต์...", class: "sl-search" });
    const saveBtn = el("button", { class: "btn-primary btn-sm", disabled: "" }, icon("save", { size: 14 }), " บันทึก");
    const reloadBtn = el("button", { class: "btn-ghost btn-sm", title: "อ่านไฟล์ใหม่" }, icon("refresh", { size: 14 }));
    const status = el("span", { class: "spinner-inline" }, "");
    const head = el("div", { class: "sl-toolbar" },
      el("div", { class: "sl-file-title" },
        el("span", {}, curScript.name),
        parsed.file_summary ? el("span", { class: "sl-file-title-sum" }, " — " + parsed.file_summary) : null),
      el("div", { class: "sl-toolbar-actions" }, search, reloadBtn, saveBtn, status),
    );
    table.append(head);

    const body = el("div", { class: "sl-body" });
    table.append(body);

    const updateSaveBtn = () => {
      saveBtn.disabled = dirty.size === 0;
      saveBtn.innerHTML = "";
      saveBtn.append(icon("save", { size: 14 }), ` บันทึก${dirty.size ? ` (${dirty.size})` : ""}`);
    };

    const markDirty = (f, newText, row, display) => {
      if (newText === null) dirty.delete(f.id);
      else dirty.set(f.id, { field: f, newText, display });
      row.classList.toggle("dirty", dirty.has(f.id));
      updateSaveBtn();
    };

    const drawRows = () => {
      body.innerHTML = "";
      const q = search.value.trim().toLowerCase();
      let shown = 0;
      for (const g of parsed.groups) {
        const rows = g.fields.filter(f =>
          !q || f.path.toLowerCase().includes(q) || (f.comment || "").toLowerCase().includes(q));
        if (!rows.length) continue;
        body.append(el("div", { class: "sl-group" }, g.name));
        let lastSection = "";
        for (const f of rows) {
          if (f.section && f.section !== lastSection) {
            body.append(el("div", { class: "sl-section" }, f.section));
            lastSection = f.section;
          }
          body.append(fieldRow(f, markDirty));
          shown++;
        }
      }
      if (!shown) body.append(el("div", { class: "empty" }, q ? "ไม่พบค่าที่ค้นหา" : "ไฟล์นี้ไม่มีค่าที่แก้ได้"));
    };
    search.addEventListener("input", drawRows);
    drawRows();

    reloadBtn.addEventListener("click", () => selectScript(curScript));

    saveBtn.addEventListener("click", async () => {
      if (!dirty.size) return;
      const edits = [...dirty.values()].map(d => ({
        start: d.field.start, end: d.field.end, new_text: d.newText,
      }));
      saveBtn.disabled = true;
      status.textContent = "กำลังบันทึก...";
      try {
        const r = await api.post("/api/sl/save", { js_path: curScript.path, mtime: parsed.mtime, edits });
        if (r.synced?.length) {
          status.textContent = `✅ บันทึก + sync เข้าเกมแล้ว (${r.synced.length} ที่) — พิมพ์ /reload ในเกม`;
        } else if (r.already_in_game) {
          status.textContent = `✅ บันทึกแล้ว (ไฟล์อยู่ในเกม) — พิมพ์ /reload ในเกม`;
        } else {
          status.textContent = `✅ บันทึก ${edits.length} ค่า (สำรอง .bak แล้ว)`;
        }
        dirty.clear();
        // re-parse silently so spans stay valid for the next edit
        parsed = await api.get("/api/sl/parse?js_path=" + encodeURIComponent(curScript.path));
        drawRows();
        updateSaveBtn();
      } catch (e) {
        status.textContent = "❌ " + e.message;
        saveBtn.disabled = false;
      }
    });
  }

  // มาจากหน้าอื่น (#/scriptlab?open=<path>) → เปิดให้เลย
  // ไม่งั้นถ้ามีโปรเจกต์ปักหมุดอยู่ ใช้พาธของมันแทนอัตโนมัติ (ไม่ต้องเลือกซ้ำ)
  const openParam = params && params.get("open");
  const autoPath = openParam || activeProjectOpenPath();
  if (autoPath) {
    srcInput.value = autoPath;
    doOpen();
  }
}

// ---------- one field row ----------
function fieldRow(f, markDirty) {
  const label = f.comment || "";
  const tagIc = TAG_ICON[f.tag];
  const row = el("div", { class: "sl-row" + (f.readonly ? " readonly" : "") });

  row.append(el("div", { class: "sl-row-key", title: f.path },
    tagIc ? icon(tagIc, { size: 13, class: "sl-tag" }) : null,
    el("span", {}, f.key)));

  const ctrl = el("div", { class: "sl-row-ctrl" });
  const hint = el("span", { class: "sl-hint" }, "");

  const setHint = (v) => {
    if (f.unit === "ticks" && isFinite(v)) hint.textContent = `= ${(v / 20).toFixed(v % 20 ? 1 : 0)} วิ`;
    else if (f.unit === "percent" && isFinite(v)) hint.textContent = v <= 1 ? `= ${(v * 100).toFixed(0)}%` : "";
    else hint.textContent = "";
  };

  if (f.readonly) {
    ctrl.append(el("span", { class: "sl-raw", title: "ค่าคำนวณ/โครงสร้างซับซ้อน — แก้ในไฟล์เอง" }, f.raw));
  } else if (f.type === "boolean") {
    const cb = el("input", { type: "checkbox" });
    cb.checked = f.value === true;
    cb.addEventListener("change", () =>
      markDirty(f, cb.checked === f.value ? null : String(cb.checked), row));
    ctrl.append(cb);
  } else if (f.type === "array") {
    const wrap = el("div", { class: "sl-chips" });
    const vals = f.items.map(it => ({ ...it }));
    const serialize = () => "[" + vals.map(it =>
      it.type === "string" ? jsStr(String(it.value), it.quote || '"') : String(it.value)).join(", ") + "]";
    const redraw = () => {
      wrap.innerHTML = "";
      vals.forEach((it, i) => {
        const inp = el("input", { class: "sl-chip", value: String(it.value) });
        inp.addEventListener("change", () => {
          it.value = it.type === "number" && !isNaN(parseFloat(inp.value)) ? parseFloat(inp.value) : inp.value;
          markDirty(f, serialize(), row);
        });
        wrap.append(inp);
      });
    };
    redraw();
    ctrl.append(wrap);
  } else {
    const inp = el("input", {
      class: "sl-input",
      type: f.type === "number" ? "number" : "text",
      step: "any",
      value: String(f.value),
    });
    setHint(f.value);
    inp.addEventListener("input", () => {
      let newText = null;
      if (f.type === "number") {
        const n = parseFloat(inp.value);
        if (!isNaN(n) && n !== f.value) newText = String(n);
        setHint(n);
      } else if (inp.value !== f.value) {
        newText = jsStr(inp.value, f.quote || '"');
      }
      markDirty(f, newText, row);
    });
    ctrl.append(inp);
  }
  ctrl.append(hint);
  row.append(ctrl);
  row.append(el("div", { class: "sl-row-comment", title: label }, label));
  return row;
}

function jsStr(value, quote) {
  const body = value.replaceAll("\\", "\\\\").replaceAll(quote, "\\" + quote).replaceAll("\n", "\\n");
  return quote + body + quote;
}
