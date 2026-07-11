import { api, el, pickSingle, renderValidation } from "../api.js";
import { icon as uiIcon } from "../ui/icons.js";

export function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "สร้างไอเทม/อาวุธ"),
    el("div", { class: "page-desc" }, "เพิ่มไอเทมถือได้ลง BP/RP ที่มีอยู่ — ใส่โมเดล + texture แล้วเชื่อม attachable อัตโนมัติ (อ่าน geometry id จากไฟล์เอง)")
  ));

  const addonName = el("input", { type: "text", placeholder: "เช่น Soen Sword" });
  const outDir = pathPicker("ว่าง = Projects/ (ค่าเริ่มต้น)");
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

  const model = filePicker("โมเดล (.geo.json)", ["JSON (*.json)"]);
  const mtex = filePicker("texture ของโมเดล (.png)", ["Images (*.png)"]);
  const icon = filePicker("icon ในช่อง inventory (.png)", ["Images (*.png)"]);
  const anim = filePicker("held animation (.json) — optional", ["JSON (*.json)"]);
  main.append(el("div", { class: "card" },
    el("div", { class: "card-title" }, "3. โมเดล & เท็กซ์เจอร์"),
    el("div", { class: "field" }, el("label", {}, "โมเดล (.geo.json) * — geometry id อ่านอัตโนมัติ"), model.node),
    el("div", { class: "field" }, el("label", {}, "Texture โมเดล (.png) *"), mtex.node),
    el("div", { class: "field" }, el("label", {}, "Icon inventory (.png) *"), icon.node),
    el("div", { class: "field" }, el("label", {}, "Held animation (optional)"), anim.node),
  ));

  const dmg = el("input", { type: "number", step: "1", placeholder: "เช่น 20 (ว่าง = ไม่ใส่)" });
  const enchSlot = el("select", {},
    el("option", { value: "" }, "ไม่มี"),
    ...["sword", "axe", "pickaxe", "shovel", "bow", "crossbow", "trident", "all", "melee_weapon", "mining", "armor_feet", "armor_head"].map(s => el("option", { value: s }, s)),
  );
  const enchVal = el("input", { type: "number", step: "1", placeholder: "14" });
  const cd = el("input", { type: "number", step: "0.1", placeholder: "วินาที เช่น 0.5 (ว่าง = ไม่ใส่)" });
  const cat = el("select", {}, ...["equipment", "items", "nature", "construction", "none"].map(c => el("option", { value: c }, c)));
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
    if (!body.addon_name) { alert("ใส่ชื่อ Add-on"); return; }
    if (!body.namespace || !body.item_name) { alert("ใส่ namespace + ชื่อไอเทม"); return; }
    if (!body.model_path || !body.model_texture_path || !body.icon_path) { alert("ใส่โมเดล + texture + icon"); return; }
    buildBtn.disabled = true;
    logBox.style.display = "block";
    logBox.textContent = "กำลังสร้าง...";
    try {
      const res = await api.post("/api/weapon/item", body);
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-ok" }, (res.log || []).join("\n")));
      logBox.append(el("span", {}, `\n\n📁 ${res.project_path || res.bp_path}\n🔗 geometry: ${res.geometry_id}\n🎮 ${res.give_command}`));
      const v = renderValidation(res.validation);
      if (v) logBox.append(v);
    } catch (e) {
      logBox.innerHTML = "";
      logBox.append(el("span", { class: "log-err" }, "❌ " + e.message));
    } finally {
      buildBtn.disabled = false;
    }
  });
}

function filePicker(placeholder, filters) {
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
      const p = await pickSingle({ mode: "open_file", filters, directory });
      if (p) input.value = p;
    }
    catch (e) { if (e.status === 501) input.focus(); else alert("เลือกไฟล์ไม่ได้: " + e.message); }
  });
  return { node: el("div", { class: "file-pick" }, input, btn), value: () => input.value.trim() };
}

function pathPicker(placeholder) {
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
      const p = await pickSingle({ mode: "folder", directory });
      if (p) input.value = p;
    }
    catch (e) { if (e.status === 501) input.focus(); else alert("เลือกไม่ได้: " + e.message); }
  });
  return { node: el("div", { class: "file-pick" }, input, btn), value: () => input.value.trim() };
}
