// Right-click context menu (Neon Yokochō theme) — the glue between tools.
// showContextMenu(x, y, items)
//   items: [{ label, icon?, danger?, hint?, onClick }] หรือ "-" (เส้นคั่น)
// ปิดเอง: คลิกที่อื่น / Esc / เลือกเมนู. เปิดซ้อน = ปิดอันเก่าก่อน.
import { el } from "../api.js";
import { icon } from "./icons.js";

let current = null;

export function closeContextMenu() {
  if (current) { current.remove(); current = null; }
  document.removeEventListener("click", closeContextMenu);
  document.removeEventListener("contextmenu", closeContextMenu);
  document.removeEventListener("keydown", onKey);
}

function onKey(e) { if (e.key === "Escape") closeContextMenu(); }

export function showContextMenu(x, y, items) {
  closeContextMenu();
  const menu = el("div", { class: "hs-ctx" });
  for (const it of items) {
    if (it === "-") { menu.append(el("div", { class: "hs-ctx-sep" })); continue; }
    if (!it) continue;
    const row = el("div", { class: "hs-ctx-item" + (it.danger ? " danger" : "") },
      it.icon ? icon(it.icon, { size: 15 }) : el("span", { class: "hs-ctx-noicon" }),
      el("span", { class: "hs-ctx-label" }, it.label),
      it.hint ? el("span", { class: "hs-ctx-hint" }, it.hint) : null,
    );
    row.addEventListener("click", (e) => {
      e.stopPropagation();
      closeContextMenu();
      it.onClick && it.onClick();
    });
    menu.append(row);
  }
  document.body.append(menu);
  current = menu;

  // clamp ให้อยู่ในจอ
  const r = menu.getBoundingClientRect();
  const px = Math.min(x, window.innerWidth - r.width - 8);
  const py = Math.min(y, window.innerHeight - r.height - 8);
  menu.style.left = Math.max(4, px) + "px";
  menu.style.top = Math.max(4, py) + "px";

  // ปิดเมื่อคลิกที่อื่น — ผูกหลัง event ปัจจุบันจบ กันปิดตัวเองทันที
  setTimeout(() => {
    document.addEventListener("click", closeContextMenu);
    document.addEventListener("contextmenu", closeContextMenu);
    document.addEventListener("keydown", onKey);
  }, 0);
  return menu;
}

// นำทางไปหน้าอื่นพร้อม payload — ถ้า hash เดิมซ้ำ ให้บังคับ re-route
export function gotoPage(hash) {
  const target = "#/" + hash;
  if (location.hash === target) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  } else {
    location.hash = target;
  }
}
