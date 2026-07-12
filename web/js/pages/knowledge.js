import { api, el } from "../api.js";

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "คลังความรู้"),
    el("div", { class: "page-desc" }, "เอกสาร SKILL และคู่มือสร้าง Bedrock addon")
  ));

  const list = el("div", { class: "kb-list" });
  const contentBox = el("div", { class: "kb-content" });
  contentBox.innerHTML = '<div class="empty">เลือกเอกสารจากด้านซ้าย</div>';
  main.append(el("div", { class: "kb-layout" }, list, contentBox));

  list.innerHTML = '<div class="spinner-inline">กำลังโหลด...</div>';

  let docs = [];
  try {
    const data = await api.get("/api/knowledge");
    docs = data.docs || [];
  } catch (e) {
    list.innerHTML = `<div class="empty">โหลดไม่ได้: ${e.message}</div>`;
    return;
  }

  if (!docs.length) {
    list.innerHTML = '<div class="empty">ไม่พบเอกสาร</div>';
    return;
  }

  const open = async (doc, node) => {
    for (const n of list.querySelectorAll(".kb-doc-item")) n.classList.remove("active");
    if (node) node.classList.add("active");
    contentBox.innerHTML = '<div class="empty">กำลังโหลด...</div>';
    try {
      const d = await api.get("/api/knowledge/doc?path=" + encodeURIComponent(doc.path));
      contentBox.innerHTML = window.marked ? window.marked.parse(d.markdown) : `<pre>${escapeHtml(d.markdown)}</pre>`;
      contentBox.scrollTop = 0;
    } catch (e) {
      contentBox.innerHTML = `<div class="empty">อ่านเอกสารไม่ได้: ${e.message}</div>`;
    }
  };

  // รายชื่อเอกสารปกติ (กรองชื่อได้จากช่องค้นหาด้วย)
  const drawList = (filter = "") => {
    list.innerHTML = "";
    const q = filter.toLowerCase();
    let lastGroup = null;
    let shown = 0;
    for (const doc of docs) {
      if (q && !doc.title.toLowerCase().includes(q)) continue;
      if (doc.group !== lastGroup) {
        list.append(el("div", { class: "sidebar-section", style: "padding-left:12px" }, doc.group));
        lastGroup = doc.group;
      }
      const item = el("div", { class: "kb-doc-item" }, doc.title);
      item.addEventListener("click", () => open(doc, item));
      list.append(item);
      shown++;
    }
    if (!shown) list.append(el("div", { class: "empty" }, "ไม่พบเอกสาร"));
  };

  // ผลค้นหาแบบ full-text (สั่งจากปุ่ม Enter)
  const drawSearch = async (q) => {
    list.innerHTML = '<div class="spinner-inline" style="padding:8px 12px">ค้นหา...</div>';
    try {
      const r = await api.get("/api/knowledge/search?q=" + encodeURIComponent(q));
      list.innerHTML = "";
      list.append(el("div", { class: "sidebar-section", style: "padding-left:12px" }, `ผลค้นหา "${q}" (${r.results.length})`));
      if (!r.results.length) { list.append(el("div", { class: "empty" }, "ไม่พบในเนื้อหา")); return; }
      for (const res of r.results) {
        const item = el("div", { class: "kb-doc-item", style: "white-space:normal" },
          el("div", {}, `${res.title} `, el("span", { class: "field-hint" }, `(${res.count})`)),
          el("div", { class: "field-hint", style: "font-weight:400;margin-top:2px" }, res.snippet.slice(0, 120)));
        item.addEventListener("click", () => open(res, item));
        list.append(item);
      }
    } catch (e) {
      list.innerHTML = `<div class="empty">ค้นหาไม่ได้: ${e.message}</div>`;
    }
  };

  // search box: พิมพ์ = กรองชื่อ, Enter = ค้นในเนื้อหาทุกไฟล์
  const searchIn = el("input", {
    type: "text",
    placeholder: "กรองชื่อ… (Enter = ค้นทั้งเนื้อหา)",
    style: "margin-bottom:8px",
  });
  searchIn.addEventListener("input", () => drawList(searchIn.value.trim()));
  searchIn.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && searchIn.value.trim().length >= 2) drawSearch(searchIn.value.trim());
    if (e.key === "Escape") { searchIn.value = ""; drawList(); }
  });
  list.before(searchIn);
  // ย้าย search เข้าคอลัมน์ list (layout เดิมเป็น flex สองคอลัมน์)
  const kbListWrap = el("div", { style: "display:flex;flex-direction:column;min-width:260px;width:260px" });
  list.parentNode.insertBefore(kbListWrap, searchIn);
  kbListWrap.append(searchIn, list);
  list.style.width = "100%";
  list.style.minWidth = "0";

  drawList();

  // มาจาก palette (#/knowledge?doc=<path>) → เปิดเอกสารนั้นเลย
  const docParam = params && params.get("doc");
  const target = docParam ? docs.find(d => d.path === docParam) : null;
  if (target) {
    // ไฮไลต์ item ในลิสต์ให้ตรงด้วย (เทียบ title)
    const node = [...list.querySelectorAll(".kb-doc-item")].find(n => n.textContent === target.title);
    open(target, node || list.querySelector(".kb-doc-item"));
  } else {
    // auto-open first
    const first = list.querySelector(".kb-doc-item");
    if (first) first.click();
  }
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}
