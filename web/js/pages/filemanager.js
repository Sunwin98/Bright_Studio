import { api, el, getApiBase } from "../api.js";
import { openWindow, confirmDialog } from "../ui/window.js";
import { browsePath } from "../ui/explorer.js";
import { icon } from "../ui/icons.js";
import { showContextMenu, gotoPage } from "../ui/contextmenu.js";
import { addPacksToWorldDialog } from "../ui/worldpicker.js";
import { toast } from "../ui/toast.js";

let profiles = [];
let curProfile = 0;
let curTab = "addons";
let contentEl = null;

let allPacks = [];
let allWorlds = [];

let searchQuery = "";
let filterType = "all"; // all, bp, rp
let sortBy = "name"; // name, mtime
const selectedPaths = new Set();

function iconUrl(path) { return getApiBase() + "/api/fm/icon?path=" + encodeURIComponent(path); }

function fmtDate(mtime) {
  if (!mtime) return "";
  const d = new Date(mtime * 1000);
  return "เล่นล่าสุด " + d.toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" });
}

function cardIcon(path, fallbackIcon) {
  if (path) {
    const img = el("img", { class: "fm-card-icon", src: iconUrl(path), alt: "" });
    img.addEventListener("error", () => {
      const div = el("div", { class: "fm-card-icon" }, icon(fallbackIcon, { size: 20 }));
      img.replaceWith(div);
    });
    return img;
  }
  return el("div", { class: "fm-card-icon" }, icon(fallbackIcon, { size: 20 }));
}

// เปิดดูไฟล์ในแอปเลย (ไม่เด้ง Windows Explorer)
function reveal(path) {
  browsePath(path);
}

async function del(path, name, kind) {
  const ok = await confirmDialog({
    title: "ลบ", jp: "削除", danger: true, confirmLabel: "ลบลงถังขยะ",
    message: `ลบ${kind} "${name}" ?\nไฟล์จะถูกย้ายไป Recycle Bin (กู้คืนได้)`,
  });
  if (!ok) return;
  try {
    await api.post("/api/fm/delete", { path });
    await loadContent();
  } catch (e) { toast.error("ลบไม่สำเร็จ: " + e.message); }
}

function actionBtns(path, name, kind) {
  return el("div", { class: "fm-card-actions" },
    el("button", { class: "fm-icon-btn", title: "เปิดในโฟลเดอร์", onclick: (e) => { e.stopPropagation(); reveal(path); } }, icon("folder-open", { size: 15 })),
    el("button", { class: "fm-icon-btn danger", title: "ลบ", onclick: (e) => { e.stopPropagation(); del(path, name, kind); } }, icon("trash", { size: 15 })),
  );
}

function selectControl(path, name, redraw) {
  const checkbox = el("input", {
    type: "checkbox",
    class: "fm-select",
    "aria-label": `เลือก${name}`,
  });
  checkbox.checked = selectedPaths.has(path);
  checkbox.addEventListener("change", () => {
    if (checkbox.checked) selectedPaths.add(path);
    else selectedPaths.delete(path);
    redraw();
  });
  const wrap = el("label", { class: "fm-select-wrap", title: `เลือก${name}` }, checkbox);
  wrap.addEventListener("click", (e) => e.stopPropagation());
  return wrap;
}

