import { api, el, pickSingle, renderValidation, resolveDroppedFile } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";

const SLOTS = [
  ["1", "หมวก (Head)"], ["2", "เสื้อเกราะ (Chest)"], ["3", "กางเกง (Legs)"],
  ["4", "รองเท้า (Feet)"], ["5", "มือขวา (Mainhand)"],
];

let skinRows = [];

export function render(main) {
  skinRows = [];
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "สร้างสกิน"),
    el("div", { class: "page-desc" }, "Skin Factory — สร้าง skin addon ครบชุด (BP+RP, icon, selector UI, Xbox lock)")
  ));

  // ── Addon settings ──
  const nameInput = el("input", { type: "text", placeholder: "เช่น My Cool Skins" });
  const uiSelect = el("select", {},
    el("option", { value: "normal" }, "Normal UI (ActionFormData)"),
    el("option", { value: "special" }, "Special UI (Custom สีชมพู)"),
    el("option", { value: "none" }, "No UI (สกินธรรมดา ไม่มี Selector)"),
  );
  const outInput = compactDropzone("ว่าง = Projects/ (ค่าเริ่มต้น)", [], "", "folder");

  const xboxToggle = el("input", { type: "checkbox" });
  const xboxPlayers = el("input", { type: "text", placeholder: "ชื่อ Xbox คั่นด้วย , (Iamsayhi1 ถูกเพิ่มอัตโนมัติ)" });
  const xboxWrap = el("div", { class: "field", style: "display:none" },
    el("label", {}, "รายชื่อผู้เล่นที่อนุญาต"), xboxPlayers);
  xboxToggle.addEventListener("change", () => {
    xboxWrap.style.display = xboxToggle.checked ? "block" : "none";
  });

  const settingsCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "ตั้งค่า Add-on"),
    el("div", { class: "field" }, el("label", {}, "ชื่อ Add-on"), nameInput),
    el("div", { class: "row" },
      el("div", { class: "field" }, el("label", {}, "ประเภท UI"), uiSelect),
      el("div", { class: "field" }, el("label", {}, "โฟลเดอร์ปลายทาง (output)"), outInput.node),
    ),
    el("div", { class: "field" }, el("label", { class: "toggle" }, xboxToggle, "ล็อก Xbox username")),
    xboxWrap,
  );
  main.append(settingsCard);

  // ── Skins ──
  const skinsCard = el("div", { class: "card" });
  const skinsList = el("div", {});
  const addBtn = el("button", { class: "btn-ghost btn-sm" }, "+ เพิ่มสกินเปล่า");

  skinsCard.append(
    el("div", { class: "card-title" }, "สกิน"),
    skinsList,
    addBtn,
  );
  main.append(skinsCard);

  addBtn.addEventListener("click", () => skinsList.append(makeSkinRow()));
  skinsList.append(makeSkinRow());

  const setupDragDrop = (element) => {
    element.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      skinsCard.classList.add("dragover");
    });
    element.addEventListener("dragleave", (e) => {
      e.stopPropagation();
      skinsCard.classList.remove("dragover");
    });
    element.addEventListener("drop", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      skinsCard.classList.remove("dragover");
      const files = Array.from(e.dataTransfer.files).filter(f => {
        const name = f.path || f.name || "";
        return name.toLowerCase().endsWith(".png");
      });
      if (files.length > 0) {
        const existingRows = Array.from(skinsList.children);
        if (existingRows.length === 1) {
          const firstRow = existingRows[0];
          if (firstRow._collect && !firstRow._collect()) {
            firstRow.remove();
          }
        }
        for (const file of files) {
          try {
            const localPath = await resolveDroppedFile(file);
            skinsList.append(makeSkinRow(localPath));
          } catch (err) {
            toast.error(`เพิ่มสกินล้มเหลว: ${err.message}`);
          }
        }
        toast.success(`เพิ่มสกินสำเร็จ ${files.length} รายการ`);
      }
    });
  };

  setupDragDrop(skinsCard);

  // ── Build ──
  const buildBtn = el("button", { class: "btn-primary" }, icon("wrench", { size: 15 }), " สร้าง Add-on");
  const logBox = el("div", { class: "log-box", style: "display:none;margin-top:14px" });
  const buildCard = el("div", { class: "card" },
    el("div", { class: "card-title" }, "สร้าง"),
    buildBtn, logBox,
  );
  main.append(buildCard);

  buildBtn.addEventListener("click", async () => {
    const skins = collectSkins();
    if (!skins.length) { toast.error("ต้องมีอย่างน้อย 1 สกิน (เลือกไฟล์ PNG)"); return; }
    const body = {
      addon_name: nameInput.value.trim() || "MultiSkin",
      ui_mode: uiSelect.value,
      xbox_lock: xboxToggle.checked,
      xbox_players: xboxPlayers.value.split(",").map(s => s.trim()).filter(Boolean),
      output_dir: outInput.value().trim() || null,
      skins,
    };
    buildBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังสร้าง...";
    const t = toast.progress("กำลังสร้างสกิน...");
    try {
      const res = await api.post("/api/skin/build", body);
      const lines = (res.log || []).join("\n");
      const gives = (res.give_commands || []).join("\n");
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, lines + "\n\n"));
      logBox.append(el("span", {}, "📁 " + res.project_path + "\n\n🎮 Give:\n" + gives));
      const v = renderValidation(res.validation);
      if (v) logBox.append(v);
      t.success("สร้างสกินสำเร็จ");
    } catch (e) {
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
      t.error("สร้างสกินไม่สำเร็จ: " + e.message);
    } finally {
      buildBtn.disabled = false;
    }
  });
}

