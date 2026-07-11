// รันเฉพาะใน Neutralino จริง: spawn backend.exe แล้วตั้ง HS_API_BASE
// (neutralino.js define window.Neutralino เสมอแม้ในเบราว์เซอร์ — ต้องเช็ค NL_PORT
// ซึ่งถูก inject โดย Neutralino server เท่านั้น)
window.HS_IS_NEU = !!(window.Neutralino && typeof NL_PORT !== "undefined");
if (window.HS_IS_NEU) {
  Neutralino.init();
  let proc = null;
  
  window.hsShutdown = async () => {
    if (proc) {
      await Neutralino.os.updateSpawnedProcess(proc.id, "exit").catch(() => {});
      if (proc.pid) await Neutralino.os.execCommand(`taskkill /F /PID ${proc.pid} /T`).catch(() => {});
    }
    await Neutralino.app.exit();
  };
  Neutralino.events.on("windowClose", () => window.hsShutdown());

  (async () => {
    try {
      const dev = await fetch("http://127.0.0.1:8777/api/health");
      if (dev.ok) {
        window.HS_API_BASE = "http://127.0.0.1:8777";
        // flag ก่อน dispatch — กัน race ที่ event ยิงก่อน app.js (module) ติด listener
        window.HS_BACKEND_READY = true;
        window.dispatchEvent(new Event("hs-backend-ready"));
        return;
      }
    } catch {}

    const port = 20000 + Math.floor(Math.random() * 20000);
    window.HS_API_BASE = `http://127.0.0.1:${port}`;
    const exe = NL_PATH + "/backend/backend.exe";

    try {
      await Neutralino.filesystem.getStats(exe);
    } catch (e) {
      window.dispatchEvent(new CustomEvent("hs-backend-failed", { detail: "ไม่พบ backend/backend.exe — รัน build.bat ก่อน" }));
      return;
    }

    Neutralino.os.spawnProcess(`"${exe}" --port ${port}`).then(p => proc = p);
    
    const t0 = Date.now();
    const poll = async () => {
      try {
        const r = await fetch(window.HS_API_BASE + "/api/health");
        if (r.ok) {
          window.HS_BACKEND_READY = true;
          return window.dispatchEvent(new Event("hs-backend-ready"));
        }
      } catch {}
      if (Date.now() - t0 < 20000) setTimeout(poll, 300); 
      else window.dispatchEvent(new CustomEvent("hs-backend-failed", { detail: "Backend Start Failed!" }));
    };
    poll();
  })();
}