function bulkToolbar(items, allItems, noun, redraw) {
  const selectAll = el("input", { type: "checkbox", class: "project-select-all", "aria-label": `เลือก${noun}ที่แสดงทั้งหมด` });
  const selectedCount = el("span", { class: "bulk-selection-count" }, "ยังไม่ได้เลือก");
  const clearBtn = el("button", { class: "btn-ghost btn-sm", type: "button", disabled: "" }, "ล้างที่เลือก");
  const deleteBtn = el("button", { class: "btn-danger btn-sm", type: "button", disabled: "" }, icon("trash", { size: 14 }), " ลบที่เลือก");
  const bar = el("div", { class: "bulk-toolbar fm-bulk-toolbar" },
    el("label", { class: "bulk-select-all" }, selectAll, "เลือกทั้งหมด"),
    selectedCount,
    el("div", { class: "bulk-toolbar-spacer" }),
    clearBtn,
    deleteBtn,
  );

  const update = () => {
    const visibleSelected = items.filter(item => selectedPaths.has(item.path)).length;
    selectAll.checked = items.length > 0 && visibleSelected === items.length;
    selectAll.indeterminate = visibleSelected > 0 && visibleSelected < items.length;
    selectAll.disabled = items.length === 0;
    selectedCount.textContent = selectedPaths.size ? `เลือกแล้ว ${selectedPaths.size} รายการ` : "ยังไม่ได้เลือก";
    clearBtn.disabled = selectedPaths.size === 0;
    deleteBtn.disabled = selectedPaths.size === 0;
    bar.classList.toggle("has-selection", selectedPaths.size > 0);
  };

  selectAll.addEventListener("change", () => {
    for (const item of items) {
      if (selectAll.checked) selectedPaths.add(item.path);
      else selectedPaths.delete(item.path);
    }
    redraw();
  });
  clearBtn.addEventListener("click", () => {
    selectedPaths.clear();
    redraw();
  });
  deleteBtn.addEventListener("click", async () => {
    const selected = allItems.filter(item => selectedPaths.has(item.path));
    if (!selected.length) { selectedPaths.clear(); redraw(); return; }
    const ok = await confirmDialog({
      title: "ลบที่เลือก", jp: "一括削除", danger: true, confirmLabel: "ลบทั้งหมด",
      message: `ลบ ${selected.length} ${noun} ลงถังขยะ?\nสามารถกู้คืนได้จาก Recycle Bin`,
    });
    if (!ok) return;

    deleteBtn.disabled = true;
    try {
      const result = await api.post("/api/fm/delete_many", { paths: selected.map(item => item.path) });
      selectedPaths.clear();
      await loadContent();
      toast.success(`ลบแล้ว ${result.trashed.length} รายการ · ย้ายไปถังขยะแล้ว`);
    } catch (e) {
      toast.error("ลบไม่สำเร็จ: " + e.message);
      update();
    }
  });
  update();
  return bar;
}

// เมนูกลาง "ส่งไปที่..." ของการ์ด addon — โยงทุกเครื่องมือ
function addonMenu(p, x, y) {
  const tag = p.type === "behavior" ? "BP" : "RP";
  showContextMenu(x, y, [
    { label: "เปิดใน Script Lab", icon: "sliders", hint: tag,
      onClick: () => gotoPage("scriptlab?open=" + encodeURIComponent(p.path)) },
    { label: "ตรวจสอบ Addon", icon: "check-circle",
      onClick: () => gotoPage("checker?open=" + encodeURIComponent(p.path)) },
    p.uuid ? { label: "เพิ่มเข้าโลก…", icon: "globe", onClick: () => addPacksToWorldDialog([p]) } : null,
    "-",
    { label: "เปิดดูไฟล์", icon: "folder-open", onClick: () => reveal(p.path) },
    { label: "ลบ (ลงถังขยะ)", icon: "trash", danger: true,
      onClick: () => del(p.path, p.name, tag === "BP" ? "behavior pack" : "resource pack") },
  ]);
}

function addonCard(p) {
  const tag = p.type === "behavior" ? "BP" : "RP";
  const card = el("div", { class: "fm-card clickable" },
    selectControl(p.path, `addon ${p.name}`, renderPacks),
    cardIcon(p.icon, "box"),
    el("div", { class: "fm-card-body" },
      el("div", { class: "fm-card-name", title: p.name }, p.name),
      el("div", { class: "fm-card-meta" }, `${tag} · v${p.version}`),
    ),
    actionBtns(p.path, p.name, tag === "BP" ? "behavior pack" : "resource pack"),
  );
  // คลิกซ้ายหรือขวา → เมนู "ส่งไปที่..."
  card.addEventListener("click", (e) => addonMenu(p, e.clientX, e.clientY));
  card.addEventListener("contextmenu", (e) => { e.preventDefault(); addonMenu(p, e.clientX, e.clientY); });
  return card;
}

