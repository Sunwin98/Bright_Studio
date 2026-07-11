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

let bgmOsc = null;
let bgmGain = null;

export function setBGM(enabled) {
  bgmEnabled = enabled;
  localStorage.setItem("hs_bgm", enabled);
  if (enabled) {
    if (ctx.state === 'suspended') ctx.resume();
    if (!bgmOsc) {
      bgmOsc = ctx.createOscillator();
      bgmGain = ctx.createGain();
      bgmOsc.type = 'sine';
      bgmOsc.frequency.value = 110; // Low A
      bgmGain.gain.value = 0.02; // Very quiet
      bgmOsc.connect(bgmGain);
      bgmGain.connect(ctx.destination);
      bgmOsc.start();
    }
  } else {
    if (bgmOsc) {
      bgmOsc.stop();
      bgmOsc.disconnect();
      bgmGain.disconnect();
      bgmOsc = null;
      bgmGain = null;
    }
  }
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
}
