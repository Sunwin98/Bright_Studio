// Shared world-picker dialog — pick a Minecraft world and enable one or more
// packs into it (writes world_*_packs.json via /api/fm/toggle_world_addon).
// Used by the File Manager (single pack) and the projects "Deploy + เพิ่มเข้าโลก"
// pipeline (all deployed BP+RP at once).
import { api, el } from "../api.js";
import { openWindow } from "./window.js";
import { icon } from "./icons.js";

function fmtDate(mtime) {
  if (!mtime) return "";
  const d = new Date(mtime * 1000);
  return "เล่นล่าสุด " + d.toLocaleDateString("th-TH", { year: "numeric", month: "short", day: "numeric" });
}

// packs: [{ type: "behavior"|"resource", name, uuid, raw_version?|version? }]
export async function addPacksToWorldDialog(packs) {
  packs = (packs || []).filter((p) => p && p.uuid);
  const label = packs.length === 1
    ? `"${packs[0].name}" (${packs[0].type === "behavior" ? "BP" : "RP"})`
    : `${packs.length} pack (BP+RP)`;

  const body = el("div", {}, el("div", { class: "loading" }, "กำลังโหลดรายชื่อโลก..."));
  const ctl = openWindow({ title: "เพิ่มเข้าโลก", jp: "ワールドへ", body, width: "min(460px, 90vw)" });

  if (!packs.length) {
    body.innerHTML = "";
    body.append(el("div", { class: "log-err" }, "ไม่มี pack ที่มี uuid ให้เพิ่มเข้าโลก"));
    return;
  }

  // Resolve which profile holds the user's worlds (first "User:" else index 0).
  let profileIdx = 0;
  try {
    const pr = await api.get("/api/fm/profiles");
    const profiles = pr.profiles || [];
    const userIdx = profiles.findIndex((p) => p.name.startsWith("User:"));
    profileIdx = userIdx >= 0 ? userIdx : 0;
  } catch (e) { /* fall back to profile 0 */ }

  try {
    const d = await api.get(`/api/fm/worlds?profile=${profileIdx}`);
    body.innerHTML = "";
    body.append(el("div", { class: "field-hint", style: "margin-bottom:10px" },
      `เลือกโลกที่จะใส่ ${label}`));
    const search = el("input", { type: "text", placeholder: "ค้นหาโลก...", style: "margin-bottom:8px" });
    const list = el("div", {});
    body.append(search, list);

    const draw = () => {
      const q = search.value.trim().toLowerCase();
      list.innerHTML = "";
      for (const w of (d.worlds || []).filter((w) => !q || w.name.toLowerCase().includes(q))) {
        const row = el("div", { class: "fm-card clickable", style: "padding:8px 10px; margin-bottom:6px;" },
          el("div", { class: "fm-card-icon", style: "width:32px;height:32px;" }, icon("globe", { size: 16 })),
          el("div", { class: "fm-card-body" },
            el("div", { class: "fm-card-name" }, w.name),
            el("div", { class: "fm-card-meta" }, fmtDate(w.mtime))));
        row.addEventListener("click", async () => {
          row.style.opacity = ".5";
          try {
            for (const p of packs) {
              await api.post("/api/fm/toggle_world_addon", {
                world_path: w.path, ptype: p.type, pack_id: p.uuid,
                version: p.raw_version || p.version || [1, 0, 0], action: "enable",
              });
            }
            ctl.close();
            const names = packs.map((p) => p.name).join(", ");
            alert(`✅ เพิ่ม ${names} เข้าโลก "${w.name}" แล้ว`);
          } catch (e) { alert("เพิ่มไม่ได้: " + e.message); row.style.opacity = "1"; }
        });
        list.append(row);
      }
      if (!list.children.length) list.append(el("div", { class: "empty" }, "ไม่พบโลก"));
    };
    search.addEventListener("input", draw);
    draw();
  } catch (e) {
    body.innerHTML = "";
    body.append(el("div", { class: "log-err" }, "โหลดโลกไม่ได้: " + e.message));
  }
}
