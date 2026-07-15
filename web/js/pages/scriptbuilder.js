import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

const ACTIONS = {
  message: { label: "ส่งข้อความ", icon: "message" },
  sound: { label: "เล่นเสียง", icon: "music" },
  effect: { label: "เพิ่ม Effect", icon: "heart" },
  command: { label: "รันคำสั่ง", icon: "code" },
  give: { label: "ให้ไอเทม", icon: "dagger" },
  particle: { label: "สร้าง Particle", icon: "image" },
};

const newBlocks = eventId => eventId === "item_use"
  ? [{ type: "condition", kind: "item", value: { item: "minecraft:stick" } }, { type: "action", kind: "message", value: { text: "ใช้ไอเทมแล้ว" } }]
  : eventId === "tick"
    ? [{ type: "setting", kind: "interval", value: { ticks: 20 } }, { type: "action", kind: "message", value: { text: "ทำงานทุกช่วงเวลา" } }]
    : [{ type: "action", kind: "message", value: { text: "เริ่มทำงานแล้ว" } }];

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "Script Builder"),
    el("div", { class: "page-desc" }, "ต่อเหตุการณ์และการทำงานเป็นบล็อก แล้วสร้างไฟล์สคริปต์ให้พร้อมใช้")
  ));

  const source = el("input", { type: "text", placeholder: "เลือกโฟลเดอร์ Behavior Pack" });
  const pickBtn = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const sourceStatus = el("div", { class: "field-hint", style: "min-height:18px;" }, "เลือกโฟลเดอร์ BP ที่ต้องการสร้างสคริปต์");
  const nameInput = el("input", { type: "text", value: "custom_event", placeholder: "ชื่อระบบ เช่น fire_sword" });
  const eventSelect = el("select", {});
  const addSelect = el("select", { class: "builder-add-select" }, ...Object.entries(ACTIONS).map(([value, action]) => el("option", { value }, action.label)));
  const addBtn = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("folder-plus", { size: 14 }), " เพิ่มการทำงาน");
  const buildBtn = el("button", { class: "btn-primary", type: "button" }, icon("save", { size: 15 }), " สร้างไฟล์สคริปต์");
  const overwrite = el("input", { type: "checkbox" });
  const buildStatus = el("div", { class: "field-hint", style: "min-height:18px;" }, "");
  let bpPath = "";
  let sourceIsArchive = false;
  let blocks = newBlocks("item_use");

  const eventInfo = await api.get("/api/scriptbuilder/events").catch(() => ({ events: [] }));
  for (const event of eventInfo.events || []) eventSelect.append(el("option", { value: event.id }, event.label));
  eventSelect.value = "item_use";

  const resolveSource = async () => {
    const value = source.value.trim();
    bpPath = "";
    sourceIsArchive = /\.(mcaddon|mcpack|zip)$/i.test(value);
    if (!value) { sourceStatus.textContent = "เลือกโฟลเดอร์ BP ที่ต้องการสร้างสคริปต์"; return; }
    sourceStatus.textContent = "กำลังค้นหา Behavior Pack...";
    try {
      const info = await api.post("/api/packio/inspect", { path: value });
      bpPath = info.bp_path || "";
      if (!bpPath) throw new Error("ไม่พบ Behavior Pack");
      sourceStatus.textContent = sourceIsArchive ? "พบ BP แต่การสร้างไฟล์ต้องใช้โฟลเดอร์ BP โดยตรง" : "พบ Behavior Pack พร้อมสร้างไฟล์";
      sourceStatus.className = sourceIsArchive ? "field-hint log-warn" : "field-hint log-ok";
    } catch (error) {
      sourceStatus.textContent = "หา BP ไม่ได้: " + error.message;
      sourceStatus.className = "field-hint log-err";
    }
  };
  pickBtn.addEventListener("click", async () => { const path = await pickSingle({ mode: "folder" }); if (path) { source.value = path; resolveSource(); } });
  source.addEventListener("change", resolveSource);
  if ((params && params.get("open")) || activeProjectOpenPath()) { source.value = params?.get("open") || activeProjectOpenPath(); resolveSource(); }

  const blockValue = (block, key, fallback = "") => block.value?.[key] ?? fallback;
  const updateBlock = (block, key, value) => { block.value = { ...(block.value || {}), [key]: value }; updatePreview(); };

  const blockControl = (block, index) => {
    const remove = el("button", { class: "btn-ghost btn-sm builder-remove", type: "button", title: "เอาบล็อกนี้ออก" }, icon("close", { size: 14 }));
    remove.addEventListener("click", () => { blocks.splice(index, 1); renderBuilder(); updatePreview(); });
    const controls = el("div", { class: "builder-block-controls" });
    if (block.kind === "item") {
      controls.append(el("label", {}, "ไอเทมที่ต้องการ", el("input", { type: "text", value: blockValue(block, "item", "minecraft:stick"), oninput: event => updateBlock(block, "item", event.target.value) })));
    } else if (block.kind === "interval") {
      controls.append(el("label", {}, "ทำซ้ำทุกกี่ Tick", el("input", { type: "number", min: "1", value: blockValue(block, "ticks", 20), oninput: event => updateBlock(block, "ticks", Number(event.target.value) || 20) })));
    } else if (block.kind === "message") {
      controls.append(el("label", {}, "ข้อความ", el("input", { type: "text", value: blockValue(block, "text", "ข้อความจาก Addon"), oninput: event => updateBlock(block, "text", event.target.value) })));
    } else if (block.kind === "sound") {
      controls.append(el("label", {}, "ชื่อเสียง", el("input", { type: "text", value: blockValue(block, "sound", "random.orb"), oninput: event => updateBlock(block, "sound", event.target.value) })));
    } else if (block.kind === "effect") {
      controls.append(el("label", {}, "Effect", el("input", { type: "text", value: blockValue(block, "effect", "speed"), oninput: event => updateBlock(block, "effect", event.target.value) })), el("label", {}, "Tick", el("input", { type: "number", min: "1", value: blockValue(block, "ticks", 100), oninput: event => updateBlock(block, "ticks", Number(event.target.value) || 100) })));
    } else if (block.kind === "command") {
      controls.append(el("label", {}, "คำสั่ง (ไม่ต้องใส่ /)", el("input", { type: "text", value: blockValue(block, "command", "say Hello"), oninput: event => updateBlock(block, "command", event.target.value) })));
    } else if (block.kind === "give") {
      controls.append(el("label", {}, "ไอเทม", el("input", { type: "text", value: blockValue(block, "item", "minecraft:diamond"), oninput: event => updateBlock(block, "item", event.target.value) })), el("label", {}, "จำนวน", el("input", { type: "number", min: "1", value: blockValue(block, "amount", 1), oninput: event => updateBlock(block, "amount", Number(event.target.value) || 1) })));
    } else if (block.kind === "particle") {
      controls.append(el("label", {}, "ชื่อ Particle", el("input", { type: "text", value: blockValue(block, "particle", "minecraft:basic_flame_particle"), oninput: event => updateBlock(block, "particle", event.target.value) })));
    }
    const title = block.type === "condition" ? "เงื่อนไข" : block.type === "setting" ? "ตั้งค่า" : (ACTIONS[block.kind]?.label || "การทำงาน");
    return el("div", { class: `builder-block builder-block-${block.type}` },
      el("div", { class: "builder-block-number" }, String(index + 1).padStart(2, "0")),
      el("div", { class: "builder-block-main" }, el("div", { class: "builder-block-title" }, title), controls),
      remove,
    );
  };

  const blocksWrap = el("div", { class: "builder-blocks" });
  const renderBuilder = () => { blocksWrap.innerHTML = ""; blocks.forEach((block, index) => blocksWrap.append(blockControl(block, index))); };
  addBtn.addEventListener("click", () => { blocks.push({ type: "action", kind: addSelect.value, value: {} }); renderBuilder(); updatePreview(); });
  eventSelect.addEventListener("change", () => { blocks = newBlocks(eventSelect.value); renderBuilder(); updatePreview(); });

  const preview = el("pre", { class: "builder-code" }, "กำลังสร้างตัวอย่าง...");
  let previewTimer;
  const updatePreview = () => {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async () => {
      try { const result = await api.post("/api/scriptbuilder/preview", { bp_path: bpPath || "preview", name: nameInput.value, event_id: eventSelect.value, blocks }); preview.textContent = result.script; }
      catch (error) { preview.textContent = "แก้ข้อมูลบล็อกเพื่อดูตัวอย่างโค้ด"; }
    }, 180);
  };
  nameInput.addEventListener("input", updatePreview);
  buildBtn.addEventListener("click", async () => {
    if (!bpPath || sourceIsArchive) { toast.error("เลือกโฟลเดอร์ Behavior Pack โดยตรงก่อนสร้างไฟล์"); return; }
    buildBtn.disabled = true;
    buildStatus.textContent = "กำลังสร้างไฟล์และบันทึกประวัติ...";
    try {
      const result = await api.post("/api/scriptbuilder/create", { bp_path: bpPath, name: nameInput.value, event_id: eventSelect.value, blocks, overwrite: overwrite.checked });
      buildStatus.textContent = `สร้างแล้ว: ${result.script_path}${result.entry_path ? " · เชื่อมเข้า entry แล้ว" : ""}`;
      toast.success("สร้างสคริปต์แล้ว พร้อมบันทึกประวัติไฟล์");
    } catch (error) { buildStatus.textContent = "สร้างไม่ได้: " + error.message; toast.error("สร้าง Script ไม่ได้: " + error.message); }
    finally { buildBtn.disabled = false; }
  });

  main.append(el("div", { class: "builder-steps" },
    el("div", { class: "builder-step active" }, el("span", {}, "1"), "เลือก BP"), el("span", { class: "builder-step-line" }),
    el("div", { class: "builder-step" }, el("span", {}, "2"), "ต่อบล็อก"), el("span", { class: "builder-step-line" }),
    el("div", { class: "builder-step" }, el("span", {}, "3"), "สร้างไฟล์"),
  ));
  main.append(el("div", { class: "card builder-source-card" },
    el("div", { class: "builder-field-grid" },
      el("div", { class: "field" }, el("label", {}, "Behavior Pack"), el("div", { class: "file-pick" }, source, pickBtn), sourceStatus),
      el("div", { class: "field" }, el("label", {}, "ชื่อระบบ"), nameInput),
      el("div", { class: "field" }, el("label", {}, "เมื่อเกิดเหตุการณ์"), eventSelect),
    ),
  ));
  main.append(el("div", { class: "builder-layout" },
    el("section", { class: "card builder-block-card" },
      el("div", { class: "builder-panel-head" }, el("div", { class: "card-title" }, "ต่อการทำงาน"), el("div", { class: "row" }, addSelect, addBtn)),
      el("div", { class: "field-hint" }, "เรียงจากบนลงล่าง ระบบจะทำตามลำดับที่ต่อไว้"), blocksWrap,
    ),
    el("section", { class: "card builder-preview-card" },
      el("div", { class: "builder-panel-head" }, el("div", { class: "card-title" }, "ตัวอย่างโค้ด"), el("span", { class: "builder-preview-note" }, "ดูได้ก่อนสร้างจริง")),
      preview,
      el("div", { class: "builder-save-row" }, overwrite, el("label", {}, "เขียนทับไฟล์เดิมถ้ามี"), buildBtn),
      buildStatus,
    ),
  ));
  renderBuilder();
  updatePreview();
}
