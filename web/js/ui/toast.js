// Toast notifications (Neon Yokochō theme) — non-blocking feedback that
// replaces alert()/silent status text for background work. Toasts render
// straight into <body> (not inside a page container), so they survive page
// switches on their own — a long task started on one tab keeps its toast
// visible/updatable even after the user navigates elsewhere.
import { el } from "../api.js";
import { icon } from "./icons.js";

let stack = null;
function ensureStack() {
  if (stack) return stack;
  stack = el("div", { class: "hs-toast-stack" });
  document.body.append(stack);
  return stack;
}

const ICONS = { success: "check-circle", error: "x-circle", info: "book", progress: "refresh" };
const DEFAULT_DURATION = { success: 4200, info: 4200, error: 6500, progress: 0 };

function show(kind, message, { duration } = {}) {
  if (duration === undefined) duration = DEFAULT_DURATION[kind] ?? 4200;

  const iconSlot = el("span", { class: "hs-toast-icon" }, icon(ICONS[kind] || "check-circle", { size: 16 }));
  const msgEl = el("span", { class: "hs-toast-msg" }, message);
  const closeBtn = el("button", { class: "hs-toast-close", title: "ปิด" }, icon("close", { size: 12 }));
  const node = el("div", { class: `hs-toast hs-toast-${kind}` }, iconSlot, msgEl, closeBtn);

  let timer = null;
  const close = () => {
    if (timer) clearTimeout(timer);
    node.classList.remove("hs-toast-in");
    node.classList.add("hs-toast-out");
    setTimeout(() => node.remove(), 200);
  };
  closeBtn.addEventListener("click", close);

  const arm = (ms) => {
    if (timer) clearTimeout(timer);
    timer = ms > 0 ? setTimeout(close, ms) : null;
  };

  ensureStack().append(node);
  requestAnimationFrame(() => node.classList.add("hs-toast-in"));
  arm(duration);

  return {
    node,
    close,
    update(newMessage) { msgEl.textContent = newMessage; },
    // switch kind (e.g. progress -> success) and re-arm auto-dismiss
    settle(newKind, newMessage, newDuration) {
      node.className = `hs-toast hs-toast-${newKind} hs-toast-in`;
      iconSlot.innerHTML = "";
      iconSlot.append(icon(ICONS[newKind] || "check-circle", { size: 16 }));
      if (newMessage !== undefined) msgEl.textContent = newMessage;
      arm(newDuration !== undefined ? newDuration : (DEFAULT_DURATION[newKind] ?? 4200));
    },
  };
}

export const toast = {
  success: (msg, opts) => show("success", msg, opts),
  error: (msg, opts) => show("error", msg, opts),
  info: (msg, opts) => show("info", msg, opts),

  // For work that spans several seconds+ (Meshy generation, deploy, export).
  // Stays open (spinning icon) until you call .success()/.error() on it —
  // safe to call after the user has navigated to a different page/tab.
  progress(msg) {
    const t = show("progress", msg, { duration: 0 });
    return {
      update: (m) => t.update(m),
      success: (m) => t.settle("success", m),
      error: (m) => t.settle("error", m),
      close: t.close,
    };
  },
};
