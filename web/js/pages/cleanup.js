import { api, el } from "../api.js";
import { icon } from "../ui/icons.js";

function fmtSize(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b / 1024).toFixed(0) + " KB";
  if (b < 1073741824) return (b / 1048576).toFixed(1) + " MB";
  return (b / 1073741824).toFixed(2) + " GB";
}

export async function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ล้างขยะ"),
    el("div", { class: "page-desc" }, "หาโฟลเดอร์ backup/สำเนาซ้อน/cache ใน stores — เลือกลบเองเท่านั้น (ไม่ลบอัตโนมัติ)")
  ));

  const scanBtn = el("button", { class: "btn-primary" }, icon("search", { size: 15 }), " สแกนหาขยะ");
  const summary = el("span", { class: "count-pill" }, "");
  main.append(el("div", { class: "toolbar" }, scanBtn, summary));

  const listCard = el("div", { class: "card", style: "display:none" });
  main.append(listCard);

  const checks = [];

  const doScan = async () => {
    scanBtn.disabled = true;
    listCard.style.display = "block";
    listCard.innerHTML = '<div class="empty">สแกน...</div>';
    checks.length = 0;
    try {
      const r = await api.get("/api/cleanup/scan");
      const items = r.candidates || [];
      summary.textContent = `พบ ${items.length} รายการ · รวม ${fmtSize(r.total_bytes)}`;
      listCard.innerHTML = "";
      const delBtn = el("button", { class: "btn-primary btn-sm" }, icon("trash", { size: 14 }), " ลบที่เลือก");
      const status = el("span", { class: "spinner-inline", style: "margin-left:10px" }, "");
      listCard.append(el("div", { class: "toolbar" }, delBtn, status));
      if (!items.length) { listCard.append(el("div", { class: "empty" }, "ไม่พบขยะ 🎉")); scanBtn.disabled = false; return; }
      for (const c of items) {
        const cb = el("input", { type: "checkbox" });
        checks.push({ cb, path: c.path });
        listCard.append(el("div", { style: "padding:8px 0;border-bottom:1px solid var(--border);display:flex;gap:10px;align-items:center" },
          cb,
          el("div", { style: "flex:1;min-width:0" },
            el("div", { style: "font-weight:600;color:var(--text-bright)" }, c.reason + " · " + fmtSize(c.size_bytes)),
            el("div", { class: "field-hint", style: "word-break:break-all" }, c.path),
          ),
        ));
      }
      delBtn.addEventListener("click", async () => {
        const sel = checks.filter(c => c.cb.checked).map(c => c.path);
        if (!sel.length) { alert("เลือกรายการก่อน"); return; }
        if (!confirm(`ลบ ${sel.length} โฟลเดอร์ถาวร?`)) return;
        status.textContent = "กำลังลบ...";
        try {
          const res = await api.post("/api/projects/delete", { paths: sel });
          status.textContent = `✅ ลบแล้ว ${res.removed.length}`;
          await doScan();
        } catch (e) { status.textContent = "❌ " + e.message; }
      });
    } catch (e) {
      listCard.innerHTML = `<div class="empty">สแกนไม่ได้: ${e.message}</div>`;
    } finally { scanBtn.disabled = false; }
  };

  scanBtn.addEventListener("click", doScan);
}
