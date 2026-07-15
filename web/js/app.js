// Shell: sidebar tabs + hash router. Each page module exports render(container).
import { api, el } from "./api.js";
import { setupUI } from "./sound.js";
import { createMascot, setState } from "./mascot.js";
import { icon } from "./ui/icons.js";
import { openPalette } from "./ui/palette.js";
import { mountActiveProjectIndicator } from "./ui/activeProjectIndicator.js";

// Ctrl+K / Ctrl+P → global search palette (module runs once — no dup listeners)
window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "p")) {
    e.preventDefault();
    openPalette();
  }
});

// Sidebar zones: each zone groups its tools and has its own project store.
const ZONES = [
  { label: "หน้าหลัก · ホーム", tabs: [
    { hash: "home",      label: "หน้าแรก",         icon: "home" },
  ]},
  { label: "โซนสกิน · スキン", tabs: [
    { hash: "projects?zone=skin", label: "โปรเจกต์สกิน", icon: "folder" },
    { hash: "skin",      label: "สร้างสกิน",       icon: "palette" },
    { hash: "physics",   label: "ฟิสิกส์",         icon: "waves" },
  ]},
  { label: "โซนสกิล · スキル", tabs: [
    { hash: "projects?zone=skill", label: "โปรเจกต์สกิล", icon: "folder" },
    { hash: "weapon",    label: "อาวุธ & สกิล",    icon: "swords" },
    { hash: "item",      label: "สร้างไอเทม/อาวุธ", icon: "dagger" },
    { hash: "scriptlab", label: "Script Lab",       icon: "sliders" },
    { hash: "scriptbuilder", label: "Script Builder", icon: "puzzle" },
  ]},
  { label: "โซนโมเดล · モデル", tabs: [
    { hash: "modelgen",  label: "โมเดล AI",         icon: "cube" },
  ]},
  { label: "จัดการ · 管理", tabs: [
    { hash: "projects",  label: "โปรเจกต์ทั้งหมด", icon: "archive" },
    { hash: "checker",   label: "ตรวจสอบ Addon",    icon: "check-circle" },
    { hash: "merger",    label: "รวม Addon",        icon: "puzzle" },
    { hash: "cleanup",   label: "ล้างขยะ",          icon: "broom" },
    { hash: "filemanager", label: "จัดการไฟล์",     icon: "folder-open" },
    { hash: "history",   label: "ประวัติไฟล์",      icon: "archive" },
    { hash: "assets",    label: "ดู Asset",         icon: "image" },
  ]},
  { label: "อื่นๆ · その他", tabs: [
    { hash: "knowledge", label: "คลังความรู้",     icon: "book" },
    { hash: "settings",  label: "ตั้งค่า",          icon: "settings" },
  ]},
];

const main = document.getElementById("main");
const tabList = document.getElementById("tab-list");

// ---------- Page cache ----------
// Each hash (path + query, e.g. "scriptlab?open=...") gets its own DOM
// container that survives navigation — render() runs once per unique hash,
// so unsaved form input, scroll position, and any in-flight work (Meshy
// polling, etc.) keep going untouched while the user is on a different tab.
// Switching back just un-hides the same node instead of re-rendering.
const pageCache = new Map(); // raw hash -> container element
const scrollPos = new WeakMap(); // container -> #main.scrollTop when last hidden
const MAX_CACHED_PAGES = 24; // evict least-recently-shown beyond this (memory guard)

function hideAllCachedPages() {
  for (const child of main.children) {
    if (child.style.display !== "none") scrollPos.set(child, main.scrollTop);
    child.style.display = "none";
  }
}

function touchCacheOrder(raw) {
  // Map preserves insertion order — re-insert to mark as most-recently-used.
  const node = pageCache.get(raw);
  if (!node) return;
  pageCache.delete(raw);
  pageCache.set(raw, node);
  while (pageCache.size > MAX_CACHED_PAGES) {
    const oldestKey = pageCache.keys().next().value;
    if (oldestKey === raw) break;
    pageCache.get(oldestKey)?.remove();
    pageCache.delete(oldestKey);
  }
}

function buildTabs() {
  for (const zone of ZONES) {
    const head = document.createElement("li");
    head.className = "tab-zone-head";
    head.textContent = zone.label;
    tabList.append(head);
    for (const t of zone.tabs) {
      const li = el("li", { class: "tab-item" }, el("span", { class: "tab-icon" }, icon(t.icon, { size: 17 })), el("span", {}, t.label));
      li.dataset.hash = t.hash;
      li.addEventListener("click", () => { location.hash = "#/" + t.hash; });
      tabList.append(li);
    }
  }
}

function setActive(raw) {
  for (const li of tabList.querySelectorAll(".tab-item")) {
    li.classList.toggle("active", li.dataset.hash === raw);
  }
}

