import { api, el, pickSingle, getApiBase } from "../api.js";
import { icon } from "../ui/icons.js";
import { showContextMenu, gotoPage } from "../ui/contextmenu.js";
import { setActiveProject, getActiveProject, clearActiveProject } from "../state/activeProject.js";
import { toast } from "../ui/toast.js";
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
  const selectAll = el("input", { type: "checkbox", class: "project-select-all", "aria-label": "เลือกโปรเจกต์ที่แสดงทั้งหมด", disabled: "" });
  const selectedCount = el("span", { class: "bulk-selection-count" }, "ยังไม่ได้เลือก");
  const clearSelectionBtn = el("button", { class: "btn-ghost btn-sm", type: "button", disabled: "" }, "ล้างที่เลือก");
  const bulkDeleteBtn = el("button", { class: "btn-danger btn-sm", type: "button", disabled: "" }, icon("trash", { size: 14 }), " ลบที่เลือก");
  const selectionBar = el("div", { class: "bulk-toolbar" },
    el("label", { class: "bulk-select-all" }, selectAll, "เลือกทั้งหมด"),
    selectedCount,
    el("div", { class: "bulk-toolbar-spacer" }),
    clearSelectionBtn,
    bulkDeleteBtn,
  );
  main.append(selectionBar);
  const importStatus = el("div", { class: "field-hint", style: "margin:-10px 0 12px" }, "");
  main.append(importStatus);

  const grid = el("div", { class: "grid" });
  main.append(grid);
  grid.innerHTML = '<div class="empty">กำลังโหลด...</div>';

  const selectedKeys = new Set();
  let visibleItems = [];
  const projectKey = (p) => p.open_path || `${p.store}:${p.name}`;

  const updateSelectionUI = () => {
    const visibleSelected = visibleItems.filter(p => selectedKeys.has(projectKey(p))).length;
    selectAll.checked = visibleItems.length > 0 && visibleSelected === visibleItems.length;
    selectAll.indeterminate = visibleSelected > 0 && visibleSelected < visibleItems.length;
    selectAll.disabled = visibleItems.length === 0;
    selectedCount.textContent = selectedKeys.size ? `เลือกแล้ว ${selectedKeys.size} โปรเจกต์` : "ยังไม่ได้เลือก";
    clearSelectionBtn.disabled = selectedKeys.size === 0;
    bulkDeleteBtn.disabled = selectedKeys.size === 0;
    selectionBar.classList.toggle("has-selection", selectedKeys.size > 0);
  };

  const clearSelection = () => {
    selectedKeys.clear();
    updateSelectionUI();
    draw();
  };

  const draw = () => {
    const q = search.value.trim().toLowerCase();
    const store = storeFilter.value;
    const items = allProjects.filter(p =>
      (!q || p.name.toLowerCase().includes(q)) && (!store || p.store === store));
    visibleItems = items.slice(0, 600);
    count.textContent = `${items.length} / ${allProjects.length} โปรเจกต์`;
    grid.innerHTML = "";
    if (!items.length) {
      grid.append(el("div", { class: "empty" }, "ไม่พบโปรเจกต์"));
      updateSelectionUI();
      return;
    }
    for (const p of visibleItems) grid.append(card(p, reload, zone, selectedKeys, updateSelectionUI));
    updateSelectionUI();
  };

  const reload = async () => {
    selectedKeys.clear();
    const data = await api.get(projUrl);
    allProjects = data.projects || [];
    draw();
  };

  selectAll.addEventListener("change", () => {
    for (const p of visibleItems) {
      const key = projectKey(p);
      if (selectAll.checked) selectedKeys.add(key);
      else selectedKeys.delete(key);
    }
    draw();
  });
  clearSelectionBtn.addEventListener("click", clearSelection);
  bulkDeleteBtn.addEventListener("click", async () => {
    const selectedProjects = allProjects.filter(p => selectedKeys.has(projectKey(p)));
    if (!selectedProjects.length) { clearSelection(); return; }

    const paths = [...new Set(selectedProjects.flatMap(p => Object.values(p.paths || {}).filter(Boolean)))];
    const names = selectedProjects.length <= 3
      ? selectedProjects.map(p => `“${p.name}”`).join(", ")
      : `${selectedProjects.length} โปรเจกต์`;
    if (!confirm(`ลบ ${names} ถาวร?\nไฟล์และโฟลเดอร์ของรายการที่เลือกจะถูกลบ`)) return;

    bulkDeleteBtn.disabled = true;
    try {
      const result = await api.post("/api/projects/delete", { paths });
      toast.success(`ลบแล้ว ${selectedProjects.length} โปรเจกต์ (${result.removed.length} รายการ)`);
      await reload();
    } catch (e) {
      toast.error("ลบไม่สำเร็จ: " + e.message);
      updateSelectionUI();
    }
  });

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
    updateSelectionUI();
  }
}

