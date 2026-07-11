import { api, el, pickSingle, renderValidation } from "../api.js";
import { icon } from "../ui/icons.js";

let selectedSourcePath = "";

export function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "อาวุธ & สกิล (Weapon & Skill)"),
    el("div", { class: "page-desc" }, "TDC Generator — สร้าง entity + สคริปต์ combat/skill ลงใน BP/RP ที่มีอยู่")
  ));

  // 1. Intake Card (Universal Intake)
  const pathDisplay = el("span", { style: "font-family:var(--font-mono);font-size:13px;color:var(--text-muted);word-break:break-all;" }, 
    selectedSourcePath || "กรุณาเลือกไฟล์ .mcaddon หรือโฟลเดอร์แอดออนเพื่อเริ่มต้น"
  );
  
  const pickFolderBtn = el("button", { class: "btn-ghost btn-sm" }, icon("folder", { size: 14 }), " เลือกโฟลเดอร์แอดออน");
  const pickFileBtn = el("button", { class: "btn-ghost btn-sm" }, icon("puzzle", { size: 14 }), " เลือกไฟล์ .mcaddon / .zip");
  
  const loadingText = el("div", { style: "display:none;margin-top:10px;color:var(--neon-cyan);" }, 
    el("span", { class: "spinner-inline" }, "กำลังแกะกล่องและตรวจสอบโครงสร้างแอดออน...")
  );

  const intakeCard = el("div", { class: "card", style: "margin-bottom:14px" },
    el("div", { class: "card-title" }, "นำเข้าไฟล์แอดออน / แหล่งข้อมูล"),
    el("div", { class: "field" },
      el("div", { class: "row", style: "gap:10px;margin-bottom:10px;" },
        pickFolderBtn,
        pickFileBtn
      ),
      el("div", { style: "padding:10px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;display:flex;align-items:center;min-height:38px;" }, 
        pathDisplay
      ),
      loadingText
    )
  );
  main.append(intakeCard);

  // 2. paths
  const genBp = el("input", { type: "checkbox", checked: "" });
  const genRp = el("input", { type: "checkbox", checked: "" });
  const bp = pathPicker("โฟลเดอร์ Behavior Pack (มี manifest.json)");
  const rp = pathPicker("โฟลเดอร์ Resource Pack (มี manifest.json)");
  const pathsCard = el("div", { class: "card", style: "margin-bottom:14px" },
    el("div", { class: "card-title" }, "1. โฟลเดอร์แพ็ค"),
    el("div", { class: "field" }, el("label", { class: "toggle" }, genBp, "สร้างไฟล์ฝั่ง BP"), bp.node),
    el("div", { class: "field" }, el("label", { class: "toggle" }, genRp, "สร้างไฟล์ฝั่ง RP"), rp.node),
  );
  main.append(pathsCard);

  // 3. items
  const itemPickers = [];
  const itemsCard = el("div", { class: "card", style: "margin-bottom:14px" }, el("div", { class: "card-title" }, "2. ไฟล์ไอเทม JSON (สูงสุด 5)"));
  for (let i = 0; i < 5; i++) {
    const p = pathPicker(`ไอเทมชิ้นที่ ${i + 1} (.json)`, ["JSON (*.json)"], true);
    itemPickers.push(p);
    itemsCard.append(el("div", { class: "field" }, p.node));
  }
  main.append(itemsCard);

  // 4. entity toggles
  const opts = {};
  const mk = (key, checked) => { const c = el("input", { type: "checkbox" }); if (checked) c.checked = true; opts[key] = c; return c; };
  const rows = [];
  for (let j = 1; j <= 3; j++) {
    rows.push(el("div", { class: "row" },
      el("label", { class: "toggle", style: "flex:1" }, mk(`atk${j}`, j <= 3), `Attack ${j}`),
      el("label", { class: "toggle", style: "flex:1" }, mk(`atk${j}_sec`, false), `Attack ${j} (รอง)`),
      el("label", { class: "toggle", style: "flex:1" }, mk(`sk${j}`, j === 1), `Skill ${j}`),
      el("label", { class: "toggle", style: "flex:1" }, mk(`sk${j}_sec`, false), `Skill ${j} (รอง)`),
    ));
  }
  const optsCard = el("div", { class: "card", style: "margin-bottom:14px" },
    el("div", { class: "card-title" }, "3. เลือก Entity ที่จะสร้าง"), ...rows);
  main.append(optsCard);

  // 5. generate
  const genBtn = el("button", { class: "btn-primary" }, icon("rocket", { size: 15 }), " สร้าง Add-on");
  const logBox = el("div", { class: "log-box", style: "display:none;margin-top:14px" });
  main.append(el("div", { class: "card" }, el("div", { class: "card-title" }, "4. สร้าง"), genBtn, logBox));

  const handleInspect = async (path) => {
    if (!path) return;
    selectedSourcePath = path;
    pathDisplay.textContent = path;
    loadingText.style.display = "block";

    try {
      const data = await api.post("/api/weapon/inspect", { path });
      loadingText.style.display = "none";
      
      if (data.bp_path) bp.input.value = data.bp_path;
      if (data.rp_path) rp.input.value = data.rp_path;
      
      // Reset items first
      itemPickers.forEach(p => p.input.value = "");
      
      if (data.items && data.items.length) {
        data.items.slice(0, 5).forEach((item, index) => {
          itemPickers[index].input.value = item.file_path;
        });
      }
    } catch (e) {
      loadingText.style.display = "none";
      alert("ตรวจสอบแอดออนล้มเหลว: " + e.message);
    }
  };

  pickFolderBtn.addEventListener("click", async () => {
    try {
      const p = await pickSingle({ mode: "folder" });
      if (p) handleInspect(p);
    } catch (e) {
      alert("เลือกโฟลเดอร์ไม่ได้: " + e.message);
    }
  });

  pickFileBtn.addEventListener("click", async () => {
    try {
      const p = await pickSingle({ mode: "open_file", filters: ["Addon (*.mcaddon)", "Pack (*.mcpack)", "Archive (*.zip)"] });
      if (p) handleInspect(p);
    } catch (e) {
      alert("เลือกไฟล์ไม่ได้: " + e.message);
    }
  });

  // Restore path display if previously selected
  if (selectedSourcePath) {
    handleInspect(selectedSourcePath);
  }

  genBtn.addEventListener("click", async () => {
    const items = itemPickers.map(p => p.value()).filter(Boolean);
    if (!items.length) { alert("เลือกไฟล์ไอเทม JSON อย่างน้อย 1 ชิ้น"); return; }
    const entity_opts = {};
    for (const k in opts) entity_opts[k] = opts[k].checked;
    const body = {
      bp_path: bp.value(), rp_path: rp.value(),
      gen_bp: genBp.checked, gen_rp: genRp.checked,
      items, entity_opts,
    };
    genBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังสร้าง...";
    try {
      const res = await api.post("/api/weapon/generate", body);
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, (res.log || []).join("\n")));
      const v = renderValidation(res.validation);
      if (v) logBox.append(v);
    } catch (e) {
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
    } finally {
      genBtn.disabled = false;
    }
  });
}

function pathPicker(placeholder, filters, isFile) {
  const input = el("input", { type: "text", placeholder });
  const btn = el("button", { class: "btn-ghost btn-sm" }, "เลือก");
  
  const getParentDir = (filePath) => {
    if (!filePath) return "";
    const lastSlash = Math.max(filePath.lastIndexOf("/"), filePath.lastIndexOf("\\"));
    return lastSlash !== -1 ? filePath.substring(0, lastSlash) : "";
  };

  btn.addEventListener("click", async () => {
    try {
      const directory = getParentDir(input.value.trim());
      const p = await pickSingle({ mode: isFile ? "open_file" : "folder", filters, directory });
      if (p) input.value = p;
    } catch (e) {
      if (e.status === 501) input.focus();
      else alert("เลือกไม่ได้: " + e.message);
    }
  });
  return { node: el("div", { class: "file-pick" }, input, btn), value: () => input.value.trim(), input };
}
