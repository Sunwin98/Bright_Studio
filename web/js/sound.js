const ctx = new (window.AudioContext || window.webkitAudioContext)();

let sfxEnabled = localStorage.getItem("hs_sfx") !== "false";
let bgmEnabled = localStorage.getItem("hs_bgm") === "true";

export function playHover() {
  if (!sfxEnabled) return;
  if (ctx.state === 'suspended') ctx.resume();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.setValueAtTime(600, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.05);
  gain.gain.setValueAtTime(0, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(0.03, ctx.currentTime + 0.02);
  gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.05);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.05);
}

export function playClick() {
  if (!sfxEnabled) return;
  if (ctx.state === 'suspended') ctx.resume();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'triangle';
  osc.frequency.setValueAtTime(400, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.1);
  gain.gain.setValueAtTime(0, ctx.currentTime);
  gain.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 0.02);
  gain.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.1);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 0.1);
}

// BGM: ใช้ไฟล์จริง web/assets/bgm.mp3 ถ้ามี (วางไฟล์ lo-fi CC0 เองได้เลย);
// ไม่มีไฟล์ → fallback เสียง ambient hum จาก oscillator แบบเดิม
let bgmOsc = null;
let bgmGain = null;
let bgmAudio = null;
let bgmFileMissing = false;

function startOsc() {
  if (bgmOsc) return;
  if (ctx.state === 'suspended') ctx.resume();
  bgmOsc = ctx.createOscillator();
  bgmGain = ctx.createGain();
  bgmOsc.type = 'sine';
  bgmOsc.frequency.value = 110; // Low A
  bgmGain.gain.value = 0.02; // Very quiet
  bgmOsc.connect(bgmGain);
  bgmGain.connect(ctx.destination);
  bgmOsc.start();
}

function stopOsc() {
  if (!bgmOsc) return;
  bgmOsc.stop();
  bgmOsc.disconnect();
  bgmGain.disconnect();
  bgmOsc = null;
  bgmGain = null;
}

export function setBGM(enabled) {
  bgmEnabled = enabled;
  localStorage.setItem("hs_bgm", enabled);
  if (!enabled) {
    stopOsc();
    if (bgmAudio) bgmAudio.pause();
    return;
  }
  if (bgmFileMissing) { startOsc(); return; }
  if (!bgmAudio) {
    bgmAudio = new Audio("/assets/bgm.mp3");
    bgmAudio.loop = true;
    bgmAudio.volume = 0.25;
    bgmAudio.addEventListener("error", () => {
      bgmFileMissing = true;
      bgmAudio = null;
      if (bgmEnabled) startOsc();
    });
  }
  bgmAudio.play().catch(() => { /* autoplay policy — จะเริ่มหลัง user คลิกครั้งแรก */ });
}

// true = มีไฟล์เพลงจริงให้เล่น (ให้หน้า settings โชว์ hint ได้)
export function hasBgmFile() {
  return !bgmFileMissing;
}

export function setSFX(enabled) {
  sfxEnabled = enabled;
  localStorage.setItem("hs_sfx", enabled);
}

export function getSettings() {
  return { sfx: sfxEnabled, bgm: bgmEnabled };
}

export function setupUI() {
  document.body.addEventListener('mouseenter', (e) => {
    if (e.target.matches('button, .tab-item, .fm-card, .kb-doc-item')) playHover();
  }, true);
  document.body.addEventListener('click', (e) => {
    if (e.target.matches('button, .tab-item, .fm-card, .kb-doc-item')) playClick();
  }, true);
  // BGM ที่เปิดค้างไว้: เริ่มเล่นหลัง user มี gesture แรก (autoplay policy)
  const resume = () => { if (bgmEnabled) setBGM(true); };
  document.body.addEventListener('click', resume, { once: true });
}
