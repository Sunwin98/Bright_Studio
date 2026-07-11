import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";

let WORKSPACE = null;
let activeFile = null;
let sourceInput;
let workbench;
let notice;
let fileList;
let fieldBody;
let fileTitle;
let fileDescription;
let fieldCount;
let searchInput;
let skillSelect;
let saveButton;
let exportButton;
let dirtyStatus;
let codeButton;
let codeMeta;
let codePanel;
let loadedCodePath = null;

const ROLE_LABELS = { Entry: "ไฟล์เริ่มระบบ", Config: "ไฟล์ตั้งค่า", Skill: "ไฟล์สกิล", Utility: "ไฟล์ช่วยทำงาน" };
const SEMANTIC_LABELS = {
  Damage: "ความแรง", Cooldown: "คูลดาวน์", Duration: "ระยะเวลา", Radius: "รัศมี",
  Range: "ระยะ", Mana: "มานา", Particle: "เอฟเฟกต์", Sound: "เสียง",
  "Item ID": "ไอเทม", Identifier: "รหัส", Speed: "ความเร็ว", Count: "จำนวน",
  Chance: "โอกาส", Amplifier: "ระดับเอฟเฟกต์", Heal: "ฟื้นพลัง", Value: "ค่าอื่น ๆ",
};

export async function render(main) {
  WORKSPACE = null;
  activeFile = null;
  main.innerHTML = "";

  main.append(
    el("div", { class: "page-header wcst-header" },
      el("div", { class: "wcst-step" }, "เครื่องมือตั้งค่าสกิลและอาวุธ"),
      el("div", { class: "page-title" }, "ตั้งค่าอาวุธขั้นสูง"),
      el("div", { class: "page-desc" }, "เลือกแอดออน แล้วปรับค่าจากตารางได้โดยไม่ต้องแก้โค้ดเอง"),
    ),
  );

  sourceInput = el("input", { type: "text", placeholder: "เลือกไฟล์ .mcaddon หรือวางที่อยู่โฟลเดอร์แอดออน", "aria-label": "ไฟล์หรือโฟลเดอร์แอดออน" });
  const browseAddon = el("button", { class: "btn-ghost", type: "button" }, icon("folder-open", { size: 15 }), " เลือกไฟล์แอดออน");
  const browseFolder = el("button", { class: "btn-ghost", type: "button" }, "เลือกโฟลเดอร์");
  const scanButton = el("button", { class: "btn-primary", type: "button" }, icon("search", { size: 15 }), " สแกนแอดออน");
  notice = el("div", { class: "wcst-notice" }, "เริ่มจากเลือกไฟล์แอดออนหรือโฟลเดอร์โปรเจกต์");

  main.append(el("section", { class: "wcst-intake" },
    el("div", { class: "wcst-intake-copy" },
      el("strong", {}, "1. เลือกแอดออน"),
      el("span", {}, "ระบบจะอ่านเฉพาะโครงสร้างและค่าที่แก้ได้ โดยไม่รันสคริปต์ของแอดออน"),
    ),
    el("div", { class: "wcst-picker" }, sourceInput, browseAddon, browseFolder, scanButton),
    notice,
  ));

  workbench = el("section", { class: "wcst-workspace", hidden: "hidden" });
  main.append(workbench);
  workbench.append(makeWorkspace());

  const getParentDir = (filePath) => {
    if (!filePath) return "";
    const lastSlash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
    return lastSlash !== -1 ? filePath.substring(0, lastSlash) : "";
  };

  browseAddon.addEventListener("click", async () => {
    try {
      const directory = getParentDir(sourceInput.value.trim());
      const path = await pickSingle({ mode: "open_file", filters: ["Addon (*.mcaddon *.mcpack *.zip)"], directory });
      if (path) sourceInput.value = path;
    } catch (error) { setNotice(`เลือกไฟล์ไม่ได้: ${error.message}`, true); }
  });
  browseFolder.addEventListener("click", async () => {
    try {
      const directory = getParentDir(sourceInput.value.trim());
      const path = await pickSingle({ mode: "folder", directory });
      if (path) sourceInput.value = path;
    } catch (error) { setNotice(`เลือกโฟลเดอร์ไม่ได้: ${error.message}`, true); }
  });
  scanButton.addEventListener("click", async () => {
    const path = sourceInput.value.trim();
    if (!path) { setNotice("เลือกไฟล์ .mcaddon หรือโฟลเดอร์ก่อน", true); return; }
    scanButton.disabled = true;
    setNotice("กำลังสแกนไฟล์และหาค่าที่ปรับได้…");
    try {
      WORKSPACE = await api.post("/api/weapon-config/analyze", { source_path: path });
      activeFile = WORKSPACE.files[0] || null;
      workbench.hidden = false;
      refreshWorkspace();
      setNotice(`พบ ${WORKSPACE.summary.scripts} ไฟล์, ${WORKSPACE.summary.skills} สกิล และ ${WORKSPACE.summary.editable_fields} ค่าที่ปรับได้`);
    } catch (error) {
      workbench.hidden = true;
      setNotice(`สแกนแอดออนไม่ได้: ${error.message}`, true);
    } finally { scanButton.disabled = false; }
  });
}

