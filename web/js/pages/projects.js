import { api, el, pickSingle, getApiBase } from "../api.js";
import { icon } from "../ui/icons.js";
import { showContextMenu, gotoPage } from "../ui/contextmenu.js";
import { addPacksToWorldDialog } from "../ui/worldpicker.js";

let allProjects = [];
let mainEl = null;

const ZONE_INFO = {
  skin:  { title: "โปรเจกต์สกิน · スキン", desc: "โปรเจกต์ของโซนสกิน — ค้นหา, เปิด, แพ็ค, Deploy, rename/ลบ/copy" },
  skill: { title: "โปรเจกต์สกิล · スキル", desc: "โปรเจกต์ของโซนสกิล (Projects Sillkes) — ค้นหา, เปิด, แพ็ค, Deploy" },
};

export async function render(main, params) {
  mainEl = main;
  const zone = (params && params.get("zone")) || "";
  const zi = ZONE_INFO[zone] || { title: "โปรเจกต์", desc: "งานทั้งหมดใน Projects + Projects Sillkes — ค้นหา, เปิด, แพ็ค, Deploy, rename/ลบ/copy" };
  const projUrl = "/api/projects" + (zone ? "?zone=" + zone : "");
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, zi.title),
    el("div", { class: "page-desc" }, zi.desc)
  ));

  const search = el("input", { type: "text", placeholder: "ค้นหาชื่อโปรเจกต์..." });
  const storeFilter = el("select", {}, el("option", { value: "" }, "ทุก store"));
  const importBtn = el("button", { class: "btn-ghost btn-sm" }, icon("upload", { size: 15 }), " Import .mcaddon");
  const count = el("span", { class: "count-pill" }, "");
  main.append(el("div", { class: "toolbar" }, search, storeFilter, importBtn, count));
  const importStatus = el("div", { class: "field-hint", style: "margin:-10px 0 12px" }, "");
  main.append(importStatus);

  const grid = el("div", { class: "grid" });
  main.append(grid);
  grid.innerHTML = '<div class="empty">กำลังโหลด...</div>';

  const draw = () => {
    const q = search.value.trim().toLowerCase();
    const store = storeFilter.value;
    const items = allProjects.filter(p =>
      (!q || p.name.toLowerCase().includes(q)) && (!store || p.store === store));
    count.textContent = `${items.length} / ${allProjects.length} โปรเจกต์`;
    grid.innerHTML = "";
    if (!items.length) { grid.append(el("div", { class: "empty" }, "ไม่พบโปรเจกต์")); return; }
    for (const p of items.slice(0, 600)) grid.append(card(p, reload));
  };

  const reload = async () => {
    const data = await api.get(projUrl);
    allProjects = data.projects || [];
    draw();
  };

  search.addEventListener("input", draw);
  storeFilter.addEventListener("change", draw);
  importBtn.addEventListener("click", async () => {
    let mcaddonPath;
    try {
      mcaddonPath = await pickSingle({ mode: "open_file", filters: ["Addon (*.mcaddon)"] });
    } catch (e) {
      if (e.status === 501) { importStatus.textContent = "❌ native file picker ใช้ไม่ได้ในโหมด browser"; return; }
      importStatus.textContent = "❌ " + e.message; return;
    }
    if (!mcaddonPath) return;
    importStatus.textContent = "กำลัง import...";
    try {
      const r = await api.post("/api/projects/import", { mcaddon_path: mcaddonPath });
      importStatus.textContent = `✅ import แล้ว ${r.imported.length} pack เข้า ${r.dest_store}`;
      await reload();
    } catch (e) {
      importStatus.textContent = "❌ " + e.message;
    }
  });

  try {
    const data = await api.get(projUrl);
    allProjects = data.projects || [];
    for (const s of [...new Set(allProjects.map(p => p.store))]) storeFilter.append(el("option", { value: s }, s));
    draw();
  } catch (e) {
    grid.innerHTML = `<div class="empty">โหลดโปรเจกต์ไม่ได้: ${e.message}</div>`;
  }
}

function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(0) + " KB";
  if (b < 1073741824) return (b / 1048576).toFixed(1) + " MB";
  return (b / 1073741824).toFixed(2) + " GB";
}

