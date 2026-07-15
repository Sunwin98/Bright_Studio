import { api, el, pickSingle, resolveDroppedFile, getApiBase } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

let tools = [];
let lastFocusedTextarea = null;
let currentAttachables = []; // Discovered attachables
let selectedAttachable = null;
let selectedSourcePath = "";

export async function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "ฟิสิกส์อัจฉริยะ (Smart Physics)"),
    el("div", { class: "page-desc" }, "สร้างฟิสิกส์สำหรับเสื้อผ้า ผ้าคลุม และเส้นผมโดยอัตโนมัติจากแอดออนหรือไฟล์ .mcaddon")
  ));

  // Load tools list
  try {
    const data = await api.get("/api/physics/tools");
    tools = data.tools || [];
  } catch (e) {
    main.append(el("div", { class: "empty" }, "โหลดรายการเครื่องมือไม่ได้: " + e.message));
    return;
  }

  // A. Intake Card
  const intakeCard = el("div", { class: "card", style: "margin-bottom:14px" });
  main.append(intakeCard);
  renderIntake(intakeCard, main);
}

function renderIntake(card, main) {
  card.innerHTML = "";
  card.append(el("div", { class: "card-title" }, "นำเข้าไฟล์แอดออน / แหล่งข้อมูล"));

  const loadingText = el("div", { style: "display:none;margin-top:10px;color:var(--neon-cyan);" }, 
    el("span", { class: "spinner-inline" }, "กำลังแกะกล่องและตรวจสอบโครงสร้างแอดออน...")
  );

  const dropzone = el("div", { class: "mg-dropzone", style: "margin-bottom: 0px;" },
    el("div", { class: "mg-dropzone-inner" },
      icon("archive", { size: 26 }),
      el("span", {}, selectedSourcePath ? "แอดออนที่เลือก: " + selectedSourcePath.split(/[\\/]/).pop() : "ลากไฟล์ .mcaddon / .zip หรือโฟลเดอร์มาวางที่นี่"),
      el("small", {}, "หรือคลิกที่นี่เพื่อเลือกไฟล์แอดออน")
    )
  );

  card.append(
    el("div", { class: "field" },
      dropzone,
      loadingText
    )
  );

  const mainContainer = el("div", { style: "display:none;" });
  main.append(mainContainer);

  const handleInspect = async (path) => {
    if (!path) return;
    selectedSourcePath = path;
    const nameSpan = dropzone.querySelector("span");
    if (nameSpan) {
      nameSpan.textContent = "แอดออนที่เลือก: " + path.split(/[\\/]/).pop();
    }
    loadingText.style.display = "block";
    mainContainer.style.display = "none";
    mainContainer.innerHTML = "";

    try {
      const data = await api.post("/api/physics/inspect", { path });
      currentAttachables = data.attachables || [];
      loadingText.style.display = "none";
      
      if (!currentAttachables.length) {
        mainContainer.innerHTML = "";
        mainContainer.append(el("div", { class: "empty" }, "❌ ไม่พบไฟล์ Attachable ในโฟลเดอร์แอดออนนี้"));
        mainContainer.style.display = "block";
        return;
      }
      
      mainContainer.style.display = "block";
      renderPhysicsWorkspace(mainContainer, currentAttachables);
    } catch (e) {
      loadingText.style.display = "none";
      mainContainer.innerHTML = "";
      mainContainer.append(el("div", { class: "empty" }, `❌ ตรวจสอบล้มเหลว: ${e.message}`));
      mainContainer.style.display = "block";
    }
  };

  dropzone.addEventListener("click", async () => {
    try {
      const p = await pickSingle({ mode: "open_file", filters: ["Addon (*.mcaddon)", "Pack (*.mcpack)", "Archive (*.zip)"] });
      if (p) handleInspect(p);
    } catch (e) {
      toast.error("เลือกไฟล์ไม่ได้: " + e.message);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", (e) => {
    e.stopPropagation();
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      try {
        const localPath = await resolveDroppedFile(file);
        handleInspect(localPath);
      } catch (err) {
        toast.error(`ตรวจพบข้อผิดพลาด: ${err.message}`);
      }
    }
  });

  // Restore state if source already selected — ไม่งั้นใช้โปรเจกต์ที่ปักหมุดไว้
  if (selectedSourcePath) {
    handleInspect(selectedSourcePath);
  } else {
    const ap = activeProjectOpenPath();
    if (ap) handleInspect(ap);
  }
}

