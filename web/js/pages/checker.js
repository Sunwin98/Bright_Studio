import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";

export function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ตรวจสอบ Addon"),
    el("div", { class: "page-desc" }, "หา error ก่อนเข้าเกม — วางไฟล์ .mcaddon/.zip หรือโฟลเดอร์ ระบบแยก BP/RP ให้เอง")
  ));

  // เลือกแหล่งเดียว: ไฟล์ .mcaddon/.zip หรือโฟลเดอร์ → /api/packio/inspect แยกให้
  const srcInput = el("input", { type: "text", placeholder: "ไฟล์ .mcaddon/.zip หรือโฟลเดอร์ addon" });
  const pickFileBtn = el("button", { class: "btn-ghost btn-sm" }, icon("document", { size: 15 }), " เลือกไฟล์");
  const pickDirBtn = el("button", { class: "btn-ghost btn-sm" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const detected = el("div", { class: "field-hint", style: "min-height:18px;" }, "");
  const checkBtn = el("button", { class: "btn-primary" }, icon("check-circle", { size: 15 }), " ตรวจสอบ");

  let resolved = { bp_path: null, rp_path: null };

  const inspect = async () => {
    const p = srcInput.value.trim();
    resolved = { bp_path: null, rp_path: null };
    if (!p) { detected.textContent = ""; return; }
    detected.textContent = "กำลังแยก BP/RP...";
    try {
      const r = await api.post("/api/packio/inspect", { path: p });
      resolved = r;
      const parts = [];
      for (const pk of r.packs) parts.push(`${pk.type === "behavior" ? "BP" : "RP"}: ${pk.name}`);
      const shown = parts.slice(0, 4).join(" · ") + (parts.length > 4 ? ` · …อีก ${parts.length - 4} แพ็ค` : "");
      detected.textContent = parts.length ? "พบ → " + shown : "ไม่พบแพ็คข้างใน (ไม่มี manifest.json)";
      detected.className = parts.length ? "field-hint log-ok" : "field-hint log-warn";
    } catch (e) {
      detected.textContent = "แยกไม่ได้: " + e.message;
      detected.className = "field-hint log-err";
    }
  };

  pickFileBtn.addEventListener("click", async () => {
    const p = await pickSingle({ mode: "open_file", filters: [".mcaddon", ".mcpack", ".zip"] });
    if (p) { srcInput.value = p; inspect(); }
  });
  pickDirBtn.addEventListener("click", async () => {
    const p = await pickSingle({ mode: "folder" });
    if (p) { srcInput.value = p; inspect(); }
  });
  srcInput.addEventListener("change", inspect);

  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "เลือก addon"),
    el("div", { class: "field" },
      el("label", {}, "ไฟล์หรือโฟลเดอร์ (รับ .mcaddon / .mcpack / .zip / โฟลเดอร์)"),
      el("div", { class: "file-pick" }, srcInput, pickFileBtn, pickDirBtn)),
    detected,
    el("div", { style: "margin-top:10px;" }, checkBtn),
  ));

  const result = el("div", {});
  main.append(result);

  // มาจากหน้าอื่น (#/checker?open=<path>) → ใส่พาธ + แยก BP/RP ให้เลย
  const openParam = params && params.get("open");
  if (openParam) {
    srcInput.value = openParam;
    inspect();
  }

  checkBtn.addEventListener("click", async () => {
    if (!resolved.bp_path && !resolved.rp_path) {
      if (srcInput.value.trim()) await inspect();
      if (!resolved.bp_path && !resolved.rp_path) { alert("ยังไม่พบ BP/RP — เลือกไฟล์หรือโฟลเดอร์ addon ก่อน"); return; }
    }
    checkBtn.disabled = true;
    result.innerHTML = '<div class="empty">กำลังตรวจ...</div>';
    try {
      const r = await api.post("/api/checker/check", { bp_path: resolved.bp_path, rp_path: resolved.rp_path });
      result.innerHTML = "";
      const head = r.ok
        ? el("div", { class: "log-ok", style: "font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px" }, icon("check-circle", { size: 18 }), `ผ่าน — 0 error, ${r.warnings} warning`)
        : el("div", { class: "log-err", style: "font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px" }, icon("x-circle", { size: 18 }), `พบ ${r.errors} error, ${r.warnings} warning`);
      const card = el("div", { class: "card" }, head);
      if (!r.issues.length) card.append(el("div", { class: "empty" }, "ไม่พบปัญหา 🎉"));
      for (const i of r.issues) {
        const color = i.level === "error" ? "var(--red)" : "var(--yellow)";
        card.append(el("div", { style: "padding:6px 0;border-bottom:1px solid var(--border)" },
          el("span", { style: `color:${color};font-weight:700;margin-right:8px` }, i.level === "error" ? "ERROR" : "WARN"),
          el("span", {}, i.message),
          i.file ? el("span", { class: "field-hint", style: "margin-left:8px" }, "· " + i.file) : null,
        ));
      }
      result.append(card);
    } catch (e) {
      result.innerHTML = `<div class="empty">ตรวจไม่ได้: ${e.message}</div>`;
    } finally {
      checkBtn.disabled = false;
    }
  });
}