function makeWorkspace() {
  fileList = el("div", { class: "wcst-file-list" });
  fieldBody = el("tbody", {});
  fileTitle = el("h2", { class: "wcst-file-title" }, "ยังไม่ได้เลือกไฟล์");
  fileDescription = el("p", { class: "wcst-file-description" }, "เลือกไฟล์จากด้านซ้ายเพื่อดูค่าที่แก้ไขได้");
  fieldCount = el("span", { class: "wcst-count" }, "");
  searchInput = el("input", { type: "search", placeholder: "ค้นหาชื่อค่า เช่น damage, cooldown", "aria-label": "ค้นหาค่าที่ต้องการ" });
  skillSelect = el("select", { "aria-label": "กรองตามสกิล" }, el("option", { value: "" }, "ทุกสกิลและค่ากลาง"));
  saveButton = el("button", { class: "btn-primary", type: "button", disabled: "disabled" }, icon("save", { size: 15 }), " บันทึกการแก้ไข");
  exportButton = el("button", { class: "btn-ghost", type: "button" }, icon("archive", { size: 15 }), " ส่งออก .mcaddon");
  dirtyStatus = el("span", { class: "wcst-dirty" }, "ยังไม่มีการแก้ไข");
  codeButton = el("button", { class: "btn-ghost btn-sm", type: "button", disabled: "disabled" }, "ดูโค้ด 300 บรรทัดแรก");
  codeMeta = el("span", { class: "wcst-code-meta" }, "โค้ดจะโหลดเมื่อกดปุ่มนี้เท่านั้น");
  codePanel = el("pre", { class: "wcst-code", hidden: "hidden" });

  searchInput.addEventListener("input", drawFields);
  skillSelect.addEventListener("change", drawFields);
  saveButton.addEventListener("click", saveChanges);
  exportButton.addEventListener("click", exportAddon);
  codeButton.addEventListener("click", loadCodePreview);

  const filePane = el("aside", { class: "wcst-files" },
    el("div", { class: "wcst-pane-title" }, el("span", {}, "2. เลือกไฟล์"), el("small", {}, "ไฟล์สกิลและไฟล์ตั้งค่าที่พบ")),
    fileList,
  );
  const valuesTable = el("table", { class: "wcst-table" },
    el("thead", {}, el("tr", {}, el("th", {}, "สิ่งที่ปรับ"), el("th", {}, "ประเภท"), el("th", {}, "ค่าใหม่"), el("th", {}, "ใช้กับ"))),
    fieldBody,
  );
  const mainPane = el("section", { class: "wcst-editor" },
    el("div", { class: "wcst-editor-head" },
      el("div", {}, fileTitle, fileDescription),
      el("div", { class: "wcst-actions" }, saveButton, exportButton),
    ),
    el("div", { class: "wcst-controls" },
      el("label", {}, el("span", {}, "ค้นหาค่า"), searchInput),
      el("label", {}, el("span", {}, "แสดงเฉพาะสกิล"), skillSelect),
      el("div", { class: "wcst-change-status" }, dirtyStatus, fieldCount),
    ),
    el("div", { class: "wcst-table-wrap" }, valuesTable),
    el("details", { class: "wcst-source" },
      el("summary", {}, "ตรวจสอบโค้ดต้นทาง (ใช้เมื่อจำเป็น)"),
      el("div", { class: "wcst-source-tools" }, codeButton, codeMeta),
      codePanel,
    ),
  );
  return el("div", { class: "wcst-layout" }, filePane, mainPane);
}

