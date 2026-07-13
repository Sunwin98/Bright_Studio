// Model zone — AI model generation via Meshy (image/text → 3D → Bedrock geo.json).
// Layout: controls (left) + permanent preview stage (right). The stage shows an
// idle state, an in-progress build animation with live %, then a 3D orbit view
// (model-viewer via backend proxy — no CORS), and the export card underneath.
import { api, el, pickSingle, getApiBase } from "../api.js";
import { icon } from "../ui/icons.js";

let pollTimer = null;
const proxied = (url) => getApiBase() + "/api/modelgen/proxy?url=" + encodeURIComponent(url);

function ensureModelViewer() {
  if (window.customElements && customElements.get("model-viewer")) return;
  if (document.getElementById("mv-script")) return;
  const s = document.createElement("script");
  s.id = "mv-script";
  s.type = "module";
  s.src = "https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js";
  document.head.append(s);
}

export async function render(main) {
  main.innerHTML = "";
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  ensureModelViewer();

  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "โมเดล AI · モデル"),
    el("div", { class: "page-desc" },
      "ปั้นโมเดล 3D จากรูปหรือข้อความ (Meshy) → ดูตัวอย่างหมุนได้ → ส่งออกเป็น geo.json + texture ใส่ Bedrock")
  ));

  const root = el("div", {});
  main.append(root);

  let cfg;
  try { cfg = await api.get("/api/modelgen/config"); }
  catch (e) { root.append(el("div", { class: "empty" }, "โหลดไม่ได้: " + e.message)); return; }

  if (!cfg.has_key) { keyGate(root, main); return; }
  buildStudio(root);
}

function keyGate(root, main) {
  const keyInput = el("input", { type: "password", placeholder: "วาง Meshy API key (msy_...)" });
  const saveKey = el("button", { class: "btn-primary btn-sm" }, "บันทึก key");
  const st = el("div", { class: "field-hint" }, "");
  saveKey.addEventListener("click", async () => {
    if (!keyInput.value.trim()) return;
    st.textContent = "กำลังบันทึก...";
    try { await api.post("/api/modelgen/key", { key: keyInput.value.trim() }); render(main); }
    catch (e) { st.textContent = "❌ " + e.message; }
  });
  root.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "ตั้งค่า Meshy API key"),
    el("div", { class: "field-hint", style: "margin-bottom:8px" },
      "สมัคร key ฟรีที่ meshy.ai → Settings → API. key เก็บในเครื่อง (settings.json)"),
    el("div", { class: "file-pick" }, keyInput, saveKey), st));
}

