// In-app file explorer (Neon Yokochō theme) — replaces native dialogs and
// Windows Explorer pop-ups. Backed by the read-only /api/fs API.
//
//   pickInApp({ mode, exts, startDir, title })  → Promise<string[]>
//     mode: "open_file" | "open_files" | "folder" | "browse"
//     exts: [".mcaddon", ".zip"] filter for file modes (optional)
//   browsePath(path)  → view-only window at that folder
import { api, el } from "../api.js";
import { openWindow } from "./window.js";
import { icon } from "./icons.js";

const EXT_ICONS = {
  ".mcaddon": "puzzle", ".mcpack": "box", ".zip": "archive-zip",
  ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
  ".json": "code", ".js": "code", ".txt": "document", ".md": "document",
  ".mp3": "music", ".ogg": "music", ".wav": "music",
};

function fmtSize(n) {
  if (n == null) return "";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / 1024 / 1024).toFixed(1) + " MB";
}

export function pickInApp({ mode = "open_file", exts = [], startDir = "", title } = {}) {
  const browse = mode === "browse";
  const folderMode = mode === "folder";
  const multi = mode === "open_files";

  return new Promise(async (resolve) => {
    let curPath = "";
    let selected = new Map(); // path -> name
    let done = false;
    const finish = (paths) => { if (!done) { done = true; ctl.close(); resolve(paths); } };

    // --- layout ---
    const sidebar = el("div", { class: "fx-sidebar" });
    const crumbs = el("div", { class: "fx-crumbs" });
    const listEl = el("div", { class: "fx-list" });
    const status = el("div", { class: "fx-status" }, browse ? "โหมดดูไฟล์" : "ยังไม่ได้เลือก");
    const upBtn = el("button", { class: "btn-ghost btn-sm", title: "ขึ้นหนึ่งชั้น" }, icon("arrow-up", { size: 14 }), " ขึ้น");
    const searchIn = el("input", { type: "text", placeholder: "กรองชื่อ...", class: "fx-filter" });

    const okBtn = browse ? null : el("button", { class: "btn-primary" },
      folderMode ? "เลือกโฟลเดอร์นี้" : "เลือก");
    const cancelBtn = el("button", { class: "btn-ghost" }, browse ? "ปิด" : "ยกเลิก");
    const revealBtn = el("button", { class: "btn-ghost btn-sm", title: "เปิดใน Windows Explorer (ถ้าจำเป็น)" }, icon("external-link", { size: 14 }), " Explorer");

    const footer = el("div", { class: "fx-footer" },
      status,
      el("div", { class: "fx-actions" }, revealBtn, cancelBtn, okBtn),
    );

    const body = el("div", { class: "fx-root" },
      sidebar,
      el("div", { class: "fx-main" },
        el("div", { class: "fx-pathbar" }, upBtn, crumbs, searchIn),
        listEl,
        footer,
      ),
    );

    const ctl = openWindow({
      title: title || (browse ? "FILE BROWSER" : folderMode ? "เลือกโฟลเดอร์" : "เลือกไฟล์"),
      jp: "ファイル",
      body,
      width: "min(860px, 94vw)",
    });
    // openWindow resolves close via ✕/overlay/Esc — treat as cancel.
    const obs = new MutationObserver(() => {
      if (!document.body.contains(ctl.win)) { obs.disconnect(); if (!done) { done = true; resolve([]); } }
    });
    obs.observe(document.body, { childList: true, subtree: false });

    cancelBtn.addEventListener("click", () => finish([]));
    revealBtn.addEventListener("click", async () => {
      try { await api.post("/api/fm/reveal", { path: curPath }); }
      catch { try { await api.post("/api/projects/open-folder", { path: curPath }); } catch {} }
    });
    if (okBtn) okBtn.addEventListener("click", () => {
      if (folderMode) return finish([curPath]);
      if (selected.size) return finish([...selected.keys()]);
      status.textContent = "ยังไม่ได้เลือกไฟล์";
    });

    let lastEntries = { dirs: [], files: [] };

    const renderList = () => {
      const q = searchIn.value.trim().toLowerCase();
      listEl.innerHTML = "";
      const frag = document.createDocumentFragment();
      const rows = [
        ...lastEntries.dirs.map(d => ({ ...d, isDir: true })),
        ...lastEntries.files.map(f => ({ ...f, isDir: false })),
      ].filter(r => !q || r.name.toLowerCase().includes(q));

      if (!rows.length) {
        listEl.append(el("div", { class: "empty" }, "โฟลเดอร์ว่าง"));
        return;
      }
      for (const r of rows) {
        const iconName = r.isDir ? "folder" : (EXT_ICONS[r.ext] || "document");
        const item = el("div", { class: "fx-item" + (selected.has(r.path) ? " selected" : "") },
          el("div", { class: "fx-item-icon" }, icon(iconName, { size: 26 })),
          el("div", { class: "fx-item-name", title: r.name }, r.name),
          r.isDir ? null : el("div", { class: "fx-item-size" }, fmtSize(r.size)),
        );
        item.addEventListener("dblclick", () => {
          if (r.isDir) load(r.path);
          else if (!browse && !folderMode) finish([r.path]);
        });
        item.addEventListener("click", () => {
          if (r.isDir) { load(r.path); return; }
          if (browse || folderMode) return;
          if (!multi) selected.clear();
          if (selected.has(r.path)) selected.delete(r.path);
          else selected.set(r.path, r.name);
          status.textContent = selected.size
            ? [...selected.values()].join(", ")
            : "ยังไม่ได้เลือก";
          renderList();
        });
        frag.append(item);
      }
      listEl.append(frag);
    };

    const renderCrumbs = () => {
      crumbs.innerHTML = "";
      const parts = curPath.replace(/\\+$/, "").split("\\");
      let acc = "";
      parts.forEach((part, i) => {
        acc = i === 0 ? part + "\\" : acc + (acc.endsWith("\\") ? "" : "\\") + part;
        const target = acc;
        crumbs.append(el("span", { class: "fx-crumb", onclick: () => load(target) }, part || "\\"));
        if (i < parts.length - 1) crumbs.append(el("span", { class: "fx-crumb-sep" }, "›"));
      });
    };

    let parentPath = null;
    async function load(path) {
      listEl.innerHTML = '<div class="loading">กำลังโหลด...</div>';
      try {
        const d = await api.get(`/api/fs/list?path=${encodeURIComponent(path)}&exts=${encodeURIComponent(exts.join(","))}`);
        curPath = d.path;
        parentPath = d.parent;
        lastEntries = { dirs: d.dirs, files: d.files };
        renderCrumbs();
        renderList();
      } catch (e) {
        listEl.innerHTML = "";
        listEl.append(el("div", { class: "log-err", style: "padding:12px" }, "เปิดไม่ได้: " + e.message));
      }
    }

    upBtn.addEventListener("click", () => { if (parentPath) load(parentPath); });
    searchIn.addEventListener("input", renderList);

    // --- sidebar (quick access + drives) ---
    try {
      const r = await api.get("/api/fs/roots");
      sidebar.append(el("div", { class: "fx-side-head" }, "ทางลัด"));
      for (const q of r.quick) {
        sidebar.append(el("div", { class: "fx-side-item", onclick: () => load(q.path) },
          icon(q.icon, { size: 16 }), el("span", { class: "fx-side-label", title: q.path }, q.name)));
      }
      sidebar.append(el("div", { class: "fx-side-head" }, "ไดรฟ์"));
      for (const d of r.drives) {
        sidebar.append(el("div", { class: "fx-side-item", onclick: () => load(d.path) },
          icon("drive", { size: 16 }), el("span", { class: "fx-side-label" }, d.name)));
      }
      await load(startDir || (r.quick[0] ? r.quick[0].path : (r.drives[0] || {}).path || "C:\\"));
    } catch (e) {
      listEl.innerHTML = "";
      listEl.append(el("div", { class: "log-err", style: "padding:12px" }, "โหลดไม่ได้: " + e.message));
    }
  });
}

// View-only browse window at a path (used by File Manager "เปิดโฟลเดอร์").
export function browsePath(path, title = "FILE BROWSER") {
  return pickInApp({ mode: "browse", startDir: path, title });
}
