// Thin fetch wrapper + native-dialog helper.

export const getApiBase = () => window.HS_API_BASE || "";

async function req(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(getApiBase() + path, opts);
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = (data && data.detail) || res.statusText;
    const err = new Error(detail);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  get: (p) => req("GET", p),
  post: (p, b) => req("POST", p, b),
};

// File/folder picker — opens the themed in-app explorer (ui/explorer.js),
// never a native OS dialog. Returns array of paths ([] if cancelled).
// `filters` accepts legacy "Addon (*.mcaddon)" strings or plain ".ext" entries.
export async function pickPath({ mode = "open_file", filters, directory } = {}) {
  const { pickInApp } = await import("./ui/explorer.js");
  const exts = [];
  for (const f of filters || []) {
    for (const m of String(f).matchAll(/\*(\.[A-Za-z0-9]+)/g)) exts.push(m[1].toLowerCase());
    if (/^\.[A-Za-z0-9]+$/.test(String(f).trim())) exts.push(String(f).trim().toLowerCase());
  }
  return pickInApp({ mode, exts, startDir: directory || "" });
}

export async function pickSingle(opts) {
  const paths = await pickPath(opts);
  return paths[0] || null;
}

// Renders a compact pass/fail line from a checker.check_addon() result
// ({ok, errors, warnings, issues}). Returns null if no validation was run.
export function renderValidation(validation) {
  if (!validation) return null;
  const { ok, errors, warnings, issues } = validation;
  const cls = ok ? "log-ok" : "log-err";
  const head = ok
    ? `✅ ตรวจสอบผ่าน — 0 error, ${warnings} warning`
    : `❌ ตรวจสอบพบปัญหา — ${errors} error, ${warnings} warning`;
  const lines = [head];
  for (const i of issues || []) {
    lines.push(`  [${i.level === "error" ? "ERROR" : "WARN"}] ${i.message}${i.file ? " · " + i.file : ""}`);
  }
  return el("span", { class: cls }, "\n\n" + lines.join("\n"));
}

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c == null) continue;
    node.append(c.nodeType ? c : document.createTextNode(c));
  }
  return node;
}