function worldCard(w) {
  const card = el("div", { class: "fm-card clickable" },
    selectControl(w.path, `โลก ${w.name}`, renderWorlds),
    cardIcon(w.icon, "globe"),
    el("div", { class: "fm-card-body" },
      el("div", { class: "fm-card-name", title: w.name }, w.name),
      el("div", { class: "fm-card-meta" }, fmtDate(w.mtime)),
    ),
    actionBtns(w.path, w.name, "โลก"),
  );
  card.addEventListener("click", () => openWorld(w));
  card.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    showContextMenu(e.clientX, e.clientY, [
      { label: "จัดการ addon ในโลก", icon: "globe", onClick: () => openWorld(w) },
      { label: "เปิดดูไฟล์", icon: "folder-open", onClick: () => reveal(w.path) },
      "-",
      { label: "ลบโลก (ลงถังขยะ)", icon: "trash", danger: true, onClick: () => del(w.path, w.name, "โลก") },
    ]);
  });
  return card;
}

let currentWorldWindow = null;
async function openWorld(w) {
  let body;
  if (!currentWorldWindow || !document.body.contains(currentWorldWindow)) {
    body = el("div", {}, el("div", { class: "loading" }, "กำลังโหลด..."));
    currentWorldWindow = openWindow({ title: "WORLD ADDONS", jp: "ワールド", body, width: "min(580px, 92vw)" });
  } else {
    body = currentWorldWindow.querySelector(".hs-window-body").firstChild;
    body.innerHTML = '<div class="loading">กำลังโหลด...</div>';
  }

  try {
    const d = await api.get("/api/fm/world_addons?path=" + encodeURIComponent(w.path));
    body.innerHTML = "";
    body.append(el("div", { style: "font-weight:700; color:var(--text-bright); margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;" },
      el("span", {}, icon("globe", { size: 16 }), " " + w.name),
      el("button", { class: "btn-ghost btn-sm", onclick: () => loadContent() }, icon("refresh", { size: 14 }), " รีเฟรช")
    ));

    const toggleAddon = async (ptype, pack, btn) => {
      const action = pack.applied ? "disable" : "enable";
      btn.disabled = true;
      try {
        await api.post("/api/fm/toggle_world_addon", {
          world_path: w.path, ptype: ptype, pack_id: pack.uuid, version: pack.raw_version, action: action
        });
        openWorld(w); // Refresh UI
      } catch(e) {
        toast.error(e.message);
        btn.disabled = false;
      }
    };

    // ค้นหาแพ็ค (เครื่องนึงมี addon ได้หลายสิบตัว)
    const packSearch = el("input", { type: "text", placeholder: "ค้นหาแพ็ค...", style: "margin-bottom:10px;" });
    body.append(packSearch);
    const listWrap = el("div", {});
    body.append(listWrap);

    const row = (r, ptype, iconName) => {
      const btn = el("button", {
        class: r.applied ? "btn-danger btn-sm" : "btn-primary btn-sm",
        style: "min-width:72px;",
        onclick: function () { toggleAddon(ptype, r, this); },
      }, r.applied ? "− เอาออก" : "+ เพิ่ม");
      if (!r.installed && !r.applied) btn.style.display = "none";
      return el("div", { class: "fm-card", style: "padding:8px 10px; margin-bottom:6px;" },
        el("div", { class: "fm-card-icon", style: "width:34px;height:34px;" }, icon(iconName, { size: 17 })),
        el("div", { class: "fm-card-body" },
          el("div", { class: "fm-card-name", style: r.installed ? "" : "color:var(--text-muted);" }, r.name),
          el("div", { class: "fm-card-meta" }, `v${r.version}` + (r.installed ? "" : " · ไม่ได้ติดตั้ง")),
        ),
        btn);
    };

    const renderPackList = () => {
      const q = packSearch.value.trim().toLowerCase();
      listWrap.innerHTML = "";
      const section = (label, rows, ptype, iconName) => {
        const applied = rows.filter(r => r.applied && (!q || r.name.toLowerCase().includes(q)));
        const avail = rows.filter(r => !r.applied && (!q || r.name.toLowerCase().includes(q)));
        const wrap = el("div", { style: "margin-bottom:14px;" },
          el("div", { class: "card-title", style: "margin-bottom:8px;" }, label));
        wrap.append(el("div", { class: "field-hint", style: "margin-bottom:6px;" }, `ใช้อยู่ในโลกนี้ (${applied.length})`));
        if (!applied.length) wrap.append(el("div", { class: "field-hint", style: "opacity:.5;margin-bottom:6px;" }, "— ไม่มี —"));
        for (const r of applied) wrap.append(row(r, ptype, iconName));
        wrap.append(el("div", { class: "field-hint", style: "margin:10px 0 6px;" }, `เพิ่มเข้าโลกได้ (${avail.length})`));
        if (!avail.length) wrap.append(el("div", { class: "field-hint", style: "opacity:.5;" }, "— ไม่มี —"));
        for (const r of avail) wrap.append(row(r, ptype, iconName));
        return wrap;
      };
      listWrap.append(section("Behavior Packs", d.behavior, "behavior", "box"));
      listWrap.append(section("Resource Packs", d.resource, "resource", "palette"));
    };
    packSearch.addEventListener("input", renderPackList);
    renderPackList();
  } catch (e) {
    body.innerHTML = "";
    body.append(el("div", { class: "log-err" }, "โหลดไม่ได้: " + e.message));
  }
}