async function route() {
  const raw = location.hash.replace(/^#\//, "") || "home";
  setActive(raw);

  if (pageCache.has(raw)) {
    hideAllCachedPages();
    const node = pageCache.get(raw);
    node.style.display = "";
    touchCacheOrder(raw);
    main.scrollTop = scrollPos.get(node) || 0;
    return;
  }

  const [id, qs] = raw.split("?");
  const params = new URLSearchParams(qs || "");
  hideAllCachedPages();
  const container = el("div", { class: "page-enter" });
  container.innerHTML = '<div class="loading">กำลังโหลด...</div>';
  main.append(container);
  
  // Cache the container immediately so hideAllCachedPages() can hide it if navigated away mid-load
  pageCache.set(raw, container);
  touchCacheOrder(raw);

  try {
    const mod = await import(`./pages/${id}.js`);
    container.innerHTML = "";
    await mod.render(container, params);
  } catch (e) {
    pageCache.delete(raw); // Evict from cache if rendering failed
    container.innerHTML = `<div class="placeholder">โหลดหน้า "${id}" ไม่ได้<br><small>${e.message}</small></div>`;
    console.error(e);
  }
}

async function checkConn() {
  const dot = document.getElementById("conn-dot");
  const txt = document.getElementById("conn-text");
  try {
    await api.get("/api/health");
    dot.className = "status-dot online";
    txt.textContent = "พร้อมใช้งาน";
  } catch {
    dot.className = "status-dot offline";
    txt.textContent = "ต่อ backend ไม่ได้";
  }
}

// ---------- Custom titlebar (frameless pywebview window) ----------
// pywebview exposes control methods on window.pywebview.api once ready. In a
// plain browser there's no native window, so hide the controls.
function wireTitlebar() {
  const bar = document.getElementById("titlebar");
  if (window.HS_IS_NEU) {
    document.getElementById("tb-min")?.addEventListener("click", () => Neutralino.window.minimize());
    document.getElementById("tb-max")?.addEventListener("click", async () => {
      try {
        const maxed = await Neutralino.window.isMaximized();
        if (maxed) await Neutralino.window.unmaximize();
        else await Neutralino.window.maximize();
      } catch (e) {
        // fallback ignored
      }
    });
    document.getElementById("tb-close")?.addEventListener("click", () =>
      window.hsShutdown ? window.hsShutdown() : Neutralino.app.exit());
    return;
  }
  const call = (fn) => {
    const api = window.pywebview && window.pywebview.api;
    if (api && typeof api[fn] === "function") api[fn]();
  };
  document.getElementById("tb-min")?.addEventListener("click", () => call("win_minimize"));
  document.getElementById("tb-max")?.addEventListener("click", () => call("win_toggle_max"));
  document.getElementById("tb-close")?.addEventListener("click", () => call("win_close"));
  // Feature-detect native window; hide controls in browser dev mode.
  const settle = () => {
    if (!(window.pywebview && window.pywebview.api)) bar.classList.add("no-native");
  };
  window.addEventListener("pywebviewready", settle);
  setTimeout(settle, 800);
}

// ---------- Intro boot overlay ----------
function playIntro() {
  const skipIntro = localStorage.getItem("hs_skip_intro") === "true";
  const boot = document.getElementById("intro-boot");
  if (!boot) return;
  if (skipIntro) {
    boot.remove();
    return;
  }
  const logsEl = document.getElementById("intro-logs");
  const lines = [
    "> BOOTING スタジオ CORE...",
    "> LOADING ASSETS [||||||||] 100%",
    "> NEON SIGNS ONLINE",
    "> ready. ようこそ.",
  ];
  let i = 0;
  const tick = () => {
    if (i < lines.length) {
      const div = document.createElement("div");
      if (i === lines.length - 1) div.className = "ok";
      div.textContent = lines[i++];
      logsEl.append(div);
      setTimeout(tick, 380);
    } else {
      setTimeout(() => {
        boot.classList.add("hide");
        setTimeout(() => boot.remove(), 700);
      }, 350);
    }
  };
  tick();
}

// Apply UI settings
if (localStorage.getItem("hs_theme") === "day") {
  document.body.classList.add("day-mode");
}
if (localStorage.getItem("hs_crt") === "false") {
  const crt = document.getElementById("crt-overlay");
  if (crt) crt.style.display = "none";
}

buildTabs();
wireTitlebar();
playIntro();
mountActiveProjectIndicator(document.getElementById("active-project-slot"));

setupUI();
createMascot();

function startApp() {
  window.addEventListener("hashchange", route);
  if (!location.hash) location.hash = "#/home";
  route();
  checkConn();
}

// HS_IS_NEU ตั้งโดย boot-neutralino.js (window.Neutralino มีเสมอแม้ใน browser —
// เชื่อ flag นี้แทน). HS_BACKEND_READY กัน race ที่ backend พร้อมก่อน module นี้รัน.
if (window.HS_IS_NEU && !window.HS_BACKEND_READY) {
  window.addEventListener("hs-backend-ready", () => {
    setState("happy");
    setTimeout(() => setState("idle"), 2000);
    startApp();
  });
  window.addEventListener("hs-backend-failed", (e) => {
    setState("angry");
    const logs = document.getElementById("intro-logs");
    if (logs) logs.innerHTML += `<div class="log-err">${e.detail || "Backend Start Failed!"}</div>`;
  });
} else {
  startApp();
}
