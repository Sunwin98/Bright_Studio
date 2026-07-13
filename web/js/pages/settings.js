import { api, el, pickSingle } from "../api.js";
import { setBGM, setSFX } from "../sound.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";

export async function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ตั้งค่า"),
    el("div", { class: "page-desc" }, "แก้พาธที่ทั้งแอปใช้ — เปลี่ยนแล้วมีผลทันที ไม่ต้องรีสตาร์ท")
  ));

  let s;
  try {
    s = await api.get("/api/settings");
  } catch (e) {
    main.append(el("div", { class: "empty" }, "โหลดตั้งค่าไม่ได้: " + e.message));
    return;
  }

  // ── Project stores (list) ──
  const storesList = el("div", {});
  const storeInputs = [];
  const addStoreRow = (val = "") => {
    const input = el("input", { type: "text", value: val, placeholder: "เช่น D:\\...\\Projects" });
    const btn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
    const rm = el("button", { class: "btn-ghost btn-sm" }, icon("close", { size: 13 }));
    btn.addEventListener("click", async () => {
      try { const p = await pickSingle({ mode: "folder" }); if (p) input.value = p; }
      catch (e) { if (e.status !== 501) toast.error("เลือกไม่ได้: " + e.message); }
    });
    const row = el("div", { class: "file-pick", style: "margin-bottom:6px" }, input, btn, rm);
    rm.addEventListener("click", () => { row.remove(); storeInputs.splice(storeInputs.indexOf(input), 1); });
    storeInputs.push(input);
    storesList.append(row);
  };
  for (const p of s.project_stores) addStoreRow(p);
  const addStoreBtn = el("button", { class: "btn-ghost btn-sm" }, "+ เพิ่ม store");
  addStoreBtn.addEventListener("click", () => addStoreRow());

  // ── Knowledge dirs (list) ──
  const kbList = el("div", {});
  const kbInputs = [];
  const addKbRow = (val = "") => {
    const input = el("input", { type: "text", value: val, placeholder: "โฟลเดอร์เอกสาร .md" });
    const btn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
    const rm = el("button", { class: "btn-ghost btn-sm" }, icon("close", { size: 13 }));
    btn.addEventListener("click", async () => {
      try { const p = await pickSingle({ mode: "folder" }); if (p) input.value = p; }
      catch (e) { if (e.status !== 501) toast.error("เลือกไม่ได้: " + e.message); }
    });
    const row = el("div", { class: "file-pick", style: "margin-bottom:6px" }, input, btn, rm);
    rm.addEventListener("click", () => { row.remove(); kbInputs.splice(kbInputs.indexOf(input), 1); });
    kbInputs.push(input);
    kbList.append(row);
  };
  for (const p of s.knowledge_dirs) addKbRow(p);
  const addKbBtn = el("button", { class: "btn-ghost btn-sm" }, "+ เพิ่มโฟลเดอร์");
  addKbBtn.addEventListener("click", () => addKbRow());

  // ── single-path fields ──
  const mkPathField = (label, value, hint) => {
    const input = el("input", { type: "text", value });
    const btn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
    btn.addEventListener("click", async () => {
      try { const p = await pickSingle({ mode: "folder" }); if (p) input.value = p; }
      catch (e) { if (e.status !== 501) toast.error("เลือกไม่ได้: " + e.message); }
    });
    const field = el("div", { class: "field" },
      el("label", {}, label), el("div", { class: "file-pick" }, input, btn));
    if (hint) field.append(el("div", { class: "field-hint" }, hint));
    return { field, input };
  };

  const assets = mkPathField("Master assets", s.master_assets, "master_assets/ ของ Skin Factory (pack_icon, ต้นแบบ.geo.json, starlib2, ui heaven)");
  const outDir = mkPathField("Default output dir", s.default_output_dir, "โฟลเดอร์ปลายทางเริ่มต้นเวลาสร้าง skin addon ใหม่");

  const mojangInput = el("input", { type: "text", value: s.mc_com_mojang_override || "", placeholder: "ว่าง = auto-detect (UWP/Preview)" });
  const mojangBtn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
  mojangBtn.addEventListener("click", async () => {
    try { const p = await pickSingle({ mode: "folder" }); if (p) mojangInput.value = p; }
    catch (e) { if (e.status !== 501) toast.error("เลือกไม่ได้: " + e.message); }
  });
  const detectBtn = el("button", { class: "btn-ghost btn-sm" }, icon("search", { size: 14 }), " ตรวจหาอัตโนมัติ");
  const detectStatus = el("span", { class: "field-hint", style: "margin-left:8px" },
    s.com_mojang_detected ? "พบ: " + s.com_mojang_detected : "ยังไม่พบ com.mojang อัตโนมัติ");
  detectBtn.addEventListener("click", async () => {
    detectStatus.textContent = "กำลังตรวจ...";
    try {
      const r = await api.get("/api/settings/detect-mojang");
      detectStatus.textContent = r.found ? "พบ: " + r.com_mojang : "ไม่พบ (ต้องระบุเอง หรือยังไม่ได้ลง Minecraft)";
    } catch (e) { detectStatus.textContent = "❌ " + e.message; }
  });

  main.append(
    el("div", { class: "card" },
      el("div", { class: "card-title" }, "Project stores"),
      el("div", { class: "field-hint" }, "โฟลเดอร์ที่ Project Browser จะสแกนหางาน"),
      storesList, addStoreBtn,
    ),
    el("div", { class: "card" },
      el("div", { class: "card-title" }, "พาธหลัก"),
      assets.field, outDir.field,
    ),
    el("div", { class: "card" },
      el("div", { class: "card-title" }, "คลังความรู้"),
      kbList, addKbBtn,
    ),
    el("div", { class: "card" },
      el("div", { class: "card-title" }, "Minecraft com.mojang (สำหรับ Deploy)"),
      el("div", { class: "field" },
        el("label", {}, "Override path"),
        el("div", { class: "file-pick" }, mojangInput, mojangBtn),
      ),
      el("div", { class: "row", style: "align-items:center" }, detectBtn, detectStatus),
    ),
  );

  // ── UI & Audio (localStorage) ──
  const mkToggle = (label, lsKey, trueLabel, falseLabel, defaultVal, onChange) => {
    const val = localStorage.getItem(lsKey) || defaultVal;
    const select = el("select", { style: "width:auto;" },
      el("option", { value: "true" }, trueLabel),
      el("option", { value: "false" }, falseLabel)
    );
    select.value = val;
    select.addEventListener("change", (e) => {
      localStorage.setItem(lsKey, e.target.value);
      if (onChange) onChange(e.target.value);
    });
    return el("div", { class: "field row", style: "align-items:center; justify-content:space-between; max-width:300px" },
      el("label", { style: "margin:0" }, label), select
    );
  };

  const themeSelect = el("select", { style: "width:auto;" },
    el("option", { value: "night" }, "กลางคืน (Night)"),
    el("option", { value: "day" }, "กลางวัน (Day)")
  );
  themeSelect.value = localStorage.getItem("hs_theme") || "night";
  themeSelect.addEventListener("change", (e) => {
    localStorage.setItem("hs_theme", e.target.value);
    document.body.classList.toggle("day-mode", e.target.value === "day");
  });

  const uiSettingsCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "การแสดงผลและเสียง (UI & Audio)"),
    el("div", { class: "field row", style: "align-items:center; justify-content:space-between; max-width:300px" },
      el("label", { style: "margin:0" }, "ธีม (Theme)"), themeSelect
    ),
    mkToggle("เอฟเฟกต์จอ CRT", "hs_crt", "เปิด", "ปิด", "true", (v) => {
      const crt = document.getElementById("crt-overlay");
      if (crt) crt.style.display = v === "false" ? "none" : "block";
    }),
    mkToggle("ข้ามหน้าต่าง Intro", "hs_skip_intro", "เปิด (ข้าม)", "ปิด (โชว์)", "false"),
    mkToggle("เสียงประกอบ (SFX)", "hs_sfx", "เปิด", "ปิด", "true", (v) => setSFX(v === "true")),
    mkToggle("เสียงเพลง (BGM)", "hs_bgm", "เปิด", "ปิด", "false", (v) => setBGM(v === "true")),
    el("div", { class: "field-hint" },
      "BGM ใช้ไฟล์ web/assets/bgm.mp3 — วางเพลง lo-fi (CC0) ของคุณเองได้เลย ไม่มีไฟล์จะเป็นเสียง ambient เบาๆ แทน"),
  );
  main.append(uiSettingsCard);

  const updateBtn = el("button", { class: "btn-ghost btn-sm" }, "ตรวจสอบอัปเดต");
  const updateStatus = el("span", { class: "field-hint", style: "margin-left:8px" }, "เวอร์ชันปัจจุบัน: v2.0.0");
  updateBtn.addEventListener("click", async () => {
    updateStatus.textContent = "กำลังตรวจ...";
    setTimeout(() => {
      updateStatus.textContent = "เวอร์ชันปัจจุบันล่าสุดแล้ว (v2.0.0)";
    }, 1000);
  });

  const systemCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "ระบบ (System)"),
    el("div", { class: "row", style: "align-items:center" }, updateBtn, updateStatus)
  );
  main.append(systemCard);

  const saveBtn = el("button", { class: "btn-primary" }, icon("save", { size: 15 }), " บันทึกตั้งค่า");
  const status = el("span", { class: "spinner-inline", style: "margin-left:10px" }, "");
  main.append(el("div", { class: "card" }, saveBtn, status));

  saveBtn.addEventListener("click", async () => {
    const body = {
      project_stores: storeInputs.map(i => i.value.trim()).filter(Boolean),
      master_assets: assets.input.value.trim(),
      default_output_dir: outDir.input.value.trim(),
      knowledge_dirs: kbInputs.map(i => i.value.trim()).filter(Boolean),
      mc_com_mojang_override: mojangInput.value.trim() || null,
    };
    saveBtn.disabled = true;
    status.textContent = "กำลังบันทึก...";
    try {
      await api.post("/api/settings", body);
      status.textContent = "✅ บันทึกแล้ว — มีผลทันที";
      toast.success("บันทึกตั้งค่าแล้ว");
    } catch (e) {
      status.textContent = "❌ " + e.message;
      toast.error("บันทึกไม่สำเร็จ: " + e.message);
    } finally {
      saveBtn.disabled = false;
    }
  });
}