function renderPhysicsWorkspace(container, attachables) {
  container.innerHTML = "";

  // Dropdown for Attachable Selector
  const attachableSel = el("select", {});
  attachables.forEach(att => {
    attachableSel.append(el("option", { value: att.identifier }, att.identifier));
  });

  const selectCard = el("div", { class: "card", style: "margin-bottom:14px" },
    el("div", { class: "field" }, 
      el("label", {}, "เลือกวัตถุ/ชุดเกราะที่ต้องการใส่ฟิสิกส์ (Attachable)"), 
      attachableSel
    )
  );
  container.append(selectCard);

  // Dynamic Workspace Container
  const workspace = el("div");
  container.append(workspace);

  const rebuildWorkspace = () => {
    const att = attachables.find(a => a.identifier === attachableSel.value);
    selectedAttachable = att;
    renderAttachableWorkspace(workspace, att);
  };

  attachableSel.addEventListener("change", rebuildWorkspace);
  rebuildWorkspace();
}

function renderAttachableWorkspace(workspace, att) {
  workspace.innerHTML = "";

  // 1. Files & Tool Selector Card
  const configCard = el("div", { class: "card", style: "margin-bottom:14px" });
  workspace.append(configCard);

  const toolSel = el("select", {}, ...tools.map(t => el("option", { value: t.id }, t.label)));

  // Pre-filled Paths compact dropzones
  const animInput = compactDropzone("ลากไฟล์แอนิเมชัน (.json) มาวาง หรือคลิกเพื่อเลือก *", ["JSON (*.json)"], att.animations[0]?.file_path || att.all_animation_files[0] || "");
  const modelInput = compactDropzone("ลากไฟล์โมเดลสามมิติ (.geo.json) มาวาง หรือคลิกเพื่อเลือก *", ["JSON (*.json)"], att.model_path || "");
  const attachInput = compactDropzone("ลากไฟล์ประกอบชิ้นส่วน Attachable (.json) มาวาง หรือคลิกเพื่อเลือก (optional)", ["JSON (*.json)"], att.attachable_path || "");

  configCard.append(
    el("div", { class: "card-title" }, "การตั้งค่าโมเดลและไฟล์อ้างอิง"),
    el("div", { class: "field" }, el("label", {}, "เลือกประเภทฟิสิกส์"), toolSel),
    el("div", { class: "field" }, 
      el("label", {}, "ไฟล์อ้างอิงแอนิเมชัน (Animation File) *"), 
      animInput.node
    ),
    el("div", { class: "field" }, 
      el("label", {}, "ไฟล์โมเดลสามมิติ (Model File) *"), 
      modelInput.node
    ),
    el("div", { class: "field" }, 
      el("label", {}, "ไฟล์ประกอบชิ้นส่วน (Attachable File) — ว่างได้"), 
      attachInput.node
    )
  );

  // 2. Bone chain & reference workspace (Flexible Layout)
  const bonesContainer = el("div", { style: "display:grid;grid-template-columns:1.8fr 1fr;gap:14px;margin-bottom:14px;" });
  workspace.append(bonesContainer);

  const leftPanel = el("div"); // Bone groups
  const rightPanel = el("div"); // Model bones quick reference
  bonesContainer.append(leftPanel, rightPanel);

  // Right Panel: Bone Names Search and List (Quick Reference)
  rightPanel.append(el("div", { class: "card", style: "height:100%;display:flex;flex-direction:column;max-height:500px;" },
    el("div", { class: "card-title" }, "กระดูกในโมเดล (Model Bones)"),
    el("div", { class: "field", style: "margin-bottom:8px;" },
      el("input", { type: "text", placeholder: "🔍 ค้นหากระดูก...", id: "bone-search" })
    ),
    el("div", { 
      id: "model-bones-list", 
      style: "flex:1;overflow-y:auto;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;padding:8px;" 
    })
  ));

  const searchInput = rightPanel.querySelector("#bone-search");
  const bonesListContainer = rightPanel.querySelector("#model-bones-list");

  const populateModelBones = () => {
    bonesListContainer.innerHTML = "";
    const filter = searchInput.value.trim().toLowerCase();
    const matches = (att.bones || []).filter(b => !filter || b.toLowerCase().includes(filter));

    if (!matches.length) {
      bonesListContainer.innerHTML = '<span style="font-size:12px;color:var(--text-muted);">ไม่พบกระดูก</span>';
      return;
    }

    matches.forEach(boneName => {
      const pill = el("span", { 
        class: "tag", 
        style: "display:inline-block;margin:3px;cursor:pointer;user-select:none;transition:background 0.15s;",
        title: "คลิกเพื่อใส่ในกลุ่มกระดูกที่กำลังพิมพ์"
      }, boneName);
      
      pill.addEventListener("click", () => {
        if (lastFocusedTextarea) {
          const area = lastFocusedTextarea;
          const val = area.value.trim();
          const lines = val ? val.split("\n").map(s => s.trim()) : [];
          if (!lines.includes(boneName)) {
            lines.push(boneName);
            area.value = lines.join("\n");
            area.dispatchEvent(new Event("input"));
          }
        } else {
          toast.info("กรุณาคลิกเลือกช่องกรอกกระดูก (Textarea) ของกลุ่มที่ต้องการเพิ่มก่อน แล้วค่อยคลิกเลือกกระดูกครับ");
        }
      });

      // Hover glow effect
      pill.addEventListener("mouseenter", () => pill.style.background = "var(--bg-hover)");
      pill.addEventListener("mouseleave", () => pill.style.background = "");

      bonesListContainer.append(pill);
    });
  };

  searchInput.addEventListener("input", populateModelBones);
  populateModelBones();

  // Left Panel: Bone Groups Configurator
  let activeGroups = [];

  const renderGroupList = () => {
    leftPanel.innerHTML = "";
    leftPanel.append(el("div", { class: "card-title", style: "margin-bottom:10px;" }, "กลุ่มกระดูกที่ต้องการใส่ฟิสิกส์"));

    if (!activeGroups.length) {
      leftPanel.append(el("div", { class: "placeholder", style: "padding:20px;border:1px dashed var(--border);border-radius:6px;margin-bottom:10px;" }, 
        "ไม่พบกลุ่มกระดูกอัตโนมัติ กรุณากดปุ่มเพิ่มกลุ่มกระดูกด้านล่าง"
      ));
    }

    activeGroups.forEach((group, index) => {
      const prefixInput = el("input", { type: "text", value: group.prefix, placeholder: "เช่น hair_back_" });
      const bonesArea = el("textarea", { 
        rows: 5, 
        placeholder: "ใส่ชื่อกระดูกทีละบรรทัด\nเช่น\nhair_1\nhair_2",
        style: "font-family:var(--font-mono);font-size:12px;margin-top:6px;"
      }, (group.bones || []).join("\n"));

      // Track last focused textarea for quick pill insert
      bonesArea.addEventListener("focus", () => {
        lastFocusedTextarea = bonesArea;
        // visual indicator on active textarea
        document.querySelectorAll(".bone-group-card").forEach(c => c.style.borderColor = "");
        groupCard.style.borderColor = "var(--neon-cyan)";
      });

      prefixInput.addEventListener("input", () => {
        group.prefix = prefixInput.value.trim();
      });

      bonesArea.addEventListener("input", () => {
        group.bones = bonesArea.value.split("\n").map(s => s.trim()).filter(Boolean);
      });

      const delBtn = el("button", { class: "btn-danger btn-sm", style: "align-self:flex-start;margin-top:6px;" }, icon("trash", { size: 13 }), " ลบกลุ่ม");
      delBtn.addEventListener("click", () => {
        activeGroups.splice(index, 1);
        if (lastFocusedTextarea === bonesArea) lastFocusedTextarea = null;
        renderGroupList();
      });

      const groupCard = el("div", { 
        class: "bone-group-card",
        style: "background:var(--bg-3);border:1px solid var(--border);border-radius:6px;padding:12px;margin-bottom:10px;display:flex;flex-direction:column;transition:border-color 0.15s;" 
      },
        el("div", { class: "row", style: "gap:10px;align-items:center;" },
          el("span", { style: "font-size:13px;font-weight:600;min-width:90px;" }, "คำนำหน้า (Prefix)"),
          prefixInput
        ),
        bonesArea,
        delBtn
      );

      leftPanel.append(groupCard);
    });

    const addGroupBtn = el("button", { class: "btn-ghost btn-sm", style: "margin-top:4px;" }, icon("plus", { size: 14 }), " เพิ่มกลุ่มกระดูก (+ Add)");
    addGroupBtn.addEventListener("click", () => {
      activeGroups.push({ prefix: "new_group_", bones: [] });
      renderGroupList();
    });

    leftPanel.append(addGroupBtn);
  };

  // Initialize with discovered chains
  activeGroups = JSON.parse(JSON.stringify(att.discovered_chains || []));
  renderGroupList();

  // Listen for model changes to extract new bones automatically
  modelInput.node.addEventListener("change", async () => {
    const mp = modelInput.value();
    if (!mp) return;
    try {
      const res = await api.post("/api/physics/extract_model", { model_path: mp });
      att.bones = res.bones || [];
      att.discovered_chains = res.discovered_chains || [];
      activeGroups = JSON.parse(JSON.stringify(att.discovered_chains));
      populateModelBones();
      renderGroupList();
      toast.success("อัปเดตกระดูกตามโมเดลใหม่แล้ว");
    } catch (e) {
      toast.error("ดึงกระดูกล้มเหลว: " + e.message);
    }
  });

  // 3. Tuning & Action Controls Card
  const tuningCard = el("div", { class: "card", style: "margin-bottom:14px;" });
  workspace.append(tuningCard);

  // Strength & Intensity selectors
  const intensitySel = el("select", {},
    el("option", { value: "light" }, "เบา (Light)"),
    el("option", { value: "medium", selected: "" }, "ปานกลาง (Medium)"),
    el("option", { value: "strong" }, "แรง (Strong)")
  );
  
  const strengthInput = el("input", { type: "number", step: "0.1", min: "0.3", max: "3.0", placeholder: "ว่าง = auto (0.3–3.0)" });

  const intensityField = el("div", { class: "field", style: "display:none;" }, el("label", {}, "ระดับความเข้มข้นฟิสิกส์ (Intensity)"), intensitySel);
  const strengthField = el("div", { class: "field", style: "display:none;" }, el("label", {}, "ตัวคูณความแรงฟิสิกส์ (Strength Multiplier)"), strengthInput);

  tuningCard.append(
    el("div", { class: "card-title" }, "การปรับแต่งและเรียกทำงาน"),
    intensityField,
    strengthField
  );

  // Toggle fields visibility based on tool selection
  const updateTuningFields = () => {
    const tool = tools.find(t => t.id === toolSel.value);
    if (!tool) return;
    
    // Check if tool uses prefix_intensity
    intensityField.style.display = tool.mode === "prefix_intensity" ? "block" : "none";
    // Check if tool uses prefix_strength
    strengthField.style.display = tool.mode === "prefix_strength" ? "block" : "none";

    // Show/hide bones/prefixes layout based on tool
    if (tool.id === "head") {
      bonesContainer.style.display = "none";
      // Render head bone input if not exists
      if (!tuningCard.querySelector("#head-bone-input-field")) {
        tuningCard.insertBefore(el("div", { class: "field", id: "head-bone-input-field" },
          el("label", {}, "ชื่อกระดูกส่วนหัว (Head Bone Name)"),
          el("input", { type: "text", id: "head-bone-name-in", value: "head", placeholder: "เช่น head หรือ Head" })
        ), applyBtn);
      }
    } else {
      bonesContainer.style.display = "grid";
      const hfield = tuningCard.querySelector("#head-bone-input-field");
      if (hfield) hfield.remove();
    }
  };

  const logBox = el("div", { class: "log-box", style: "display:none;margin-top:14px" });
  workspace.append(logBox);

  const applyBtn = el("button", { class: "btn-primary", style: "width:100%;margin-top:14px;padding:12px;" }, 
    icon("settings", { size: 16 }), " เริ่มการคำนวณและติดตั้งฟิสิกส์"
  );
  tuningCard.append(applyBtn);

  toolSel.addEventListener("change", updateTuningFields);
  updateTuningFields();

  applyBtn.addEventListener("click", async () => {
    const tool = tools.find(t => t.id === toolSel.value);
    const headField = tuningCard.querySelector("#head-bone-name-in");
    
    const body = {
      tool: tool.id,
      animation_path: animInput.value().trim(),
      model_path: modelInput.value().trim() || null,
      attachable_path: attachInput.value().trim() || null,
      prefixes: [], // Not used when bone_groups are provided
      bone_groups: activeGroups.map(g => ({
        prefix: g.prefix,
        bones: g.bones
      })),
      bone_name: headField ? headField.value.trim() : null,
      intensity: intensitySel.value,
      strength: strengthInput.value ? parseFloat(strengthInput.value) : null,
      source_path: selectedSourcePath
    };

    applyBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "⚙️ กำลังทำการคำนวณและเขียนไฟล์แอดออน...";
    const t = toast.progress("กำลังใส่ฟิสิกส์...");

    try {
      const res = await api.post("/api/physics/apply", body);
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, "✅ ติดตั้งฟิสิกส์อัจฉริยะเสร็จสมบูรณ์เรียบร้อยแล้ว!\n\n" + (res.log || []).join("\n")));
      logBox.append(el("span", {}, "\n\n💾 ไฟล์สำรองดั้งเดิมเขียนไว้ที่:\n" + (res.backups || []).join("\n")));
      
      if (res.exported_path && selectedSourcePath.includes("bright_studio_uploads")) {
        const dlUrl = getApiBase() + "/api/dialog/download?path=" + encodeURIComponent(res.exported_path);
        const a = el("a", { href: dlUrl, download: "", style: "display:none;" });
        document.body.append(a);
        a.click();
        a.remove();
        logBox.append(el("span", { style: "color:var(--neon-cyan);display:block;margin-top:10px;font-weight:bold;" }, `📥 กำลังดาวน์โหลดแอดออนลงเครื่องของคุณ: ${res.exported_path.split(/[\\/]/).pop()}`));
      }
      
      t.success("ใส่ฟิสิกส์สำเร็จ");
    } catch (e) {
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-err" }, "❌ ผิดพลาด: " + e.message));
      t.error("ใส่ฟิสิกส์ไม่สำเร็จ: " + e.message);
    } finally {
      applyBtn.disabled = false;
    }
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
      toast.error("เลือกไฟล์ไม่ได้: " + e.message);
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
