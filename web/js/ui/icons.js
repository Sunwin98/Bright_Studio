// Line-icon SVG set (Neon Yokochō) — replaces emoji throughout the UI.
// All icons share one 24x24 viewBox, stroke="currentColor" so they inherit
// whatever color the surrounding button/text already uses (incl. hover glow).
import { el } from "../api.js";

const PATHS = {
  // navigation / zones
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/>',
  "folder-open": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2H3z"/><path d="M3 9l1.5 9a2 2 0 0 0 2 1.7h11a2 2 0 0 0 2-1.7L21 9H3z"/>',
  "folder-plus": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/><path d="M12 11v5M9.5 13.5h5"/>',
  archive: '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M4 8v11a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V8"/><path d="M10 13h4"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5z"/><path d="M4 19.5V5.5"/>',
  "sliders": '<path d="M5 4v6M5 14v6M12 4v10M12 18v2M19 4v3M19 11v9"/><circle cx="5" cy="11.5" r="1.8"/><circle cx="12" cy="15.5" r="1.8"/><circle cx="19" cy="8.5" r="1.8"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',

  // tools
  palette: '<path d="M12 3a9 9 0 1 0 6.7 15c.8-.9.3-2.3-.8-2.3h-1.6a2.6 2.6 0 0 1-1.9-4.4c.5-.5 1.2-.8 1.9-.8H19a2 2 0 0 0 2-2A9 9 0 0 0 12 3z"/><circle cx="7.5" cy="10.5" r="1.1" fill="currentColor" stroke="none"/><circle cx="11" cy="7" r="1.1" fill="currentColor" stroke="none"/><circle cx="15.5" cy="8" r="1.1" fill="currentColor" stroke="none"/>',
  waves: '<path d="M2 8c1.5-1.7 3-1.7 4.5 0s3 1.7 4.5 0 3-1.7 4.5 0 3 1.7 4.5 0"/><path d="M2 14c1.5-1.7 3-1.7 4.5 0s3 1.7 4.5 0 3-1.7 4.5 0 3 1.7 4.5 0"/><path d="M2 20c1.5-1.7 3-1.7 4.5 0s3 1.7 4.5 0 3-1.7 4.5 0 3 1.7 4.5 0"/>',
  swords: '<path d="M4 20L20 4M17 4h3v3M8 17l-3 3-2-2 3-3"/><path d="M20 20L4 4M7 4H4v3M16 17l3 3 2-2-3-3"/>',
  dagger: '<path d="M12 2v13"/><path d="M9 5l3-3 3 3-3 3z"/><path d="M7 15h10l-1.5 2H8.5z"/><path d="M12 17v5"/>',
  puzzle: '<path d="M9 4h4v2a1.6 1.6 0 0 0 3.2 0V4H20v4.2h-2a1.6 1.6 0 0 0 0 3.2h2V16h-3.8a1.6 1.6 0 0 0 0 3.2V20H9v-4h-2a1.6 1.6 0 0 1 0-3.2H9V9H6.8a1.6 1.6 0 0 1 0-3.2H9z"/>',
  broom: '<path d="M20 3L10 13"/><path d="M4 21l4-4"/><path d="M7 14l6-6 3 3-6 6z"/><path d="M4 21l3-7 4 4z"/>',
  wrench: '<path d="M14.7 6.3a4 4 0 0 1-5.4 5.4L4 17l3 3 5.3-5.3a4 4 0 0 1 5.4-5.4L21 6z"/>',

  // actions
  check: '<path d="M5 13l4 4L19 7"/>',
  "check-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
  "x-circle": '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5l5 5m0-5l-5 5"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  "chevron-right": '<path d="M9 6l6 6-6 6"/>',
  "chevron-down": '<path d="M6 9l6 6 6-6"/>',
  "arrow-up": '<path d="M12 19V5"/><path d="M6 11l6-6 6 6"/>',
  "external-link": '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.3-4.3"/>',
  save: '<path d="M5 4h11l3 3v13H5z"/><path d="M8 4v5h7V4"/><path d="M8 14h8v6H8z"/>',
  pencil: '<path d="M4 20l1-4 11-11 3 3-11 11z"/><path d="M14 6l3 3"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="1.5"/><path d="M5 15V5.5A1.5 1.5 0 0 1 6.5 4H15"/>',
  trash: '<path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/><path d="M10 11v6M14 11v6"/>',
  refresh: '<path d="M20 11A8 8 0 0 0 5.5 6.5L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.5 4.5L20 16"/><path d="M20 20v-4h-4"/>',
  upload: '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  download: '<path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M4 19h16"/>',
  rocket: '<path d="M12 2c3 1 5 4 5 8 0 3-1.5 5.5-2.5 7l-2.5 3-2.5-3C8.5 15.5 7 13 7 10c0-4 2-7 5-8z"/><circle cx="12" cy="9" r="1.6"/><path d="M9 16l-2.5 1.5L6 21l3.5-1M15 16l2.5 1.5.5 3.5-3.5-1"/>',
  box: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5L12 12l8-4.5"/><path d="M12 12v9"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18 14 14 0 0 1 0-18z"/>',
  film: '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M7 5v14M17 5v14M3 9.5h4M17 9.5h4M3 14.5h4M17 14.5h4"/>',
  eq: '<path d="M4 21V13M4 9V3M12 21v-4M12 13V3M20 21v-8M20 9V3"/><path d="M2 13h4M10 9h4M18 13h4"/>',

  // explorer sidebar / file types
  home: '<path d="M4 11l8-7 8 7"/><path d="M6 10v9a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-9"/><path d="M10 20v-6h4v6"/>',
  document: '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/><path d="M9.5 12h5M9.5 15.5h5"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="1.5"/><circle cx="8.5" cy="9.5" r="1.6"/><path d="M4 17l5-5 3.5 3.5L16 12l5 6"/>',
  music: '<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
  "archive-zip": '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M12 3v3M12 8v2M12 12v2M12 16v2"/>',
  code: '<path d="M8 8L3.5 12 8 16"/><path d="M16 8l4.5 4-4.5 4"/>',
  drive: '<rect x="3" y="6" width="18" height="12" rx="1.5"/><path d="M3 14h18"/><circle cx="7" cy="16" r=".8" fill="currentColor" stroke="none"/>',
  pickaxe: '<path d="M4 8c3-3 7-4.5 11-4 .5 3 0 6-3 9L7 18"/><path d="M6 15l3 3-2 2-3-3z"/>',
};

export function iconSvg(name, { size = 16 } = {}) {
  const body = PATHS[name] || PATHS.document;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="hs-icon-svg">${body}</svg>`;
}

// icon(name, {size, class}) → <span class="hs-icon"> wrapping the inline SVG.
export function icon(name, opts = {}) {
  return el("span", { class: "hs-icon" + (opts.class ? " " + opts.class : ""), html: iconSvg(name, opts) });
}
