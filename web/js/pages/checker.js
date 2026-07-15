import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { confirmDialog } from "../ui/window.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

export function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ตรวจสอบ Addon"),
    el("div", { class: "page-desc" }, "หา error ก่อนเข้าเกม, เลือกไฟล์ .mcaddon/.zip หรือโฟลเดอร์ addon ระบบจะแยก BP/RP ให้เอง")
  ));

  const srcInput = el("input", { type: "text", placeholder: "ไฟล์ .mcaddon/.zip หรือโฟลเดอร์ addon" });
  const pickFileBtn = el("button", { class: "btn-ghost btn-sm" }, icon("document", { size: 15 }), " เลือกไฟล์");
  const pickDirBtn = el("button", { class: "btn-ghost btn-sm" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const detected = el("div", { class: "field-hint", style: "min-height:18px;" }, "");
  const checkBtn = el("button", { class: "btn-primary" }, icon("check-circle", { size: 15 }), " ตรวจสอบ");
  const result = el("div", {});
  let resolved = { bp_path: null, rp_path: null };

  const inspect = async () => {
    const path = srcInput.value.trim();
    resolved = { bp_path: null, rp_path: null };
    if (!path) { detected.textContent = ""; return; }
    detected.textContent = "กำลังแยก BP/RP...";
    try {
      const report = await api.post("/api/packio/inspect", { path });
      resolved = report;
      const parts = (report.packs || []).map(pack => `${pack.type === "behavior" ? "BP" : "RP"}: ${pack.name}`);
      detected.textContent = parts.length
        ? "พบ → " + parts.slice(0, 4).join(" · ") + (parts.length > 4 ? ` · …อีก ${parts.length - 4} แพ็ก` : "")
        : "ไม่พบแพ็กข้างใน (ไม่มี manifest.json)";
      detected.className = parts.length ? "field-hint log-ok" : "field-hint log-warn";
    } catch (error) {
      detected.textContent = "แยกไม่ได้: " + error.message;
      detected.className = "field-hint log-err";
    }
  };

  pickFileBtn.addEventListener("click", async () => {
    const path = await pickSingle({ mode: "open_file", filters: [".mcaddon", ".mcpack", ".zip"] });
    if (path) { srcInput.value = path; inspect(); }
  });
  pickDirBtn.addEventListener("click", async () => {
    const path = await pickSingle({ mode: "folder" });
    if (path) { srcInput.value = path; inspect(); }
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
  main.append(result);

  const hasSource = () => Boolean(srcInput.value.trim());
  const isArchiveSource = () => [".mcaddon", ".mcpack", ".zip"].some(ext => srcInput.value.trim().toLowerCase().endsWith(ext));

  const applyAutoFix = async (fixable, selectedRepairs, button) => {
    const labels = [...new Set(fixable.map(issue => issue.fix_label).filter(Boolean))];
    const repairLines = selectedRepairs.map(repair => `• ${repair.from} → ${repair.to}`);
    const lines = [...labels.map(label => "• " + label), ...repairLines];
    const ok = await confirmDialog({
      title: "ตรวจรายการก่อนแก้ไข", jp: "修復確認", danger: true,
      confirmLabel: "แก้ไขและตรวจซ้ำ",
      message: `ระบบจะเปลี่ยน ${lines.length} รายการที่เลือก\n${lines.join("\n")}\n\n${isArchiveSource()
        ? "ระบบจะสร้าง archive ใหม่ทับไฟล์เดิม และเก็บต้นฉบับเป็น .autofix.bak"
        : "ระบบจะสำรองไฟล์ที่แก้เป็น .autofix.bak ก่อนบันทึก"}`,
    });
    if (!ok) return;
    button.disabled = true;
    try {
      const fixed = await api.post("/api/checker/fix", {
        source: srcInput.value.trim(),
        bp_path: resolved.bp_path,
        rp_path: resolved.rp_path,
        repairs: selectedRepairs.map(repair => ({ repair_id: repair.id, to: repair.to })),
      });
      if (fixed.source_replaced) await inspect();
      renderReport(fixed.check);
      if (fixed.changed) {
        const destination = fixed.source_replaced
          ? "สร้างไฟล์ใหม่แทนต้นฉบับแล้ว พร้อม backup"
          : "สำรองไฟล์เดิมไว้แล้ว";
        toast.success(`แก้แล้ว ${fixed.changes.length} รายการ · ${destination}`);
      } else {
        toast.info("ยังไม่มีการเปลี่ยนแปลงที่ปลอดภัยให้ทำอัตโนมัติ");
      }
    } catch (error) {
      button.disabled = false;
      toast.error("แก้อัตโนมัติไม่ได้: " + error.message);
    }
  };

  const renderReport = report => {
    const fixable = (report.issues || []).filter(issue => issue.fixable);
    const repairIssues = (report.issues || []).filter(issue => issue.repair && issue.repair.candidates?.length);
    const repairControls = [];
    const head = report.ok
      ? el("div", { class: "checker-result-status ok" }, icon("check-circle", { size: 18 }), `ผ่าน · 0 error, ${report.warnings} warning`)
      : el("div", { class: "checker-result-status error" }, icon("x-circle", { size: 18 }), `พบ ${report.errors} error, ${report.warnings} warning`);
    const card = el("div", { class: "card checker-result" }, head);

    if (repairIssues.length) {
      const repairList = el("div", { class: "checker-repair-list" });
      for (const issue of repairIssues) {
        const repair = issue.repair;
        const auto = issue.fixable && repair.to;
        const select = auto ? null : el("select", { class: "checker-repair-select", "aria-label": "เลือกไฟล์ที่ต้องการใช้แทน" },
          el("option", { value: "" }, "เลือกไฟล์ที่ต้องการใช้แทน"),
          ...repair.candidates.map(candidate => el("option", { value: candidate }, candidate)),
        );
        if (select) repairControls.push({ issue, select });
        repairList.append(el("div", { class: "checker-repair-row" },
          el("div", { class: "checker-repair-copy" },
            el("div", { class: "checker-repair-title" }, "พาธที่พบปัญหา"),
            el("div", { class: "checker-repair-path" },
              el("code", {}, repair.from),
              el("span", { class: "checker-repair-arrow" }, "→"),
              auto ? el("code", { class: "checker-repair-target" }, repair.to) : select,
            ),
          ),
          el("span", { class: "checker-fix-chip" }, auto ? "มั่นใจสูง" : "ต้องเลือก"),
        ));
      }
      card.append(el("div", { class: "checker-repair-panel" },
        el("div", { class: "checker-repair-heading" }, icon("search", { size: 15 }), "ระบบพบไฟล์ที่อาจเป็นไฟล์ที่ถูกต้อง"),
        el("div", { class: "field-hint" }, "รายการที่มั่นใจสูงจะแก้ได้ทันที ส่วนรายการที่มีหลายตัวเลือกให้เลือกก่อน"),
        repairList,
      ));
    }

    const selectedRepairs = () => repairControls
      .filter(control => control.select.value)
      .map(control => ({ ...control.issue.repair, to: control.select.value }));
    const actionCount = () => fixable.length + selectedRepairs().length;
    const canFix = fixable.length > 0 || repairIssues.length > 0;
    if (canFix) {
      const fixBtn = el("button", { class: "btn-primary btn-sm", type: "button" }, icon("wrench", { size: 14 }), ` แก้ไขที่เลือก (${actionCount()})`);
      const updateCount = () => { fixBtn.lastChild.textContent = ` แก้ไขที่เลือก (${actionCount()})`; };
      for (const control of repairControls) control.select.addEventListener("change", updateCount);
      fixBtn.addEventListener("click", () => {
        const selected = selectedRepairs();
        if (!fixable.length && !selected.length) {
          toast.info("เลือกไฟล์ที่ต้องการใช้แทนก่อน");
          return;
        }
        applyAutoFix(fixable, selected, fixBtn);
      });
      card.append(el("div", { class: "checker-fix-panel" },
        el("div", { class: "checker-fix-copy" },
          el("div", { class: "checker-fix-title" }, icon("wrench", { size: 15 }), "มีรายการที่ช่วยแก้ได้"),
          el("div", { class: "field-hint" }, isArchiveSource()
            ? "เมื่อยืนยัน ระบบจะสร้าง archive ใหม่ทับไฟล์เดิมและเก็บ backup"
            : "ระบบจะแก้เฉพาะรายการที่ยืนยัน และเก็บ backup ของไฟล์เดิม"),
        ),
        fixBtn,
      ));
    } else if (fixable.length > 0) {
      card.append(el("div", { class: "checker-fix-note" }, icon("folder", { size: 15 }), "เลือกไฟล์หรือโฟลเดอร์ addon ก่อน จึงจะใช้การแก้ไขอัตโนมัติได้"));
    }

    if (!report.issues?.length) card.append(el("div", { class: "empty" }, "ไม่พบปัญหา 🎉"));
    for (const issue of report.issues || []) {
      const color = issue.level === "error" ? "var(--red)" : "var(--yellow)";
      card.append(el("div", { class: "checker-issue-row" },
        el("div", { class: "checker-issue-main" },
          el("span", { style: `color:${color};font-weight:700` }, issue.level === "error" ? "ERROR" : "WARN"),
          el("span", {}, issue.message),
        ),
        el("div", { class: "checker-issue-meta" },
          issue.file ? el("span", { class: "checker-issue-file" }, "· " + issue.file) : null,
          issue.fixable ? el("span", { class: "checker-fix-chip" }, hasSource() ? "แก้ได้อัตโนมัติ" : "เลือก source ก่อน") : null,
        ),
      ));
    }
    result.innerHTML = "";
    result.append(card);
  };

  const openParam = params && params.get("open");
  const autoPath = openParam || activeProjectOpenPath();
  if (autoPath) { srcInput.value = autoPath; inspect(); }

  checkBtn.addEventListener("click", async () => {
    if (!resolved.bp_path && !resolved.rp_path) {
      if (srcInput.value.trim()) await inspect();
      if (!resolved.bp_path && !resolved.rp_path) { toast.error("ยังไม่พบ BP/RP, เลือกไฟล์หรือโฟลเดอร์ addon ก่อน"); return; }
    }
    checkBtn.disabled = true;
    result.innerHTML = '<div class="empty">กำลังตรวจ...</div>';
    try {
      const report = await api.post("/api/checker/check", { bp_path: resolved.bp_path, rp_path: resolved.rp_path });
      renderReport(report);
    } catch (error) {
      result.innerHTML = `<div class="empty">ตรวจไม่ได้: ${error.message}</div>`;
    } finally {
      checkBtn.disabled = false;
    }
  });
}