function renderPacks() {
  contentEl.innerHTML = "";
  let filtered = allPacks.filter(p => {
    if (filterType === "bp" && p.type !== "behavior") return false;
    if (filterType === "rp" && p.type !== "resource") return false;
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery)) return false;
    return true;
  });
  
  filtered.sort((a, b) => a.name.localeCompare(b.name));

  contentEl.append(bulkToolbar(filtered, allPacks, "addon", renderPacks));
  if (!filtered.length) { contentEl.append(el("div", { class: "empty" }, "ไม่พบ addon")); return; }
  const grid = el("div", { class: "fm-grid" });
  for (const p of filtered) grid.append(addonCard(p));
  contentEl.append(grid);
}

function renderWorlds() {
  contentEl.innerHTML = "";
  let filtered = allWorlds.filter(w => {
    if (searchQuery && !w.name.toLowerCase().includes(searchQuery)) return false;
    return true;
  });

  if (sortBy === "name") {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  } else {
    filtered.sort((a, b) => b.mtime - a.mtime);
  }

  contentEl.append(bulkToolbar(filtered, allWorlds, "โลก", renderWorlds));
  if (!filtered.length) { contentEl.append(el("div", { class: "empty" }, "ไม่พบโลก")); return; }
  const grid = el("div", { class: "fm-grid" });
  for (const w of filtered) grid.append(worldCard(w));
  contentEl.append(grid);
}

