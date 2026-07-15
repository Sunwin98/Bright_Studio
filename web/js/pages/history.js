import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { confirmDialog } from "../ui/window.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

const dateText = value => {
  if (!value) return "ไม่ทราบเวลา";
  try { return new Date(value).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" }); }
  catch { return value; }
};

const shortPath = value => {
  const text = String(value || "");
  return text.length > 72 ? "…" + text.slice(-69) : text;
};

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ประวัติไฟล์"),
    el("div", { class: "page-desc" }, "ดูสถานะเดิมก่อนแก้ไข และกู้คืนโปรเจกต์ได้อย่างปลอดภัย")
  ));

  const sourceInput = el("input", { type: "text", placeholder: "โฟลเดอร์หรือไฟล์ที่ต้องการบันทึกสถานะ" });
  const pickFileBtn = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("document", { size: 15 }), " เลือกไฟล์");
  const pickDirBtn = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const labelInput = el("input", { type: "text", placeholder: "ชื่อจุดบันทึก เช่น ก่อนปรับสกิล" });
  const saveBtn = el("button", { class: "btn-primary btn-sm", type: "button" }, icon("save", { size: 15 }), " บันทึกสถานะตอนนี้");
  const saveStatus = el("div", { class: "field-hint", style: "min-height:18px;" }, "");

  const openParam = params && params.get("open");
  sourceInput.value = openParam || activeProjectOpenPath() || "";
  pickFileBtn.addEventListener("click", async () => {
    const path = await pickSingle({ mode: "open_file", filters: [".mcaddon", ".mcpack", ".zip", ".json", ".js"] });
    if (path) sourceInput.value = path;
  });
  pickDirBtn.addEventListener("click", async () => {
    const path = await pickSingle({ mode: "folder" });
    if (path) sourceInput.value = path;
  });

  main.append(el("div", { class: "card history-capture-card" },
    el("div", { class: "card-title" }, "สร้างจุดกู้คืน"),
    el("div", { class: "field-hint history-lead" }, "ระบบจะเก็บสำเนาสถานะปัจจุบันไว้ก่อนที่คุณจะเริ่มแก้ไข"),
    el("div", { class: "field" },
      el("label", {}, "ไฟล์หรือโฟลเดอร์"),
      el("div", { class: "file-pick" }, sourceInput, pickFileBtn, pickDirBtn)),
    el("div", { class: "field" },
      el("label", {}, "ชื่อจุดกู้คืน (ไม่จำเป็น)"), labelInput),
    el("div", { class: "row history-capture-actions" }, saveBtn, saveStatus),
  ));

  const list = el("div", { class: "history-list" });
  const detail = el("div", { class: "history-detail" }, el("div", { class: "empty" }, "เลือกประวัติด้านซ้ายเพื่อดูรายละเอียด"));
  main.append(el("div", { class: "history-layout" },
    el("section", { class: "card history-list-card" },
      el("div", { class: "card-title" }, "รายการล่าสุด"), list),
    el("section", { class: "card history-detail-card" }, detail),
  ));

  let snapshots = [];

  const loadDetail = async id => {
    detail.innerHTML = '<div class="loading">กำลังโหลดรายละเอียด...</div>';
    try {
      const snapshot = await api.get(`/api/history/${encodeURIComponent(id)}`);
      const files = snapshot.files || [];
      const restoreBtn = el("button", { class: "btn-primary btn-sm", type: "button" }, icon("refresh", { size: 14 }), " กู้คืนสถานะนี้");
      const deleteBtn = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("trash", { size: 14 }), " ลบประวัติ");
      restoreBtn.addEventListener("click", async () => {
        const ok = await confirmDialog({
          title: "กู้คืนประวัติไฟล์", jp: "復元確認", danger: true, confirmLabel: "กู้คืนและสำรองปัจจุบัน",
          message: `กู้คืน “${snapshot.label}” ใช่ไหม?\nระบบจะสำรองสถานะปัจจุบันให้อัตโนมัติก่อนกู้คืน\n\n${files.length} รายการจะถูกกู้คืน`,
        });
        if (!ok) return;
        restoreBtn.disabled = true;
        try {
          const result = await api.post(`/api/history/${encodeURIComponent(id)}/restore`, {});
          toast.success(`กู้คืนแล้ว ${result.restored.length} รายการ และสำรองสถานะเดิมไว้แล้ว`);
          await loadSnapshots();
          await loadDetail(id);
        } catch (error) {
          restoreBtn.disabled = false;
          toast.error("กู้คืนไม่ได้: " + error.message);
        }
      });
      deleteBtn.addEventListener("click", async () => {
        const ok = await confirmDialog({ title: "ลบประวัติไฟล์", jp: "履歴削除", danger: true, confirmLabel: "ลบประวัตินี้", message: `ลบ “${snapshot.label}” ใช่ไหม?\nการลบประวัติไม่กระทบไฟล์โปรเจกต์` });
        if (!ok) return;
        try {
          await api.delete(`/api/history/${encodeURIComponent(id)}`);
          toast.success("ลบประวัติแล้ว");
          detail.innerHTML = '<div class="empty">เลือกประวัติด้านซ้ายเพื่อดูรายละเอียด</div>';
          await loadSnapshots();
        } catch (error) { toast.error("ลบประวัติไม่ได้: " + error.message); }
      });

      detail.innerHTML = "";
      detail.append(
        el("div", { class: "history-detail-head" },
          el("div", {}, el("div", { class: "history-detail-title" }, snapshot.label), el("div", { class: "field-hint" }, dateText(snapshot.created_at))),
          el("span", { class: "history-status" + (snapshot.status === "completed" ? " ok" : " warn") }, snapshot.status === "completed" ? "พร้อมกู้คืน" : snapshot.status),
        ),
        el("div", { class: "field-hint history-source" }, snapshot.source ? "ต้นทาง: " + shortPath(snapshot.source) : "สร้างจากการบันทึกสถานะด้วยตนเอง"),
        el("div", { class: "history-file-heading" }, `ไฟล์และโฟลเดอร์ในจุดนี้ (${files.length})`),
        el("div", { class: "history-file-list" }, ...files.map(file => el("div", { class: "history-file-row" }, icon(file.kind === "directory" ? "folder" : "document", { size: 15 }), el("span", { title: file.path }, shortPath(file.path))))),
        el("div", { class: "history-actions" }, restoreBtn, deleteBtn),
      );
    } catch (error) { detail.innerHTML = `<div class="empty">โหลดประวัติไม่ได้: ${error.message}</div>`; }
  };

  const loadSnapshots = async () => {
    list.innerHTML = '<div class="loading">กำลังโหลดประวัติ...</div>';
    try {
      const data = await api.get("/api/history?limit=100");
      snapshots = data.snapshots || [];
      list.innerHTML = "";
      if (!snapshots.length) {
        list.append(el("div", { class: "empty history-empty" }, icon("archive", { size: 24 }), el("div", {}, "ยังไม่มีประวัติไฟล์"), el("div", { class: "field-hint" }, "บันทึกจุดกู้คืนก่อนเริ่มแก้ไขโปรเจกต์")));
        return;
      }
      for (const snapshot of snapshots) {
        const row = el("button", { class: "history-row", type: "button" },
          el("span", { class: "history-row-icon" }, icon("archive", { size: 16 })),
          el("span", { class: "history-row-copy" }, el("span", { class: "history-row-label" }, snapshot.label), el("span", { class: "history-row-meta" }, `${dateText(snapshot.created_at)} · ${snapshot.item_count} รายการ`)),
          icon("chevron-right", { size: 15 }),
        );
        row.addEventListener("click", () => { list.querySelectorAll(".history-row").forEach(item => item.classList.remove("active")); row.classList.add("active"); loadDetail(snapshot.id); });
        list.append(row);
      }
      if (!detail.querySelector(".history-detail-title") && snapshots[0]) {
        list.querySelector(".history-row")?.classList.add("active");
        loadDetail(snapshots[0].id);
      }
    } catch (error) { list.innerHTML = `<div class="empty">โหลดประวัติไม่ได้: ${error.message}</div>`; }
  };

  saveBtn.addEventListener("click", async () => {
    const path = sourceInput.value.trim();
    if (!path) { toast.error("เลือกไฟล์หรือโฟลเดอร์ก่อน"); return; }
    saveBtn.disabled = true;
    saveStatus.textContent = "กำลังสร้างจุดกู้คืน...";
    try {
      const snapshot = await api.post("/api/history/snapshot", { paths: [path], label: labelInput.value.trim() || "บันทึกสถานะไฟล์", source: path });
      saveStatus.textContent = `บันทึกแล้ว · ${snapshot.item_count || snapshot.items?.length || 1} รายการ`;
      labelInput.value = "";
      await loadSnapshots();
      await loadDetail(snapshot.id);
    } catch (error) { saveStatus.textContent = "บันทึกไม่ได้: " + error.message; }
    finally { saveBtn.disabled = false; }
  });

  await loadSnapshots();
}