function refreshWorkspace() {
  drawFiles();
  resetCodePreview();
  updateSkillOptions();
  drawFields();
  updateDirtyState();
}

function drawFiles() {
  fileList.innerHTML = "";
  for (const file of WORKSPACE.files) {
    const selected = activeFile?.path === file.path;
    const button = el("button", { class: `wcst-file ${selected ? "is-active" : ""}`, type: "button", "aria-pressed": selected ? "true" : "false" },
      el("span", { class: "wcst-file-name" }, file.relative_path),
      el("span", { class: `wcst-role role-${file.role.toLowerCase()}` }, ROLE_LABELS[file.role] || file.role),
      el("small", {}, file.field_count ? `พบ ${file.field_count} ค่าที่ปรับได้` : "ยังไม่พบค่าที่ปรับได้"),
    );
    button.addEventListener("click", () => {
      activeFile = file;
      drawFiles();
      resetCodePreview();
      updateSkillOptions();
      drawFields();
    });
    fileList.append(button);
  }
}

function updateSkillOptions() {
  const current = skillSelect.value;
  skillSelect.innerHTML = "";
  skillSelect.append(el("option", { value: "" }, "ทุกสกิลและค่ากลาง"));
  const skills = [...new Set((activeFile?.fields || []).map(field => field.skill))];
  for (const skill of skills) skillSelect.append(el("option", { value: skill }, skill === "Shared config" || skill === "Shared values" ? "ค่ากลางของไฟล์" : skill));
  skillSelect.value = skills.includes(current) ? current : "";
}

function drawFields() {
  fieldBody.innerHTML = "";
  if (!activeFile) return;
  fileTitle.textContent = activeFile.relative_path;
  const role = ROLE_LABELS[activeFile.role] || activeFile.role;
  fileDescription.textContent = `${role} · เลือกปรับค่าในตาราง แล้วกด “บันทึกการแก้ไข” เมื่อพร้อม`;
  codeButton.disabled = false;

  const query = searchInput.value.trim().toLowerCase();
  const skill = skillSelect.value;
  const fields = activeFile.fields.filter(field => {
    const matchesText = !query || [field.name, field.label, field.semantic, field.skill].join(" ").toLowerCase().includes(query);
    return matchesText && (!skill || field.skill === skill);
  });
  fieldCount.textContent = `แสดง ${fields.length} จาก ${activeFile.fields.length} ค่า`;
  if (!fields.length) {
    fieldBody.append(el("tr", {}, el("td", { colspan: "4", class: "wcst-empty" }, "ไม่พบค่าที่ตรงกับการค้นหา ลองล้างคำค้นหรือเลือกสกิลอื่น")));
    return;
  }
  for (const field of fields) fieldBody.append(renderFieldRow(field));
}

function renderFieldRow(field) {
  const changed = Object.hasOwn(field, "draft");
  const row = el("tr", { class: changed ? "is-changed" : "" });
  const value = changed ? field.draft : field.value;
  const control = inputFor(field, value, row);
  row.append(
    el("td", {}, el("strong", {}, field.label), el("small", { class: "wcst-key" }, field.name)),
    el("td", {}, el("span", { class: "wcst-semantic" }, SEMANTIC_LABELS[field.semantic] || field.semantic)),
    el("td", { class: "wcst-value-cell" }, control),
    el("td", {}, el("span", { class: "wcst-skill" }, translateSkill(field.skill)), el("small", {}, `อยู่บรรทัด ${field.line}`)),
  );
  return row;
}

