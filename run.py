"""Entry point: start the FastAPI server in a background thread, then open a
native desktop window pointing at it. Double-click friendly.

Run with the Python that has the deps installed (py -3.12 run.py on this box).
"""
from __future__ import annotations

import socket
import threading
import time
import urllib.request

import uvicorn

from app.main import app
from app.api import dialogs


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_healthy(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


class WindowApi:
    """Exposed to the frontend as window.pywebview.api — drives the custom
    frameless titlebar (min / maximize toggle / close)."""

    def __init__(self) -> None:
        self._maximized = False

    def _win(self):
        import webview
        return webview.windows[0] if webview.windows else None

    def win_minimize(self) -> None:
        w = self._win()
        if w:
            w.minimize()

    def win_toggle_max(self) -> None:
        w = self._win()
        if not w:
            return
        try:
            if self._maximized:
                w.restore()
            else:
                w.maximize()
            self._maximized = not self._maximized
        except Exception:
            # Older pywebview without maximize(): fall back to fullscreen toggle.
            w.toggle_fullscreen()

    def win_close(self) -> None:
        w = self._win()
        if w:
            w.destroy()


def main() -> None:
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not _wait_healthy(f"{base}/api/health"):
        raise SystemExit("server failed to start")

    import webview

    win = webview.create_window(
        "Bright Studio",
        base,
        width=1280,
        height=800,
        x=100,
        y=100,
        min_size=(960, 640),
        frameless=True,
        easy_drag=False,      # dragging handled by titlebar's -webkit-app-region
        background_color="#0a0a16",
        js_api=WindowApi(),
    )
    dialogs.set_window(win)

    def on_before_show():
        try:
            import ctypes
            hwnd = int(win.native.Handle)
            GWL_STYLE = -16
            WS_SYSMENU = 0x00080000
            WS_MINIMIZEBOX = 0x00020000
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style |= WS_SYSMENU | WS_MINIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            
            # Force repaint to apply the new window styles (SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 2 | 1 | 4 | 0x0020)
        except Exception:
            pass

    win.events.before_show += on_before_show
    webview.start()


if __name__ == "__main__":
    main()