function buildStudio(root) {
  let mode = "image";
  let current = null;   // { mode, taskId } ของงานที่โชว์อยู่
  let selectedPath = "";

  // ════════ LEFT: controls ════════
  const tabImage = el("button", { class: "fm-tab active" }, icon("image", { size: 14 }), " จากรูป");
  const tabText = el("button", { class: "fm-tab" }, icon("book", { size: 14 }), " จากข้อความ");

  const imgThumb = el("div", { class: "mg-img-thumb", style: "display:none; margin-top:8px;" });
  const dropzone = el("div", { class: "mg-dropzone" },
    el("div", { class: "mg-dropzone-inner" },
      icon("image", { size: 24 }),
      el("span", {}, "โยนไฟล์ภาพที่นี่ หรือ คลิกเพื่อเลือกรูป")
    )
  );

  const selectImage = async () => {
    const p = await pickSingle({ mode: "open_file", filters: [".png", ".jpg", ".jpeg"] });
    if (p) {
      selectedPath = p;
      dropzone.querySelector("span").textContent = "เลือกรูปแล้ว: " + p.split(/[\\/]/).pop();
      showLocalThumb(p);
    }
  };
  dropzone.addEventListener("click", selectImage);

  // drag-and-drop events
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) {
      const p = file.path; // WebView2/Neutralino local path
      if (p && (p.endsWith(".png") || p.endsWith(".jpg") || p.endsWith(".jpeg") || p.endsWith(".PNG") || p.endsWith(".JPG") || p.endsWith(".JPEG"))) {
        selectedPath = p;
        dropzone.querySelector("span").textContent = "เลือกรูปแล้ว: " + p.split(/[\\/]/).pop();
        showLocalThumb(p);
      } else if (!p) {
        alert("โปรแกรมเข้าถึงเส้นทางไฟล์ไม่ได้ กรุณาใช้คลิกเลือกรูปแทน");
      } else {
        alert("กรุณาใช้ไฟล์รูปภาพ (.png, .jpg, .jpeg) เท่านั้น");
      }
    }
  });

  const showLocalThumb = (p) => {
    imgThumb.innerHTML = "";
    imgThumb.style.display = "";
    imgThumb.append(el("img", { src: getApiBase() + "/api/fm/icon?path=" + encodeURIComponent(p) }));
  };

  const imageBox = el("div", {},
    dropzone,
    imgThumb,
    el("div", { class: "field-hint", style: "margin-top:6px" }, "รูปพื้นหลังโล่ง วัตถุชัดๆ ได้ผลดีสุด"));

  const promptInput = el("textarea", { placeholder: "อธิบายโมเดล เช่น: a cute cartoon sword with blue gem", rows: "3" });
  const artStyle = el("select", { style: "width:auto" },
    el("option", { value: "realistic", selected: "" }, "สมจริง (realistic)"),
    el("option", { value: "sculpture" }, "ปั้น (sculpture)"));
  const textBox = el("div", { style: "display:none" },
    el("div", { class: "field" }, promptInput),
    el("div", { class: "row", style: "gap:10px;align-items:center" },
      el("label", { style: "margin:0" }, "สไตล์:"), artStyle));

  const detail = el("select", {},
    el("option", { value: "1500" }, "ต่ำ ~1.5k polys (เบา เหมาะไอเทม)"),
    el("option", { value: "4000", selected: "" }, "กลาง ~4k polys"),
    el("option", { value: "10000" }, "สูง ~10k polys (หนักเกม)"));
  const genBtn = el("button", { class: "btn-primary", style: "width:100%; padding: 12px; font-size: 15px;" }, icon("rocket", { size: 18 }), " สร้างโมเดล");

  const exportSlot = el("div", { style: "display:none; margin-bottom:12px;" });

  const controls = el("div", { class: "mg-controls" },
    el("div", { class: "fm-tabs", style: "margin-bottom:12px" }, tabImage, tabText),
    el("div", { class: "card", style: "margin-bottom:12px" }, imageBox, textBox),
    el("div", { class: "card", style: "margin-bottom:12px" },
      el("div", { class: "field" }, el("label", {}, "รายละเอียดโมเดล"), detail),
      genBtn),
    exportSlot,
    el("div", { class: "card mg-recent-card" },
      el("div", { class: "card-title" }, "งานล่าสุด (เปิดซ้ำได้ ไม่เสียเครดิต)"),
      el("div", { class: "mg-recent", html: '<div class="spinner-inline">กำลังโหลด...</div>' })),
  );

  // ════════ RIGHT: preview stage ════════
  const stage = el("div", { class: "mg-stage" });
  const right = el("div", { class: "mg-right" }, stage);

  root.append(el("div", { class: "mg-layout" }, controls, right));

  // ---- stage states ----
  const stageIdle = () => {
    stage.innerHTML = "";
    stage.append(el("div", { class: "mg-idle" },
      el("div", { class: "mg-idle-icon" }, icon("cube", { size: 52 })),
      el("div", { class: "mg-idle-text" }, "พรีวิวโมเดลจะขึ้นที่นี่"),
      el("div", { class: "field-hint" }, "เลือกรูปหรือพิมพ์คำอธิบาย แล้วกด สร้างโมเดล")));
    exportSlot.innerHTML = "";
    exportSlot.style.display = "none";
  };

  let progEls = null;
  const stageGenerating = (label) => {
    stage.innerHTML = "";
    exportSlot.innerHTML = "";
    exportSlot.style.display = "none";
    const bar = el("div", { class: "mg-prog-fill" });
    const pct = el("div", { class: "mg-prog-pct" }, "0%");
    const phase = el("div", { class: "mg-prog-phase" }, label);
    stage.append(el("div", { class: "mg-building" },
      el("div", { class: "mg-forge" },
        el("div", { class: "mg-forge-cube c1" }), el("div", { class: "mg-forge-cube c2" }),
        el("div", { class: "mg-forge-cube c3" }), el("div", { class: "mg-forge-cube c4" }),
        el("div", { class: "mg-forge-glow" })),
      pct, phase,
      el("div", { class: "mg-prog" }, bar),
      el("div", { class: "mg-scanline" })));
    progEls = { bar, pct, phase };
  };
  const setProgress = (p, label) => {
    if (!progEls) return;
    progEls.bar.style.width = (p || 0) + "%";
    progEls.pct.textContent = (p || 0) + "%";
    if (label) progEls.phase.textContent = label;
  };

  const stageResult = async (s, { isPreview }) => {
    stage.innerHTML = "";
    const glb = (s.model_urls || {}).glb;
    let shown = false;
    if (glb) {
      try { await Promise.race([customElements.whenDefined("model-viewer"), new Promise((_, rj) => setTimeout(rj, 4000))]); } catch {}
      if (customElements.get("model-viewer")) {
        const mv = document.createElement("model-viewer");
        mv.setAttribute("src", proxied(glb));
        mv.setAttribute("camera-controls", "");
        mv.setAttribute("auto-rotate", "");
        mv.setAttribute("interaction-prompt", "none");
        mv.setAttribute("shadow-intensity", "1");
        mv.setAttribute("exposure", "1.1");
        // lazy reveal ไม่ trigger ใน layout นี้ — บังคับโหลดทันที
        mv.setAttribute("loading", "eager");
        mv.setAttribute("reveal", "auto");
        mv.className = "mg-mv";
        stage.append(mv);
        shown = true;
      }
    }
    if (!shown && s.thumbnail_url) {
      stage.append(el("img", { class: "mg-thumb", src: proxied(s.thumbnail_url) }));
      shown = true;
    }
    if (!shown) stage.append(el("div", { class: "empty" }, "ไม่มีไฟล์พรีวิว"));
    stage.append(el("div", { class: "mg-stage-badge" + (isPreview ? " warn" : "") },
      isPreview ? "พรีวิว (ยังไม่มีเท็กซ์เจอร์)" : "พร้อมส่งออก"));
  };

  // ---- polling ----
  const stopPoll = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } };
  const poll = (pollMode, taskId, label, onDone) => {
    stopPoll();
    pollTimer = setInterval(async () => {
      if (!document.body.contains(stage)) { stopPoll(); return; }
      try {
        const s = await api.get(`/api/modelgen/status?mode=${pollMode}&task_id=${encodeURIComponent(taskId)}`);
        setProgress(s.progress, `${label} · ${s.status}`);
        if (s.status === "SUCCEEDED") { stopPoll(); onDone(s); }
        else if (s.status === "FAILED" || s.status === "CANCELED") {
          stopPoll(); genBtn.disabled = false;
          stage.innerHTML = "";
          stage.append(el("div", { class: "mg-idle" },
            el("div", { class: "log-err" }, "❌ ล้มเหลว: " + (s.task_error || s.status))));
        }
      } catch { /* transient */ }
    }, 4000);
  };

  const showFinal = (pollMode, taskId, s) => {
    current = { mode: pollMode, taskId };
    stageResult(s, { isPreview: false });
    exportSlot.innerHTML = "";
    exportSlot.style.display = "";
    exportSlot.append(buildExport(pollMode, taskId));
    genBtn.disabled = false;
    loadRecent();
  };

  const showPreviewPhase = (taskId, s) => {
    current = { mode: "text", taskId };
    stageResult(s, { isPreview: true });
    exportSlot.innerHTML = "";
    exportSlot.style.display = "";
    const refineBtn = el("button", { class: "btn-primary" }, icon("palette", { size: 15 }), " ใส่เท็กซ์เจอร์ + ทำต่อ");
    const rst = el("span", { class: "field-hint", style: "margin-left:8px" }, "");
    refineBtn.addEventListener("click", async () => {
      refineBtn.disabled = true;
      try {
        const r = await api.post("/api/modelgen/text-refine", { preview_task_id: taskId });
        stageGenerating("กำลังใส่เท็กซ์เจอร์ (refine)...");
        poll("text", r.task_id, "ใส่เท็กซ์เจอร์", (fs) => showFinal("text", r.task_id, fs));
      } catch (e) { rst.textContent = "❌ " + e.message; refineBtn.disabled = false; }
    });
    exportSlot.append(el("div", { class: "card" },
      el("div", { class: "card-title" }, "ขั้นต่อไป"),
      el("div", { class: "field-hint", style: "margin-bottom:8px" }, "พรีวิวโอเคแล้วกดใส่เท็กซ์เจอร์ เพื่อให้ส่งออกพร้อมภาพลาย"),
      el("div", {}, refineBtn, rst)));
    genBtn.disabled = false;
  };

  // ---- generate ----
  genBtn.addEventListener("click", async () => {
    const poly = parseInt(detail.value, 10);
    genBtn.disabled = true;
    try {
      if (mode === "image") {
        const p = selectedPath.trim();
        if (!p) { alert("เลือกรูปก่อน"); genBtn.disabled = false; return; }
        stageGenerating("กำลังปั้นโมเดลจากรูป... (~1-3 นาที)");
        const r = await api.post("/api/modelgen/image", { image_path: p, target_polycount: poly });
        poll("image", r.task_id, "ปั้นจากรูป", (s) => showFinal("image", r.task_id, s));
      } else {
        const t = promptInput.value.trim();
        if (!t) { alert("ใส่คำอธิบายก่อน"); genBtn.disabled = false; return; }
        stageGenerating("กำลังปั้นพรีวิวจากข้อความ... (~1-2 นาที)");
        const r = await api.post("/api/modelgen/text", { prompt: t, art_style: artStyle.value, target_polycount: poly });
        poll("text", r.task_id, "พรีวิว", (s) => showPreviewPhase(r.task_id, s));
      }
    } catch (e) {
      genBtn.disabled = false;
      stage.innerHTML = "";
      stage.append(el("div", { class: "mg-idle" }, el("div", { class: "log-err" }, "❌ " + e.message)));
    }
  });

  // ---- recent tasks ----
  const recentBox = controls.querySelector(".mg-recent");
  async function loadRecent() {
    try {
      const r = await api.get("/api/modelgen/recent");
      recentBox.innerHTML = "";
      const done = (r.tasks || []).filter(t => t.status === "SUCCEEDED");
      if (!done.length) { recentBox.append(el("div", { class: "field-hint" }, "ยังไม่มีงานเก่า")); return; }
      for (const t of done.slice(0, 8)) {
        const item = el("div", { class: "mg-recent-item", title: t.prompt || t.task_id },
          t.thumbnail_url ? el("img", { src: proxied(t.thumbnail_url) }) : el("span", {}, icon("cube", { size: 20 })));
        item.addEventListener("click", async () => {
          try {
            const s = await api.get(`/api/modelgen/status?mode=${t.mode}&task_id=${encodeURIComponent(t.task_id)}`);
            showFinal(t.mode, t.task_id, s);
          } catch (e) { alert("เปิดไม่ได้: " + e.message); }
        });
        recentBox.append(item);
      }
    } catch (e) {
      recentBox.innerHTML = "";
      recentBox.append(el("div", { class: "field-hint" }, "โหลดงานเก่าไม่ได้: " + e.message));
    }
  }

  // ---- tabs ----
  const setMode = (m) => {
    mode = m;
    tabImage.classList.toggle("active", m === "image");
    tabText.classList.toggle("active", m === "text");
    imageBox.style.display = m === "image" ? "" : "none";
    textBox.style.display = m === "text" ? "" : "none";
  };
  tabImage.addEventListener("click", () => setMode("image"));
  tabText.addEventListener("click", () => setMode("text"));

  stageIdle();
  loadRecent();
}