function inputFor(field, value, row) {
  if (field.value_type === "boolean") {
    const control = el("input", { type: "checkbox" });
    const state = el("span", {}, value ? "เปิด" : "ปิด");
    control.checked = Boolean(value);
    control.addEventListener("change", () => {
      state.textContent = control.checked ? "เปิด" : "ปิด";
      changeField(field, control.checked, row);
    });
    return el("label", { class: "toggle wcst-toggle" }, control, state);
  }
  const control = el("input", { type: field.value_type === "number" ? "number" : "text", value: value == null ? "" : String(value), step: "any" });
  control.addEventListener("input", () => {
    if (field.value_type === "number") {
      if (control.value === "" || !Number.isFinite(Number(control.value))) return;
      changeField(field, Number(control.value), row);
    } else {
      changeField(field, control.value, row);
    }
  });
  return control;
}

function changeField(field, value, row) {
  if (Object.is(value, field.value)) delete field.draft;
  else field.draft = value;
  row.classList.toggle("is-changed", Object.hasOwn(field, "draft"));
  updateDirtyState();
}

function dirtyFields() {
  return (WORKSPACE?.fields || []).filter(field => Object.hasOwn(field, "draft"));
}

function updateDirtyState() {
  const count = dirtyFields().length;
  saveButton.disabled = count === 0;
  dirtyStatus.textContent = count ? `มี ${count} ค่าที่ยังไม่ได้บันทึก` : "ยังไม่มีการแก้ไข";
  dirtyStatus.classList.toggle("has-changes", count > 0);
}

function resetCodePreview() {
  loadedCodePath = null;
  codePanel.hidden = true;
  codePanel.textContent = "";
  codeMeta.textContent = "โค้ดจะโหลดเมื่อกดปุ่มนี้เท่านั้น";
  codeButton.disabled = !activeFile;
}

async function loadCodePreview() {
  if (!activeFile || loadedCodePath === activeFile.path) return;
  codeButton.disabled = true;
  codeMeta.textContent = "กำลังโหลดตัวอย่างโค้ด…";
  try {
    const response = await api.post("/api/weapon-config/script", { path: activeFile.path, max_lines: 300 });
    codePanel.textContent = response.content;
    codePanel.hidden = false;
    loadedCodePath = activeFile.path;
    codeMeta.textContent = response.truncated
      ? `แสดง ${response.shown_lines} จาก ${response.total_lines} บรรทัด เพื่อให้หน้าไม่หน่วง`
      : `ทั้งหมด ${response.total_lines} บรรทัด`;
  } catch (error) {
    codeMeta.textContent = `อ่านโค้ดไม่ได้: ${error.message}`;
  } finally { codeButton.disabled = false; }
}

async function saveChanges() {
  const dirty = dirtyFields();
  if (!dirty.length) return;
  saveButton.disabled = true;
  setNotice("กำลังสำรองไฟล์และบันทึกค่า…");
  try {
    const result = await api.post("/api/weapon-config/save", { edits: dirty.map(field => ({
      path: field.path, start: field.start, end: field.end, original: field.original, value: field.draft,
    })) });
    setNotice(`บันทึกแล้ว ${dirty.length} ค่า และสร้างไฟล์สำรอง ${result.saved.length} ไฟล์`);
    const selectedPath = activeFile?.path;
    WORKSPACE = await api.post("/api/weapon-config/analyze", { source_path: WORKSPACE.source });
    activeFile = WORKSPACE.files.find(file => file.path === selectedPath) || WORKSPACE.files[0];
    refreshWorkspace();
  } catch (error) {
    setNotice(`บันทึกไม่ได้: ${error.message}`, true);
    updateDirtyState();
  }
}

async function exportAddon() {
  if (!WORKSPACE) return;
  exportButton.disabled = true;
  setNotice("กำลังรวมแอดออนเป็นไฟล์ .mcaddon…");
  try {
    const result = await api.post("/api/weapon-config/export", { source_path: WORKSPACE.source });
    setNotice(`ส่งออกแล้ว: ${result.output_path}`);
  } catch (error) {
    setNotice(`ส่งออกไม่ได้: ${error.message}`, true);
  } finally { exportButton.disabled = false; }
}

function translateSkill(skill) {
  if (skill === "Shared config" || skill === "Shared values") return "ค่ากลางของไฟล์";
  return skill;
}

function setNotice(message, error = false) {
  notice.textContent = message;
  notice.classList.toggle("error", error);
}
