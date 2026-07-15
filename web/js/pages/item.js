import { api, el, pickSingle, renderValidation, resolveDroppedFile } from "../api.js";
import { icon as uiIcon } from "../ui/icons.js";
import { toast } from "../ui/toast.js";

export function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "สร้างไอเทม/อาวุธ"),
    el("div", { class: "page-desc" }, "เพิ่มไอเทมถือได้ลง BP/RP ที่มีอยู่ — ใส่โมเดล + texture แล้วเชื่อม attachable อัตโนมัติ (อ่าน geometry id จากไฟล์เอง)")
  ));

  const addonName = el("input", { type: "text", placeholder: "เช่น Soen Sword" });
  const outDir = compactDropzone("ว่าง = Projects/ (ค่าเริ่มต้น)", [], "", "folder");
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "1. สร้างแอดออนใหม่"),
    el("div", { class: "field" }, el("label", {}, "ชื่อ Add-on *"), addonName),
    el("div", { class: "field" }, el("label", {}, "โฟลเดอร์ปลายทาง (output)"), outDir.node),
    el("div", { class: "field-hint" }, "ระบบสร้าง BP + RP + manifest ให้อัตโนมัติ"),
  ));

  const ns = el("input", { type: "text", placeholder: "เช่น soen" });
  const nm = el("input", { type: "text", placeholder: "เช่น sword" });
  const dn = el("input", { type: "text", placeholder: "ชื่อที่โชว์ในเกม (§ สีได้)" });
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "2. ข้อมูลไอเทม"),
    el("div", { class: "row" },
      el("div", { class: "field" }, el("label", {}, "Namespace"), ns),
      el("div", { class: "field" }, el("label", {}, "ชื่อไอเทม (id)"), nm),
    ),
    el("div", { class: "field" }, el("label", {}, "Display name"), dn),
    el("div", { class: "field-hint" }, "identifier = namespace:ชื่อไอเทม (a-z, 0-9, _)"),
  ));

  const model = compactDropzone("ลากไฟล์โมเดล (.geo.json) มาวาง หรือคลิกเพื่อเลือก *", ["JSON (*.json)"]);
  const mtex = compactDropzone("ลากไฟล์ Texture โมเดล (.png) มาวาง หรือคลิกเพื่อเลือก *", ["Images (*.png)"]);
  const icon = compactDropzone("ลากไฟล์ Icon inventory (.png) มาวาง หรือคลิกเพื่อเลือก *", ["Images (*.png)"]);
  const anim = compactDropzone("ลากไฟล์ Held animation (.json) มาวาง หรือคลิกเพื่อเลือก (optional)", ["JSON (*.json)"]);
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "3. โมเดล & เท็กซ์เจอร์"),
    el("div", { class: "field" }, el("label", {}, "โมเดล (.geo.json) * — geometry id อ่านอัตโนมัติ"), model.node),
    el("div", { class: "field" }, el("label", {}, "Texture โมเดล (.png) *"), mtex.node),
    el("div", { class: "field" }, el("label", {}, "Icon inventory (.png) *"), icon.node),
    el("div", { class: "field" }, el("label", {}, "Held animation (optional)"), anim.node),
  ));

  const dmg = el("input", { type: "number", step: "1", placeholder: "เช่น 20 (ว่าง = ไม่ใส่)" });
  const cd = el("input", { type: "number", step: "0.1", placeholder: "วินาที เช่น 0.5 (ว่าง = ไม่ใส่)" });
  const cat = el("select", {}, ...["equipment", "items", "nature", "construction", "none"].map(c => el("option", { value: c }, c)));
  const enchSlot = el("select", {},
    el("option", { value: "" }, "ไม่มี"),
    ...["sword", "axe", "pickaxe", "shovel", "bow", "crossbow", "trident", "all", "melee_weapon", "mining", "armor_feet", "armor_head"].map(s => el("option", { value: s }, s)),
  );
  const enchVal = el("input", { type: "number", step: "1", placeholder: "14" });
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "4. คุณสมบัติ (optional)"),
    el("div", { class: "row" },
      el("div", { class: "field" }, el("label", {}, "Damage"), dmg),
      el("div", { class: "field" }, el("label", {}, "Cooldown (วิ)"), cd),
      el("div", { class: "field" }, el("label", {}, "หมวดเมนู"), cat),
    ),
    el("div", { class: "row" },
      el("div", { class: "field" }, el("label", {}, "Enchant slot"), enchSlot),
      el("div", { class: "field" }, el("label", {}, "Enchant value"), enchVal),
    ),
  ));

  const buildBtn = el("button", { class: "btn-primary" }, uiIcon("dagger", { size: 15 }), " สร้างไอเทม");
  const logBox = el("div", { class: "log-box", style: "display:none;margin-top:14px" });
  main.append(el("div", { class: "card" }, el("div", { class: "card-title" }, "5. สร้าง"), buildBtn, logBox));

  buildBtn.addEventListener("click", async () => {
    const body = {
      addon_name: addonName.value.trim(),
      output_dir: outDir.value() || null,
      namespace: ns.value.trim(), item_name: nm.value.trim(),
      display_name: dn.value.trim() || null,
      model_path: model.value(), model_texture_path: mtex.value(), icon_path: icon.value(),
      held_animation_path: anim.value() || null,
      menu_category: cat.value,
      damage: dmg.value ? parseInt(dmg.value) : null,
      enchantable_slot: enchSlot.value || null,
      enchantable_value: enchVal.value ? parseInt(enchVal.value) : null,
      cooldown_seconds: cd.value ? parseFloat(cd.value) : null,
    };
    if (!body.addon_name) { toast.error("ใส่ชื่อ Add-on"); return; }
    if (!body.namespace || !body.item_name) { toast.error("ใส่ namespace + ชื่อไอเทม"); return; }
    if (!body.model_path || !body.model_texture_path || !body.icon_path) { toast.error("ใส่โมเดล + texture + icon"); return; }
    buildBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังสร้าง...";
    const t = toast.progress("กำลังสร้างไอเทม...");
    try {
      const res = await api.post("/api/weapon/item", body);
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, (res.log || []).join("\n")));
      logBox.append(el("span", {}, `\n\n📁 ${res.project_path || res.bp_path}\n🔗 geometry: ${res.geometry_id}\n🎮 ${res.give_command}`));
      const v = renderValidation(res.validation);
      if (v) logBox.append(v);
      t.success("สร้างไอเทมสำเร็จ: " + res.give_command);
    } catch (e) {
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
      t.error("สร้างไอเทมไม่สำเร็จ: " + e.message);
    } finally {
      buildBtn.disabled = false;
    }
  });
}

function compactDropzone(placeholder, filters, initialValue = "", mode = "open_file") {
  let value = initialValue;
  
  const iconEl = el("span", { class: "cd-icon" }, uiIcon(mode === "folder" ? "folder" : "upload", { size: 14 }));
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