function makeSkinRow(initialSkinPath = "") {
  const skinPath = compactDropzone("ลากไฟล์ Skin (.png) มาวาง หรือคลิกเพื่อเลือก *", ["Images (*.png)"], initialSkinPath);
  const modelPath = compactDropzone("ลากไฟล์ Model (.geo.json) มาวาง หรือคลิกเพื่อเลือก (optional)", ["JSON (*.json)"]);
  const animPath = compactDropzone("ลากไฟล์ Animation (.json) มาวาง หรือคลิกเพื่อเลือก (optional)", ["JSON (*.json)"]);
  const nameInput = el("input", { type: "text", placeholder: "ว่าง = ชื่อไฟล์" });
  const slotSel = el("select", {}, ...SLOTS.map(([v, t]) => el("option", { value: v }, t)));
  const preview = el("img", { width: "48", height: "48", style: "image-rendering:pixelated;border-radius:6px;background:#1e1f22;display:none" });
  const previewBtn = el("button", { class: "btn-ghost btn-sm" }, "ดู icon");
  const removeBtn = el("button", { class: "btn-ghost btn-sm" }, "ลบ");
 
  if (initialSkinPath) {
    const filename = initialSkinPath.split(/[\\/]/).pop().replace(/\.png$/i, "");
    nameInput.value = filename;
  }

  // Preview listener should watch for changes
  skinPath.node.addEventListener("change", () => {
    preview.style.display = "none";
  });

  previewBtn.addEventListener("click", async () => {
    const p = skinPath.value();
    if (!p) { toast.error("เลือกไฟล์สกินก่อน"); return; }
    try {
      const r = await api.post("/api/skin/preview-icon", { skin_path: p });
      preview.src = "data:image/png;base64," + r.icon_base64;
      preview.style.display = "inline-block";
    } catch (e) { toast.error("preview ไม่ได้: " + e.message); }
  });
 
  const row = el("div", { class: "card", style: "background:#2b2d31" },
    el("div", { class: "field" }, el("label", {}, "ไฟล์ Skin (.png) *"), skinPath.node),
    el("div", { class: "row" },
      el("div", { class: "field" }, el("label", {}, "ชื่อสกิน"), nameInput),
      el("div", { class: "field" }, el("label", {}, "Slot"), slotSel),
    ),
    el("div", { class: "field" }, el("label", {}, "Model (optional)"), modelPath.node),
    el("div", { class: "field" }, el("label", {}, "Animation (optional)"), animPath.node),
    el("div", { class: "row", style: "align-items:center;gap:12px" }, previewBtn, preview, removeBtn),
  );
  removeBtn.addEventListener("click", () => row.remove());
 
  row._collect = () => {
    const sp = skinPath.value();
    if (!sp) return null;
    return {
      skin_path: sp,
      model_path: modelPath.value() || null,
      animation_path: animPath.value() || null,
      display_name: nameInput.value.trim() || null,
      slot: slotSel.value,
    };
  };
  return row;
}
 
function collectSkins() {
  const out = [];
  for (const node of document.querySelectorAll("#main .card")) {
    if (node._collect) {
      const s = node._collect();
      if (s) out.push(s);
    }
  }
  return out;
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
          toast.error(`นำเข้าไฟล์ล้มเหลว: ${err.message}`);
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
