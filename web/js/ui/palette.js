// Ctrl+K / Ctrl+P global search palette. Overlay with a single input + grouped
// results (projects / local addons / worlds / docs). Arrow keys + Enter or mouse
// navigate; Esc or click-outside closes. Data is fetched once per open session
// (cached) so re-filtering is instant.
import { api, el } from "../api.js";
import { icon } from "./icons.js";
import { gotoPage } from "./contextmenu.js";

let overlay = null;      // current overlay element (null = closed)
let cache = null;        // { projects, addons, worlds, docs } for this session

const GROUPS = [
  { key: "project", title: "โปรเจกต์", icon: "folder" },
  { key: "addon", title: "Addon ในเครื่อง", icon: "box" },
  { key: "world", title: "โลก", icon: "globe" },
  { key: "doc", title: "เอกสาร", icon: "book" },
];

async function loadData() {
  if (cache) return cache;
  const settled = await Promise.allSettled([
    api.get("/api/projects?zone=skin"),
    api.get("/api/projects?zone=skill"),
    api.get("/api/fm/profiles"),
    api.get("/api/knowledge"),
  ]);
  const val = (i, key, def) =>
    settled[i].status === "fulfilled" && settled[i].value ? (settled[i].value[key] || def) : def;

  const skin = val(0, "projects", []);
  const skill = val(1, "projects", []);
  const profiles = val(2, "profiles", []);
  const docs = val(3, "docs", []);

  const sharedIdx = profiles.findIndex((p) => p.name === "Shared Add-ons");
  const userIdx = profiles.findIndex((p) => p.name.startsWith("User:"));
  const addonIdx = sharedIdx >= 0 ? sharedIdx : 0;
  const worldIdx = userIdx >= 0 ? userIdx : 0;

  let addons = [], worlds = [];
  if (profiles.length) {
    const [aRes, wRes] = await Promise.allSettled([
      api.get(`/api/fm/addons?profile=${addonIdx}`),
      api.get(`/api/fm/worlds?profile=${worldIdx}`),
    ]);
    if (aRes.status === "fulfilled" && aRes.value) addons = aRes.value.packs || [];
    if (wRes.status === "fulfilled" && wRes.value) worlds = wRes.value.worlds || [];
  }

  const projects = [
    ...skin.map((p) => ({ ...p, _zone: "skin" })),
    ...skill.map((p) => ({ ...p, _zone: "skill" })),
  ];
  cache = { projects, addons, worlds, docs };
  return cache;
}

function buildItems(data) {
  const out = [];
  for (const p of data.projects) {
    const paths = p.paths || {};
    const open = paths.bp || paths.folder || paths.mcaddon || paths.rp || "";
    out.push({
      type: "project", name: p.name, hint: p._zone || p.store || "", icon: "folder",
      action: () => gotoPage("scriptlab?open=" + encodeURIComponent(open)),
    });
  }
  for (const a of data.addons) {
    out.push({
      type: "addon", name: a.name, hint: a.type === "behavior" ? "BP" : "RP", icon: "box",
      action: () => gotoPage("scriptlab?open=" + encodeURIComponent(a.path)),
    });
  }
  for (const w of data.worlds) {
    out.push({
      type: "world", name: w.name, hint: "โลก", icon: "globe",
      action: () => gotoPage("filemanager?world=" + encodeURIComponent(w.path)),
    });
  }
  for (const d of data.docs) {
    out.push({
      type: "doc", name: d.title, hint: d.group || "", icon: "book",
      action: () => gotoPage("knowledge?doc=" + encodeURIComponent(d.path)),
    });
  }
  return out;
}

export function closePalette() {
  if (overlay) { overlay.remove(); overlay = null; }
}

export async function openPalette() {
  if (overlay) return; // already open — guard against double-trigger

  overlay = el("div", { class: "hs-palette-overlay" });
  const box = el("div", { class: "hs-palette" });
  const input = el("input", {
    class: "hs-palette-input", type: "text",
    placeholder: "ค้นหาโปรเจกต์ / addon / โลก / เอกสาร… (Esc ปิด)",
  });
  const results = el("div", { class: "hs-palette-results" });
  box.append(input, results);
  overlay.append(box);
  document.body.append(overlay);
  input.focus();

  overlay.addEventListener("click", (e) => { if (e.target === overlay) closePalette(); });

  let items = [];
  let rows = [];   // [{ el, action }]
  let active = 0;

  const highlight = () => {
    rows.forEach((r, i) => r.el.classList.toggle("active", i === active));
    if (rows[active]) rows[active].el.scrollIntoView({ block: "nearest" });
  };

  const draw = () => {
    const q = input.value.trim().toLowerCase();
    results.innerHTML = "";
    rows = [];
    for (const g of GROUPS) {
      const matched = items
        .filter((it) => it.type === g.key && (!q || it.name.toLowerCase().includes(q)))
        .slice(0, 6);
      if (!matched.length) continue;
      results.append(el("div", { class: "hs-palette-group" }, g.title));
      for (const it of matched) {
        const row = el("div", { class: "hs-palette-row" },
          el("span", { class: "hs-palette-row-icon" }, icon(it.icon, { size: 16 })),
          el("span", { class: "hs-palette-row-name", title: it.name }, it.name),
          it.hint ? el("span", { class: "hs-palette-row-hint" }, it.hint) : null);
        const idx = rows.length;
        row.addEventListener("mousemove", () => { active = idx; highlight(); });
        row.addEventListener("click", () => { const a = it.action; closePalette(); a(); });
        rows.push({ el: row, action: it.action });
        results.append(row);
      }
    }
    if (!rows.length) {
      results.append(el("div", { class: "hs-palette-empty" },
        items.length ? "ไม่พบผลลัพธ์" : "กำลังโหลด…"));
    }
    active = 0;
    highlight();
  };

  input.addEventListener("input", draw);
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (rows.length) { active = (active + 1) % rows.length; highlight(); }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (rows.length) { active = (active - 1 + rows.length) % rows.length; highlight(); }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (rows[active]) { const a = rows[active].action; closePalette(); a(); }
    } else if (e.key === "Escape") {
      e.preventDefault();
      closePalette();
    }
  });

  draw(); // initial "กำลังโหลด…" state

  const data = await loadData();
  if (!overlay) return; // closed while loading
  items = buildItems(data);
  draw();
}