function card(p, reload) {
  const paths = p.paths || {};
  const bp = paths.bp || null, rp = paths.rp || null;

  const thumb = el("div", { style: "width:40px;height:40px;border-radius:8px;background:#1e1f22;flex:none;overflow:hidden" });
  if (p.has_icon) {
    const q = new URLSearchParams();
    if (bp) q.set("bp", bp); if (rp) q.set("rp", rp); if (paths.folder) q.set("folder", paths.folder);
    thumb.append(el("img", { src: getApiBase() + "/api/projects/thumbnail?" + q.toString(), width: "40", height: "40", style: "object-fit:cover" }));
  }

  const badges = el("div", { class: "badges" },
    el("span", { class: "badge " + (p.has_bp ? "bp" : "off") }, "BP"),
    el("span", { class: "badge " + (p.has_rp ? "rp" : "off") }, "RP"),
    el("span", { class: "badge " + (p.has_mcaddon ? "mc" : "off") }, ".mcaddon"),
  );
  const sizePill = el("span", { class: "field-hint" }, "");
  const status = el("div", { class: "field-hint", style: "min-height:14px;margin-top:6px;word-break:break-all" }, "");

  // lazy size
  api.post("/api/projects/info", { paths }).then(r => { sizePill.textContent = fmtSize(r.size_bytes); }).catch(() => {});

  const mkBtn = (label, fn) => { const b = el("button", { class: "btn-ghost btn-sm" }, label); b.addEventListener("click", fn); return b; };

  const openBtn = mkBtn(icon("folder-open", { size: 15 }), async () => {
    try { await api.post("/api/projects/open-folder", { path: p.open_path }); }
    catch (e) { status.textContent = "❌ " + e.message; }
  });
  const packBtn = mkBtn(icon("box", { size: 15 }), async () => {
    status.textContent = "แพ็ค...";
    try { const r = await api.post("/api/projects/export", { name: p.name, bp_path: bp, rp_path: rp }); status.textContent = "✅ " + r.mcaddon; }
    catch (e) { status.textContent = "❌ " + e.message; }
  });
  const deployBtn = mkBtn(icon("rocket", { size: 15 }), async () => {
    if (!bp && !rp) { status.textContent = "❌ ไม่มี BP/RP"; return; }
    status.textContent = "deploy...";
    try { const r = await api.post("/api/projects/deploy", { bp_path: bp, rp_path: rp }); status.textContent = "✅ deploy " + r.deployed.length + " pack"; }
    catch (e) { status.textContent = "❌ " + e.message; }
  });

  // Deploy → เปิด world-picker → เพิ่ม pack ที่ deploy ทั้งหมด (BP+RP) เข้าโลกเดียว
  const deployAndAdd = async () => {
    if (!bp && !rp) { status.textContent = "❌ ไม่มี BP/RP"; return; }
    status.textContent = "deploy...";
    try {
      const r = await api.post("/api/projects/deploy", { bp_path: bp, rp_path: rp });
      const packs = r.deployed_packs || [];
      status.textContent = `✅ deploy ${r.deployed.length} pack`;
      if (!packs.length) { status.textContent = "deploy แล้ว แต่ไม่พบ pack identity ใน manifest"; return; }
      addPacksToWorldDialog(packs);
    } catch (e) { status.textContent = "❌ " + e.message; }
  };
  const renameBtn = mkBtn(icon("pencil", { size: 15 }), async () => {
    const nn = prompt("เปลี่ยนชื่อเป็น:", p.name);
    if (!nn || nn === p.name) return;
    try { await api.post("/api/projects/rename", { paths, new_name: nn }); await reload(); }
    catch (e) { status.textContent = "❌ " + e.message; }
  });
  const dupBtn = mkBtn(icon("copy", { size: 15 }), async () => {
    const nn = prompt("ก๊อปเป็นชื่อ:", p.name + "_copy");
    if (!nn) return;
    status.textContent = "copy...";
    try { await api.post("/api/projects/duplicate", { paths, new_name: nn }); await reload(); }
    catch (e) { status.textContent = "❌ " + e.message; }
  });
  const delBtn = mkBtn(icon("trash", { size: 15 }), async () => {
    if (!confirm(`ลบ "${p.name}" ถาวร?\n(${Object.keys(paths).length} รายการ)`)) return;
    try { await api.post("/api/projects/delete", { paths: Object.values(paths) }); await reload(); }
    catch (e) { status.textContent = "❌ " + e.message; }
  });

  const cardEl = el("div", { class: "proj-card", style: "cursor:default" },
    el("div", { class: "row", style: "gap:10px;align-items:center" }, thumb,
      el("div", { style: "flex:1;min-width:0" },
        el("div", { class: "proj-name" }, p.name),
        el("div", { class: "proj-store" }, p.store, " · ", sizePill),
      )),
    el("div", { style: "margin-top:8px" }, badges),
    el("div", { class: "row", style: "gap:4px;margin-top:10px;flex-wrap:wrap" },
      openBtn, packBtn, deployBtn, renameBtn, dupBtn, delBtn),
    status,
  );
  // คลิกขวา → เมนู "ส่งไปที่..." โยงเครื่องมืออื่น
  cardEl.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const src = bp || paths.folder || paths.mcaddon || rp;
    showContextMenu(e.clientX, e.clientY, [
      src ? { label: "เปิดใน Script Lab", icon: "sliders",
        onClick: () => gotoPage("scriptlab?open=" + encodeURIComponent(src)) } : null,
      src ? { label: "ตรวจสอบ Addon", icon: "check-circle",
        onClick: () => gotoPage("checker?open=" + encodeURIComponent(src)) } : null,
      (bp || rp) ? { label: "Deploy เข้า com.mojang", icon: "rocket",
        onClick: () => deployBtn.click() } : null,
      (bp || rp) ? { label: "Deploy + เพิ่มเข้าโลก…", icon: "rocket",
        onClick: () => deployAndAdd() } : null,
      "-",
      { label: "แพ็คเป็น .mcaddon", icon: "box", onClick: () => packBtn.click() },
      { label: "เปิดโฟลเดอร์", icon: "folder-open", onClick: () => openBtn.click() },
    ]);
  });
  return cardEl;
}