function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(0) + " KB";
  if (b < 1073741824) return (b / 1048576).toFixed(1) + " MB";
  return (b / 1073741824).toFixed(2) + " GB";
}

function card(p, reload, zone, selectedKeys, updateSelectionUI) {
  const paths = p.paths || {};
  const bp = paths.bp || null, rp = paths.rp || null;
  const key = p.open_path || `${p.store}:${p.name}`;

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

  const select = el("input", { type: "checkbox", class: "proj-select", "aria-label": `เลือกโปรเจกต์ ${p.name}` });
  select.checked = selectedKeys.has(key);
  select.addEventListener("click", (e) => e.stopPropagation());
  select.addEventListener("change", () => {
    if (select.checked) selectedKeys.add(key);
    else selectedKeys.delete(key);
    updateSelectionUI();
  });

  const cardEl = el("div", { class: "proj-card", style: "cursor:default" },
    el("div", { class: "proj-card-head" },
      el("label", { class: "proj-select-wrap", title: `เลือก ${p.name}` }, select),
      el("div", { class: "row", style: "gap:10px;align-items:center;flex:1;min-width:0" }, thumb,
      el("div", { style: "flex:1;min-width:0" },
        el("div", { class: "proj-name" }, p.name),
        el("div", { class: "proj-store" }, p.store, " · ", sizePill),
      ))),
    el("div", { style: "margin-top:8px" }, badges),
    el("div", { class: "row", style: "gap:4px;margin-top:10px;flex-wrap:wrap" },
      openBtn, packBtn, deployBtn, renameBtn, dupBtn, delBtn),
    status,
  );
  // ปักหมุด: ทุกเครื่องมือ (Script Lab/checker/weapon/physics/deploy) เติม path
  // ของโปรเจกต์นี้ให้เองแทนที่จะต้องเลือกซ้ำทุกหน้า
  const isPinned = () => (getActiveProject() || {}).name === p.name && (getActiveProject() || {}).store === p.store;
  const pinProject = () => {
    setActiveProject({ name: p.name, zone: zone || "", store: p.store, paths });
    toast.success(`ปักหมุด "${p.name}" แล้ว — Script Lab/ตรวจสอบ/ฟิสิกส์/อาวุธ จะเติม path ให้อัตโนมัติ`);
  };

  // คลิกขวา → เมนู "ส่งไปที่..." โยงเครื่องมืออื่น
  cardEl.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    const src = bp || paths.folder || paths.mcaddon || rp;
    showContextMenu(e.clientX, e.clientY, [
      isPinned()
        ? { label: "เลิกปักหมุดโปรเจกต์นี้", icon: "close",
            onClick: () => { clearActiveProject(); toast.info("เลิกปักหมุดแล้ว"); } }
        : { label: "ปักหมุดเป็นโปรเจกต์ที่ทำอยู่", icon: "folder", onClick: pinProject },
      "-",
      src ? { label: "เปิดใน Script Lab", icon: "sliders",
        onClick: () => gotoPage("scriptlab?open=" + encodeURIComponent(src)) } : null,
      (bp || paths.folder) ? { label: "เปิดใน Script Builder", icon: "puzzle",
        onClick: () => gotoPage("scriptbuilder?open=" + encodeURIComponent(bp || paths.folder)) } : null,
      src ? { label: "ตรวจสอบ Addon", icon: "check-circle",
        onClick: () => gotoPage("checker?open=" + encodeURIComponent(src)) } : null,
      src ? { label: "ประวัติไฟล์", icon: "archive",
        onClick: () => gotoPage("history?open=" + encodeURIComponent(paths.folder || bp || rp || paths.mcaddon || src)) } : null,
      src ? { label: "ดู Asset", icon: "image",
        onClick: () => gotoPage("assets?open=" + encodeURIComponent(src)) } : null,
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