function buildExport(mode, taskId) {
  const nameInput = el("input", { type: "text", placeholder: "ชื่อโมเดล เช่น dragon_sword" });
  const outInput = el("input", { type: "text", placeholder: "ว่าง = Projects/ai_models" });
  const pickOut = el("button", { class: "btn-ghost btn-sm" }, icon("folder", { size: 15 }));
  pickOut.addEventListener("click", async () => {
    const p = await pickSingle({ mode: "folder" });
    if (p) outInput.value = p;
  });
  const sizeSel = el("select", { style: "width:auto" },
    el("option", { value: "16", selected: "" }, "1 บล็อก (16u)"),
    el("option", { value: "8" }, "เล็ก (8u)"),
    el("option", { value: "24" }, "ใหญ่ (24u)"),
    el("option", { value: "32" }, "ใหญ่มาก (32u)"));
  const exportBtn = el("button", { class: "btn-primary" }, icon("save", { size: 15 }), " ส่งออก geo.json + texture");
  const st = el("div", { class: "field-hint", style: "min-height:18px;margin-top:6px" }, "");

  exportBtn.addEventListener("click", async () => {
    if (!nameInput.value.trim()) { st.textContent = "ตั้งชื่อก่อน"; return; }
    exportBtn.disabled = true;
    st.className = "field-hint";
    st.textContent = "กำลังดาวน์โหลด + แปลงเป็น geo.json...";
    try {
      const r = await api.post("/api/modelgen/export", {
        mode, task_id: taskId, name: nameInput.value.trim(),
        output_dir: outInput.value.trim() || null, target_size: parseFloat(sizeSel.value),
      });
      st.innerHTML = "";
      st.className = "log-ok";
      const openBtn = el("button", { class: "btn-ghost btn-sm", style: "margin-top:8px" }, icon("folder-open", { size: 14 }), " เปิดโฟลเดอร์");
      openBtn.addEventListener("click", () => api.post("/api/projects/open-folder", { path: r.output_dir }).catch(() => {}));
      st.append(
        el("div", {}, `✅ เสร็จ! (${r.polys} polys)`),
        el("div", {}, "geo: " + r.geo_path),
        el("div", {}, r.texture_path ? "texture: " + r.texture_path : "— ไม่มี texture"),
        el("div", { style: "margin-top:4px" }, "identifier: " + r.identifier),
        openBtn,
      );
      exportBtn.disabled = false;
    } catch (e) {
      st.className = "field-hint log-err";
      st.textContent = "❌ " + e.message;
      exportBtn.disabled = false;
    }
  });

  return el("div", { class: "card" },
    el("div", { class: "card-title" }, "ส่งออกเป็น Bedrock geo.json"),
    el("div", { class: "row", style: "gap:10px;flex-wrap:wrap;align-items:flex-end" },
      el("div", { class: "field", style: "flex:1;min-width:160px;margin:0" }, el("label", {}, "ชื่อ"), nameInput),
      el("div", { class: "field", style: "margin:0" }, el("label", {}, "ขนาดในเกม"), sizeSel)),
    el("div", { class: "field", style: "margin-top:8px" }, el("label", {}, "โฟลเดอร์ปลายทาง"),
      el("div", { class: "file-pick" }, outInput, pickOut)),
    el("div", { style: "margin-top:10px" }, exportBtn),
    st);
}
