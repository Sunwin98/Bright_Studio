import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";

let pairs = [];

export function render(main) {
  pairs = [];
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "รวม Addon"),
    el("div", { class: "page-desc" }, "รวมหลาย skin addon เป็นชุดเดียว (ชี้โฟลเดอร์ที่มี &lt;name&gt;_BP/&lt;name&gt;_RP)")
  ));

  const src = pathPicker("โฟลเดอร์ที่มี addon หลายตัว");
  const scanBtn = el("button", { class: "btn-ghost btn-sm" }, icon("search", { size: 15 }), " สแกน");
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "1. แหล่ง addon"),
    el("div", { class: "field" }, el("label", {}, "โฟลเดอร์"), src.node),
    scanBtn,
  ));

  const listCard = el("div", { class: "card", style: "display:none" });
  main.append(listCard);

  const nameInput = el("input", { type: "text", placeholder: "ชื่อ addon รวม" });
  const mergeBtn = el("button", { class: "btn-primary" }, icon("puzzle", { size: 15 }), " รวม");
  const logBox = el("div", { class: "log-box", style: "display:none;margin-top:14px" });
  const mergeCard = el("div", { class: "card", style: "display:none" },
    el("div", { class: "card-title" }, "3. รวม"),
    el("div", { class: "field" }, el("label", {}, "ชื่อ addon รวม"), nameInput),
    mergeBtn, logBox);
  main.append(mergeCard);

  const checks = [];
  scanBtn.addEventListener("click", async () => {
    const path = src.value();
    if (!path) { alert("เลือกโฟลเดอร์"); return; }
    listCard.style.display = "block";
    listCard.innerHTML = '<div class="empty">สแกน...</div>';
    checks.length = 0;
    try {
      const r = await api.get("/api/merger/scan?path=" + encodeURIComponent(path));
      const found = r.pairs || [];
      listCard.innerHTML = "";
      listCard.append(el("div", { class: "card-title" }, `2. เลือก addon (พบ ${found.length})`));
      if (!found.length) { listCard.append(el("div", { class: "empty" }, "ไม่พบ addon (ต้องมี _BP + _RP)")); return; }
      for (const p of found) {
        const cb = el("input", { type: "checkbox" }); cb.checked = true;
        checks.push({ cb, pair: p });
        listCard.append(el("div", { class: "field" }, el("label", { class: "toggle" }, cb, p.name)));
      }
      mergeCard.style.display = "block";
    } catch (e) { listCard.innerHTML = `<div class="empty">สแกนไม่ได้: ${e.message}</div>`; }
  });

  mergeBtn.addEventListener("click", async () => {
    const selected = checks.filter(c => c.cb.checked).map(c => c.pair);
    if (selected.length < 2) { alert("เลือกอย่างน้อย 2 addon"); return; }
    mergeBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังรวม...";
    try {
      const r = await api.post("/api/merger/merge", { pairs: selected, merged_name: nameInput.value.trim() || "MergedSkins" });
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, (r.log || []).join("\n")));
      logBox.append(el("span", {}, `\n\n📁 ${r.merged_path}\n📊 รวม ${r.total_files} ไฟล์`));
    } catch (e) {
      logBox.innerHTML = ""; logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
    } finally { mergeBtn.disabled = false; }
  });
}

function pathPicker(placeholder) {
  const input = el("input", { type: "text", placeholder });
  const btn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
  btn.addEventListener("click", async () => {
    try { const p = await pickSingle({ mode: "folder" }); if (p) input.value = p; }
    catch (e) { if (e.status === 501) input.focus(); else alert("เลือกไม่ได้: " + e.message); }
  });
  return { node: el("div", { class: "file-pick" }, input, btn), value: () => input.value.trim() };
}
