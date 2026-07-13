// Titlebar pill showing the pinned "active project" — click it for a quick
// launcher (Script Lab / ตรวจสอบ / Deploy) without navigating to Projects first.
import { api, el } from "../api.js";
import { icon } from "./icons.js";
import { showContextMenu, gotoPage } from "./contextmenu.js";
import { getActiveProject, clearActiveProject, onActiveProjectChanged, activeProjectOpenPath } from "../state/activeProject.js";
import { addPacksToWorldDialog } from "./worldpicker.js";
import { toast } from "./toast.js";

async function quickDeploy(project) {
  const paths = project.paths || {};
  if (!paths.bp && !paths.rp) { toast.error("โปรเจกต์นี้ไม่มี BP/RP ให้ deploy"); return; }
  const t = toast.progress("กำลัง deploy...");
  try {
    const r = await api.post("/api/projects/deploy", { bp_path: paths.bp || null, rp_path: paths.rp || null });
    const packs = r.deployed_packs || [];
    t.success(`deploy ${(r.deployed || []).length} pack แล้ว`);
    if (packs.length) addPacksToWorldDialog(packs);
  } catch (e) {
    t.error("deploy ไม่สำเร็จ: " + e.message);
  }
}

export function mountActiveProjectIndicator(slot) {
  const render = () => {
    const p = getActiveProject();
    slot.innerHTML = "";
    if (!p) { slot.style.display = "none"; return; }
    slot.style.display = "";
    slot.title = activeProjectOpenPath() || "";
    slot.append(
      icon("folder", { size: 13 }),
      el("span", { class: "tb-ap-name" }, p.name),
    );
    const clearBtn = el("button", { class: "tb-ap-clear", title: "เลิกปักหมุดโปรเจกต์" }, icon("close", { size: 11 }));
    clearBtn.addEventListener("click", (e) => { e.stopPropagation(); clearActiveProject(); });
    slot.append(clearBtn);
  };

  slot.addEventListener("click", (e) => {
    const p = getActiveProject();
    if (!p) return;
    const path = activeProjectOpenPath() || "";
    showContextMenu(e.clientX, e.clientY, [
      { label: "เปิดใน Script Lab", icon: "sliders",
        onClick: () => gotoPage("scriptlab?open=" + encodeURIComponent(path)) },
      { label: "ตรวจสอบ Addon", icon: "check-circle",
        onClick: () => gotoPage("checker?open=" + encodeURIComponent(path)) },
      { label: "Deploy + เพิ่มเข้าโลก…", icon: "rocket", onClick: () => quickDeploy(p) },
      "-",
      { label: "เลิกปักหมุด", icon: "close", danger: true, onClick: () => clearActiveProject() },
    ]);
  });

  onActiveProjectChanged(render);
  render();
}
