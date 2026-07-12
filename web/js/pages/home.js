// หน้าแรก — dashboard: งานล่าสุด, สถิติต่อโซน, ปุ่มลัด.
// Frontend-only: ประกอบจาก API ที่มีอยู่แล้ว (/api/projects?zone, /api/fm/*).
import { api, el, getApiBase } from "../api.js";
import { icon } from "../ui/icons.js";

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return "ดึกแล้ว พักบ้างนะ 🌙";
  if (h < 12) return "สวัสดีตอนเช้า ☀️";
  if (h < 17) return "สวัสดีตอนบ่าย 🌤️";
  return "สวัสดีตอนค่ำ 🌆";
}

function agoText(mtime) {
  if (!mtime) return "";
  const d = (Date.now() / 1000 - mtime) / 86400;
  if (d < 1 / 24) return "เมื่อครู่";
  if (d < 1) return `${Math.floor(d * 24)} ชม.ที่แล้ว`;
  if (d < 30) return `${Math.floor(d)} วันที่แล้ว`;
  return new Date(mtime * 1000).toLocaleDateString("th-TH", { month: "short", day: "numeric" });
}

export async function render(main) {
  main.innerHTML = "";
  main.append(el("div", { class: "page-header" },
    el("div", { class: "page-title" }, "Bright Studio · ホーム"),
    el("div", { class: "page-desc" }, greeting() + " — สรุปงานทั้งหมดในที่เดียว")
  ));

  // ── quick actions ──
  const act = (hash, ic, label) => {
    const b = el("button", { class: "btn-ghost hm-action" }, icon(ic, { size: 18 }), el("span", {}, label));
    b.addEventListener("click", () => { location.hash = "#/" + hash; });
    return b;
  };
  main.append(el("div", { class: "hm-actions" },
    act("skin", "palette", "สร้างสกิน"),
    act("scriptlab", "sliders", "Script Lab"),
    act("filemanager", "folder-open", "จัดการไฟล์"),
    act("checker", "check-circle", "ตรวจสอบ Addon"),
    act("merger", "puzzle", "รวม Addon"),
  ));

  // ── stat cards ──
  const statVal = {};
  const stat = (key, ic, label, hash) => {
    const v = el("div", { class: "hm-stat-num" }, "…");
    statVal[key] = v;
    const card = el("div", { class: "hm-stat" },
      el("div", { class: "hm-stat-icon" }, icon(ic, { size: 20 })),
      el("div", {}, v, el("div", { class: "hm-stat-label" }, label)));
    if (hash) { card.classList.add("clickable"); card.addEventListener("click", () => { location.hash = "#/" + hash; }); }
    return card;
  };
  main.append(el("div", { class: "hm-stats" },
    stat("skin", "palette", "โปรเจกต์สกิน", "projects?zone=skin"),
    stat("skill", "swords", "โปรเจกต์สกิล", "projects?zone=skill"),
    stat("packs", "box", "Addon ในเครื่อง (Shared)", "filemanager"),
    stat("worlds", "globe", "โลกในเครื่อง", "filemanager"),
  ));

  // ── recent projects ──
  const recentWrap = el("div", { class: "card" },
    el("div", { class: "card-title" }, "งานล่าสุด · 最近の作業"),
    el("div", { class: "empty" }, "กำลังโหลด..."));
  main.append(recentWrap);

  // load ทุกอย่างขนานกัน — พังตัวไหนตัวนั้นขึ้น "–" เฉยๆ ไม่ล้มทั้งหน้า
  const [skin, skill, profiles] = await Promise.allSettled([
    api.get("/api/projects?zone=skin"),
    api.get("/api/projects?zone=skill"),
    api.get("/api/fm/profiles"),
  ]);

  const skinProjects = skin.status === "fulfilled" ? skin.value.projects : [];
  const skillProjects = skill.status === "fulfilled" ? skill.value.projects : [];
  statVal.skin.textContent = skin.status === "fulfilled" ? String(skinProjects.length) : "–";
  statVal.skill.textContent = skill.status === "fulfilled" ? String(skillProjects.length) : "–";

  if (profiles.status === "fulfilled") {
    const profs = profiles.value.profiles || [];
    const sharedIdx = profs.findIndex(p => p.name === "Shared Add-ons");
    const userIdx = profs.findIndex(p => p.name.startsWith("User:"));
    const [packs, worlds] = await Promise.allSettled([
      sharedIdx >= 0 ? api.get(`/api/fm/addons?profile=${sharedIdx}`) : Promise.reject(),
      userIdx >= 0 ? api.get(`/api/fm/worlds?profile=${userIdx}`) : Promise.reject(),
    ]);
    statVal.packs.textContent = packs.status === "fulfilled" ? String(packs.value.packs.length) : "–";
    statVal.worlds.textContent = worlds.status === "fulfilled" ? String(worlds.value.worlds.length) : "–";
  } else {
    statVal.packs.textContent = "–";
    statVal.worlds.textContent = "–";
  }

  // recent = รวมสองโซน เรียง mtime
  const recent = [
    ...skinProjects.map(p => ({ ...p, zone: "skin" })),
    ...skillProjects.map(p => ({ ...p, zone: "skill" })),
  ].sort((a, b) => (b.mtime || 0) - (a.mtime || 0)).slice(0, 8);

  recentWrap.querySelector(".empty")?.remove();
  if (!recent.length) {
    recentWrap.append(el("div", { class: "empty" }, "ยังไม่มีโปรเจกต์"));
    return;
  }
  const grid = el("div", { class: "hm-recent" });
  for (const p of recent) {
    const paths = p.paths || {};
    const thumb = el("div", { class: "hm-recent-thumb" }, icon(p.zone === "skin" ? "palette" : "swords", { size: 18 }));
    if (p.has_icon) {
      const q = new URLSearchParams();
      if (paths.bp) q.set("bp", paths.bp);
      if (paths.rp) q.set("rp", paths.rp);
      if (paths.folder) q.set("folder", paths.folder);
      const img = el("img", { src: getApiBase() + "/api/projects/thumbnail?" + q.toString(), width: "38", height: "38", style: "object-fit:cover;border-radius:8px" });
      img.addEventListener("error", () => img.remove());
      thumb.innerHTML = "";
      thumb.append(img);
    }
    const row = el("div", { class: "hm-recent-item" },
      thumb,
      el("div", { class: "hm-recent-body" },
        el("div", { class: "hm-recent-name", title: p.name }, p.name),
        el("div", { class: "hm-recent-meta" },
          (p.zone === "skin" ? "สกิน" : "สกิล") + " · " + agoText(p.mtime)),
      ));
    row.addEventListener("click", () => { location.hash = "#/projects?zone=" + p.zone; });
    grid.append(row);
  }
  recentWrap.append(grid);
}
