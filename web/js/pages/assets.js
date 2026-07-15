import { api, el, pickSingle } from "../api.js";
import { icon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";
import { activeProjectOpenPath } from "../state/activeProject.js";

const KIND_LABELS = { texture: "Texture", model: "Model", entity: "Entity", attachable: "Attachable", animation: "Animation", json: "JSON", script: "Script", file: "ไฟล์" };
const KIND_ICONS = { texture: "image", model: "cube", entity: "box", attachable: "dagger", animation: "film", json: "document", script: "code", file: "document" };
const fmtSize = bytes => bytes < 1024 ? `${bytes} B` : bytes < 1048576 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1048576).toFixed(1)} MB`;

export async function render(main, params) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "Asset Preview"),
    el("div", { class: "page-desc" }, "เปิดดู Texture, Model และไฟล์ที่เชื่อมโยงกันใน Addon")
  ));

  const source = el("input", { type: "text", placeholder: "ไฟล์ .mcaddon/.zip หรือโฟลเดอร์ Addon" });
  const pickFile = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("document", { size: 15 }), " เลือกไฟล์");
  const pickFolder = el("button", { class: "btn-ghost btn-sm", type: "button" }, icon("folder", { size: 15 }), " เลือกโฟลเดอร์");
  const scanBtn = el("button", { class: "btn-primary btn-sm", type: "button" }, icon("search", { size: 15 }), " เปิด Asset");
  const status = el("div", { class: "field-hint", style: "min-height:18px;" }, "");
  source.value = (params && params.get("open")) || activeProjectOpenPath() || "";

  const scan = async () => {
    if (!source.value.trim()) { toast.error("เลือกไฟล์หรือโฟลเดอร์ Addon ก่อน"); return; }
    scanBtn.disabled = true;
    status.textContent = "กำลังจัดทำรายการ Asset...";
    try {
      const data = await api.post("/api/assets/scan", { path: source.value.trim() });
      status.textContent = `พบ ${data.total} Asset · เลือกไฟล์ด้านล่างเพื่อดูตัวอย่าง`;
      status.className = "field-hint log-ok";
      renderWorkspace(data);
    } catch (error) {
      status.textContent = "เปิด Asset ไม่ได้: " + error.message;
      status.className = "field-hint log-err";
    } finally { scanBtn.disabled = false; }
  };
  pickFile.addEventListener("click", async () => { const path = await pickSingle({ mode: "open_file", filters: [".mcaddon", ".mcpack", ".zip"] }); if (path) { source.value = path; scan(); } });
  pickFolder.addEventListener("click", async () => { const path = await pickSingle({ mode: "folder" }); if (path) { source.value = path; scan(); } });
  scanBtn.addEventListener("click", scan);
  source.addEventListener("keydown", event => { if (event.key === "Enter") scan(); });

  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "เลือก Addon"),
    el("div", { class: "file-pick" }, source, pickFile, pickFolder, scanBtn),
    status,
  ));
  const workspace = el("div", { class: "asset-workspace" });
  main.append(workspace);

  const renderWorkspace = data => {
    const assets = data.assets || [];
    let selected = assets[0] || null;
    const search = el("input", { type: "text", placeholder: "ค้นหาไฟล์หรือพาธ..." });
    const filter = el("select", {}, el("option", { value: "all" }, "ทุกประเภท"), ...Object.entries(KIND_LABELS).map(([value, label]) => el("option", { value }, label)));
    const list = el("div", { class: "asset-list" });
    const preview = el("div", { class: "asset-preview" });

    const drawPreview = () => {
      preview.innerHTML = "";
      if (!selected) { preview.append(el("div", { class: "empty" }, "เลือก Asset เพื่อดูรายละเอียด")); return; }
      const asset = selected;
      const head = el("div", { class: "asset-preview-head" },
        el("div", {}, el("div", { class: "asset-preview-title" }, asset.name), el("div", { class: "field-hint" }, `${asset.pack} · ${KIND_LABELS[asset.kind] || asset.kind}`)),
        el("span", { class: "asset-type-chip" }, KIND_LABELS[asset.kind] || asset.kind),
      );
      const body = el("div", { class: "asset-preview-body" });
      if (asset.kind === "texture") {
        if (asset.path.toLowerCase().endsWith(".tga")) body.append(el("div", { class: "asset-no-preview" }, icon("image", { size: 28 }), el("div", {}, "TGA ยังแสดงภาพในหน้าต่างนี้ไม่ได้")));
        else body.append(el("img", { class: "asset-image-preview", src: "/api/assets/file?path=" + encodeURIComponent(asset.path), alt: asset.name }));
      } else if (asset.kind === "model") {
        const details = asset.details || {};
        body.append(el("div", { class: "asset-model-summary" },
          el("div", { class: "asset-model-icon" }, icon("cube", { size: 30 })),
          el("div", {}, el("div", { class: "asset-model-id" }, (details.geometry_ids || []).join(", ") || "ไม่พบ geometry identifier"), el("div", { class: "field-hint" }, `${details.geometry_count || 0} geometry · ${details.bone_count || 0} bone`)),
        ));
      } else {
        body.append(el("div", { class: "asset-no-preview" }, icon(KIND_ICONS[asset.kind] || "document", { size: 28 }), el("div", {}, "ไฟล์นี้แสดงข้อมูลความเชื่อมโยงได้ด้านล่าง")));
      }
      body.append(el("div", { class: "asset-meta" }, el("div", {}, "พาธ"), el("code", { title: asset.path }, asset.relative_path), el("div", {}, "ขนาด"), el("span", {}, fmtSize(asset.size))));
      const refs = asset.references || [];
      body.append(el("div", { class: "asset-refs" },
        el("div", { class: "asset-section-title" }, `ถูกใช้งานจาก (${refs.length})`),
        ...(refs.length ? refs.map(ref => el("div", { class: "asset-ref-row" }, icon("link", { size: 14 }), el("span", { title: ref.file }, ref.file), ref.pointer ? el("span", { class: "field-hint" }, ref.pointer) : null)) : [el("div", { class: "field-hint" }, "ยังไม่พบไฟล์ที่อ้างถึง Asset นี้")]),
      ));
      preview.append(head, body);
    };

    const drawList = () => {
      const query = search.value.trim().toLowerCase();
      const kind = filter.value;
      const rows = assets.filter(asset => (!query || `${asset.name} ${asset.relative_path}`.toLowerCase().includes(query)) && (kind === "all" || asset.kind === kind));
      list.innerHTML = "";
      if (!rows.length) { list.append(el("div", { class: "empty" }, "ไม่พบ Asset ตามที่ค้นหา")); return; }
      for (const asset of rows) {
        const row = el("button", { class: "asset-row" + (asset === selected ? " active" : ""), type: "button" },
          el("span", { class: "asset-row-icon" }, icon(KIND_ICONS[asset.kind] || "document", { size: 16 })),
          el("span", { class: "asset-row-copy" }, el("span", { class: "asset-row-name" }, asset.name), el("span", { class: "asset-row-path" }, asset.relative_path)),
          el("span", { class: "asset-row-kind" }, KIND_LABELS[asset.kind] || asset.kind),
        );
        row.addEventListener("click", () => { selected = asset; drawList(); drawPreview(); });
        list.append(row);
      }
    };
    search.addEventListener("input", drawList);
    filter.addEventListener("change", drawList);
    workspace.innerHTML = "";
    workspace.append(el("div", { class: "asset-browser card" }, el("div", { class: "asset-toolbar" }, search, filter, el("span", { class: "count-pill" }, `${assets.length} ไฟล์`)), list), el("div", { class: "asset-preview-card card" }, preview));
    drawList();
    drawPreview();
  };

  if (source.value) scan();
}
