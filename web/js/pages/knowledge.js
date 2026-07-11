import { api, el } from "../api.js";

export async function render(main) {
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

  list.innerHTML = "";
  const open = async (doc, node) => {
    for (const n of list.querySelectorAll(".kb-doc-item")) n.classList.remove("active");
    node.classList.add("active");
    contentBox.innerHTML = '<div class="empty">กำลังโหลด...</div>';
    try {
      const d = await api.get("/api/knowledge/doc?path=" + encodeURIComponent(doc.path));
      contentBox.innerHTML = window.marked ? window.marked.parse(d.markdown) : `<pre>${escapeHtml(d.markdown)}</pre>`;
      contentBox.scrollTop = 0;
    } catch (e) {
      contentBox.innerHTML = `<div class="empty">อ่านเอกสารไม่ได้: ${e.message}</div>`;
    }
  };

  let lastGroup = null;
  for (const doc of docs) {
    if (doc.group !== lastGroup) {
      list.append(el("div", { class: "sidebar-section", style: "padding-left:12px" }, doc.group));
      lastGroup = doc.group;
    }
    const item = el("div", { class: "kb-doc-item" }, doc.title);
    item.addEventListener("click", () => open(doc, item));
    list.append(item);
  }

  // auto-open first
  const first = list.querySelector(".kb-doc-item");
  if (first) first.click();
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}