async function loadContent() {
  if (!profiles.length) return;
  selectedPaths.clear();
  contentEl.innerHTML = '<div class="loading">กำลังโหลด...</div>';
  try {
    if (curTab === "addons") {
      const d = await api.get(`/api/fm/addons?profile=${curProfile}`);
      allPacks = d.packs || [];
      renderPacks();
    } else {
      const d = await api.get(`/api/fm/worlds?profile=${curProfile}`);
      allWorlds = d.worlds || [];
      renderWorlds();
    }
  } catch (e) {
    contentEl.innerHTML = "";
    contentEl.append(el("div", { class: "log-err" }, "โหลดไม่ได้: " + e.message));
  }
}

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "จัดการไฟล์ · ファイル"),
    el("div", { class: "page-desc" }, "จัดการ addon และโลกใน Minecraft Bedrock (com.mojang) — ดู / เปิด / ลบ")
  ));

  try {
    const d = await api.get("/api/fm/profiles");
    profiles = d.profiles || [];
  } catch (e) {
    main.append(el("div", { class: "log-err" }, "โหลดโปรไฟล์ไม่ได้: " + e.message));
    return;
  }

  if (!profiles.length) {
    main.append(el("div", { class: "placeholder pixel" }, "ไม่พบ Minecraft Bedrock บนเครื่องนี้"));
    return;
  }

  // Auto profile: addons tab → "Shared Add-ons", worlds tab → user profile.
  // (dropdown still works as a manual override for the current tab)
  const sharedIdx = profiles.findIndex((p) => p.name === "Shared Add-ons");
  const userIdx = profiles.findIndex((p) => p.name.startsWith("User:"));
  const autoProfileFor = (tab) => {
    if (tab === "addons" && sharedIdx >= 0) return sharedIdx;
    if (tab === "worlds" && userIdx >= 0) return userIdx;
    return curProfile;
  };
  curProfile = autoProfileFor(curTab);

  const sel = el("select", { onchange: (e) => { curProfile = +e.target.value; loadContent(); } },
    ...profiles.map((p, i) => el("option", { value: i }, p.name)));
  sel.value = String(curProfile);
  main.append(el("div", { class: "fm-profile-bar" },
    el("span", { class: "field-hint" }, "โปรไฟล์:"), sel));

  // Search & Filter Toolbar
  const searchInput = el("input", { type: "text", placeholder: "ค้นหา...", value: searchQuery });
  searchInput.addEventListener("input", (e) => {
    searchQuery = e.target.value.toLowerCase();
    if (curTab === "addons") renderPacks();
    else renderWorlds();
  });

  const filterSelect = el("select", { style: "width:auto;" }, 
    el("option", { value: "all" }, "ทั้งหมด (BP/RP)"),
    el("option", { value: "bp" }, "เฉพาะ BP"),
    el("option", { value: "rp" }, "เฉพาะ RP")
  );
  filterSelect.value = filterType;
  filterSelect.addEventListener("change", (e) => {
    filterType = e.target.value;
    if (curTab === "addons") renderPacks();
  });

  const sortSelect = el("select", { style: "width:auto;" },
    el("option", { value: "mtime" }, "เรียงตาม: เวลา (ล่าสุดก่อน)"),
    el("option", { value: "name" }, "เรียงตาม: ชื่อ (A-Z)")
  );
  sortSelect.value = sortBy;
  sortSelect.addEventListener("change", (e) => {
    sortBy = e.target.value;
    if (curTab === "worlds") renderWorlds();
  });

  const updateToolbar = () => {
    if (curTab === "addons") {
      filterSelect.style.display = "";
      sortSelect.style.display = "none";
    } else {
      filterSelect.style.display = "none";
      sortSelect.style.display = "";
    }
  };
  
  const toolbar = el("div", { class: "toolbar" }, searchInput, filterSelect, sortSelect);

  const mkTab = (id, label) => {
    const b = el("button", { class: "fm-tab" + (id === curTab ? " active" : "") }, label);
    b.addEventListener("click", () => {
      curTab = id;
      selectedPaths.clear();
      searchQuery = "";
      searchInput.value = "";
      curProfile = autoProfileFor(id);
      sel.value = String(curProfile);
      main.querySelectorAll(".fm-tab").forEach(t => t.classList.toggle("active", t === b));
      updateToolbar();
      loadContent();
    });
    return b;
  };
  main.append(el("div", { class: "fm-tabs" },
    mkTab("addons", "ADD-ONS"), mkTab("worlds", "WORLDS")));
    
  main.append(toolbar);
  updateToolbar();

  contentEl = el("div", {});
  main.append(contentEl);
  await loadContent();

  // มาจาก palette (#/filemanager?world=<path>) → สลับไปแท็บโลกแล้วเปิดโลกนั้น
  const worldParam = params && params.get("world");
  if (worldParam) {
    curTab = "worlds";
    selectedPaths.clear();
    searchQuery = "";
    searchInput.value = "";
    curProfile = autoProfileFor("worlds");
    sel.value = String(curProfile);
    main.querySelectorAll(".fm-tab").forEach(t => t.classList.toggle("active", t.textContent.trim() === "WORLDS"));
    updateToolbar();
    await loadContent();
    const w = allWorlds.find(x => x.path === worldParam)
      || { path: worldParam, name: worldParam.split(/[\\/]/).pop() };
    openWorld(w);
  }
}
