// Active project — pin one project (from the projects grid or FM) and every
// tool that takes a BP/RP/addon path (Script Lab, checker, weapon, physics,
// deploy) can reuse it instead of re-picking a path on every page.
// Persists across restarts via localStorage; broadcasts changes so the
// titlebar indicator and any open page can react live.
const KEY = "hs_active_project";
const EVENT = "hs-active-project-changed";

// shape: { name, zone, store, paths: {bp?, rp?, folder?, mcaddon?}, pinnedAt }
export function getActiveProject() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setActiveProject(project) {
  const withStamp = { ...project, pinnedAt: Date.now() };
  localStorage.setItem(KEY, JSON.stringify(withStamp));
  window.dispatchEvent(new CustomEvent(EVENT, { detail: withStamp }));
}

export function clearActiveProject() {
  localStorage.removeItem(KEY);
  window.dispatchEvent(new CustomEvent(EVENT, { detail: null }));
}

export function onActiveProjectChanged(fn) {
  window.addEventListener(EVENT, (e) => fn(e.detail));
}

// Best single path for tools that just want "the" addon source to inspect
// (Script Lab / checker / weapon / physics intake): bp > folder > mcaddon > rp.
export function activeProjectOpenPath() {
  const p = getActiveProject();
  if (!p) return null;
  const paths = p.paths || {};
  return paths.bp || paths.folder || paths.mcaddon || paths.rp || null;
}
