import { api, el, pickSingle, resolveDroppedFile } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";

let pairs = [];

export function render(main) {
  pairs = [];
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "รวม Addon"),
    el("div", { class: "page-desc" }, "รวมหลาย skin addon เป็นชุดเดียว (ชี้โฟลเดอร์ที่มี &lt;name&gt;_BP/&lt;name&gt;_RP)")
  ));

  const src = compactDropzone("ลากโฟลเดอร์แหล่ง addon มาวาง หรือคลิกเพื่อเลือก", [], "", "folder");
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
    if (!path) { toast.error("เลือกโฟลเดอร์"); return; }
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
    if (selected.length < 2) { toast.error("เลือกอย่างน้อย 2 addon"); return; }
    mergeBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังรวม...";
    const t = toast.progress("กำลังรวม addon...");
    try {
      const r = await api.post("/api/merger/merge", { pairs: selected, merged_name: nameInput.value.trim() || "MergedSkins" });
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, (r.log || []).join("\n")));
      logBox.append(el("span", {}, `\n\n📁 ${r.merged_path}\n📊 รวม ${r.total_files} ไฟล์`));
      t.success(`รวมสำเร็จ (${r.total_files} ไฟล์)`);
    } catch (e) {
      logBox.innerHTML = ""; logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
      t.error("รวมไม่สำเร็จ: " + e.message);
    } finally { mergeBtn.disabled = false; }
  });
}

function compactDropzone(placeholder, filters, initialValue = "", mode = "open_file") {
  let value = initialValue;
  
  const iconEl = el("span", { class: "cd-icon" }, icon(mode === "folder" ? "folder" : "upload", { size: 14 }));
  const labelEl = el("span", { class: "cd-label" }, value ? value.split(/[\\/]/).pop() : placeholder);
  if (value) {
    labelEl.style.color = "var(--text)";
  }

  const node = el("div", { class: "compact-dropzone" },
    iconEl,
    labelEl
  );
  node.title = value || placeholder;

  const updateValue = (newVal) => {
    value = newVal;
    labelEl.textContent = value ? value.split(/[\\/]/).pop() : placeholder;
    labelEl.style.color = value ? "var(--text)" : "";
    node.title = value || placeholder;
  };

  const getParentDir = (filePath) => {
    if (!filePath) return "";
    const lastSlash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
    return lastSlash !== -1 ? filePath.substring(0, lastSlash) : "";
  };

  node.addEventListener("click", async () => {
    try {
      const directory = getParentDir(value);
      const p = await pickSingle({ mode, filters: mode === "folder" ? undefined : filters, directory });
      if (p) {
        updateValue(p);
        node.dispatchEvent(new Event("change"));
      }
    } catch (e) {
      toast.error("เลือกโฟลเดอร์ไม่ได้: " + e.message);
    }
  });

  node.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    node.classList.add("dragover");
  });
  node.addEventListener("dragleave", (e) => {
    e.stopPropagation();
    node.classList.remove("dragover");
  });
  node.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    node.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      const fileName = file.path || file.name || "";
      const pathLower = fileName.toLowerCase();
      let isValid = true;
      if (mode !== "folder" && filters && filters.length > 0) {
        const allowedExts = [];
        for (const f of filters) {
          for (const m of String(f).matchAll(/\*(\.[A-Za-z0-9]+)/g)) {
            allowedExts.push(m[1].toLowerCase());
          }
        }
        if (allowedExts.length > 0) {
          isValid = allowedExts.some(ext => pathLower.endsWith(ext));
        }
      }
      if (isValid) {
        try {
          const localPath = await resolveDroppedFile(file);
          updateValue(localPath);
          node.dispatchEvent(new Event("change"));
        } catch (err) {
          toast.error(`นำเข้าโฟลเดอร์ล้มเหลว: ${err.message}`);
        }
      } else {
        toast.error(`ไฟล์ไม่ตรงกับประเภทที่กำหนดสำหรับช่องนี้`);
      }
    }
  });

  return {
    node,
    value: () => value,
    setValue: (v) => updateValue(v)
  };
}
