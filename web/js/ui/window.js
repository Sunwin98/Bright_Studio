// Reusable retro-OS floating window + confirm dialog (Neon Yokochō theme).
// Styles live in app.css (.hs-window*). Used by the File Manager world drill-in
// and any future in-app dialog.
import { el } from "../api.js";
import { icon } from "./icons.js";

// openWindow({ title, jp, body }) → { close, body }
// `body` (in) is a DOM node or string rendered inside the window.
export function openWindow({ title = "WINDOW", jp = "", body = null, width } = {}) {
  const bodyEl = el("div", { class: "hs-window-body" });
  if (body != null) bodyEl.append(body.nodeType ? body : document.createTextNode(body));

  const win = el("div", { class: "hs-window" },
    el("div", { class: "hs-window-titlebar" },
      el("div", { class: "hs-window-title" },
        el("span", {}, title),
        jp ? el("span", { class: "jp" }, jp) : null,
      ),
      el("button", { class: "hs-window-close", title: "ปิด" }, icon("close", { size: 15 })),
    ),
    bodyEl,
  );
  if (width) win.style.width = width;

  const overlay = el("div", { class: "hs-window-overlay" }, win);

  const close = () => {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  };
  const onKey = (e) => { if (e.key === "Escape") close(); };

  win.querySelector(".hs-window-close").addEventListener("click", close);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });
  document.addEventListener("keydown", onKey);

  document.body.append(overlay);
  return { close, body: bodyEl, win };
}

// confirmDialog(...) → Promise<boolean>
export function confirmDialog({ title = "ยืนยัน", jp = "確認", message = "", confirmLabel = "ตกลง", danger = false } = {}) {
  return new Promise((resolve) => {
    const body = el("div", {},
      el("div", { style: "margin-bottom:18px; line-height:1.6;" }, message),
      el("div", { style: "display:flex; gap:10px; justify-content:flex-end;" },
        el("button", { class: "btn-ghost", onclick: () => { ctl.close(); resolve(false); } }, "ยกเลิก"),
        el("button", { class: danger ? "btn-danger" : "btn-primary", onclick: () => { ctl.close(); resolve(true); } }, confirmLabel),
      ),
    );
    const ctl = openWindow({ title, jp, body, width: "min(440px, 90vw)" });
  });
}
