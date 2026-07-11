"""Central paths and brand constants for Bright Studio.

Edit these if the workspace moves. Everything else in the app reads from here,
so the original tools/assets stay where they are — nothing is duplicated.
"""
from pathlib import Path

# --- Studio itself ---
STUDIO_ROOT = Path(__file__).resolve().parent
WEB_DIR = STUDIO_ROOT / "web"

# --- Existing Heaven Send Factory workspace ---
FACTORY_ROOT = Path(r"D:\heaven send\Heaven_Send_Factory")
MASTER_ASSETS = FACTORY_ROOT / "master_assets"

# Project stores (scanned by the Project Browser)
PROJECT_STORES = [
    FACTORY_ROOT / "Projects",
    FACTORY_ROOT / "Projects Sillkes",
]

# Default output dir for newly built skin addons
DEFAULT_OUTPUT_DIR = FACTORY_ROOT / "Projects"

# --- Knowledge base (markdown docs) ---
KNOWLEDGE_DIRS = [
    Path(r"D:\Bedrock_Addon_Skills"),
    FACTORY_ROOT / "Projects Sillkes" / "Projects SafeZoneCraft" / "safezone-bedrock-addon",
    FACTORY_ROOT / "Projects Sillkes" / "Projects SafeZoneCraft",
]

# --- Tool zones: each sidebar zone scans its own project stores ---
ZONE_STORES: dict[str, list[Path]] = {
    "skin": [FACTORY_ROOT / "Projects"],
    "skill": [FACTORY_ROOT / "Projects Sillkes"],
}

# --- Brand constants (mirror the CLI tools) ---
STORE_NAME = "Bright"
CREATOR_NAME = "Bright"
FILE_PREFIX = "heaver"

# --- Minecraft Bedrock com.mojang (for Deploy). Set MC_COM_MOJANG_OVERRIDE to
# force a path; otherwise the common UWP/Preview install locations are probed. ---
import os as _os

MC_COM_MOJANG_OVERRIDE: str | None = None


def find_com_mojang() -> Path | None:
    if MC_COM_MOJANG_OVERRIDE:
        p = Path(MC_COM_MOJANG_OVERRIDE)
        return p if p.exists() else None
    local = _os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local) / "Packages" / "Microsoft.MinecraftUWP_8wekyb3d8bbwe" / "LocalState" / "games" / "com.mojang",
        Path(local) / "Packages" / "Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe" / "LocalState" / "games" / "com.mojang",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_profiles() -> list[dict]:
    """All Minecraft Bedrock com.mojang roots on this machine.

    Mirrors the reference app's scanProfiles(): official UWP, Preview/Beta, and
    every launcher user under %APPDATA%\\Minecraft Bedrock\\Users. Each entry is
    {"name": str, "path": str}. An explicit MC_COM_MOJANG_OVERRIDE wins and is
    returned alone.
    """
    if MC_COM_MOJANG_OVERRIDE:
        p = Path(MC_COM_MOJANG_OVERRIDE)
        return [{"name": "Custom (override)", "path": str(p)}] if p.exists() else []

    profiles: list[dict] = []
    seen: set[str] = set()

    def add(name: str, path: Path) -> None:
        if path.is_dir():
            key = str(path).lower()
            if key not in seen:
                seen.add(key)
                profiles.append({"name": name, "path": str(path)})

    local = _os.environ.get("LOCALAPPDATA", "")
    if local:
        pkgs = Path(local) / "Packages"
        add("Minecraft (UWP)", pkgs / "Microsoft.MinecraftUWP_8wekyb3d8bbwe" / "LocalState" / "games" / "com.mojang")
        add("Minecraft Preview", pkgs / "Microsoft.MinecraftWindowsBeta_8wekyb3d8bbwe" / "LocalState" / "games" / "com.mojang")

    appdata = _os.environ.get("APPDATA", "")
    if appdata:
        users_root = Path(appdata) / "Minecraft Bedrock" / "Users"
        if users_root.is_dir():
            for user in users_root.iterdir():
                if user.is_dir():
                    label = "Shared Add-ons" if user.name == "Shared" else f"User: {user.name}"
                    add(label, user / "games" / "com.mojang")

    return profiles


# --- User-editable settings (Settings tab) ---------------------------------
# Persisted to settings.json next to this file. Loaded once at import time so
# every module that did `import config` (not `from config import X`) sees the
# overridden values immediately — no restart needed after Save.
import sys as _sys
import os as _os
import json as _json

if getattr(_sys, "frozen", False):
    _app_data = Path(_os.environ.get("APPDATA", str(STUDIO_ROOT))) / "BrightStudio"
    _app_data.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE = _app_data / "settings.json"
else:
    SETTINGS_FILE = STUDIO_ROOT / "settings.json"

_EDITABLE_LIST_PATHS = ("PROJECT_STORES", "KNOWLEDGE_DIRS")
_EDITABLE_SINGLE_PATHS = ("MASTER_ASSETS", "DEFAULT_OUTPUT_DIR")


def load_settings() -> None:
    global PROJECT_STORES, MASTER_ASSETS, DEFAULT_OUTPUT_DIR, KNOWLEDGE_DIRS, MC_COM_MOJANG_OVERRIDE, ZONE_STORES
    if not SETTINGS_FILE.exists():
        return
    try:
        data = _json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
    if data.get("project_stores"):
        PROJECT_STORES = [Path(p) for p in data["project_stores"]]
    if isinstance(data.get("zone_stores"), dict):
        ZONE_STORES = {k: [Path(p) for p in v] for k, v in data["zone_stores"].items() if isinstance(v, list)}
    if data.get("master_assets"):
        MASTER_ASSETS = Path(data["master_assets"])
    if data.get("default_output_dir"):
        DEFAULT_OUTPUT_DIR = Path(data["default_output_dir"])
    if data.get("knowledge_dirs"):
        KNOWLEDGE_DIRS = [Path(p) for p in data["knowledge_dirs"]]
    if "mc_com_mojang_override" in data:
        MC_COM_MOJANG_OVERRIDE = data["mc_com_mojang_override"] or None


def get_settings() -> dict:
    detected = find_com_mojang()
    return {
        "project_stores": [str(p) for p in PROJECT_STORES],
        "master_assets": str(MASTER_ASSETS),
        "default_output_dir": str(DEFAULT_OUTPUT_DIR),
        "knowledge_dirs": [str(p) for p in KNOWLEDGE_DIRS],
        "mc_com_mojang_override": MC_COM_MOJANG_OVERRIDE,
        "com_mojang_detected": str(detected) if detected else None,
        "zone_stores": {k: [str(p) for p in v] for k, v in ZONE_STORES.items()},
    }


def save_settings(data: dict) -> dict:
    global PROJECT_STORES, MASTER_ASSETS, DEFAULT_OUTPUT_DIR, KNOWLEDGE_DIRS, MC_COM_MOJANG_OVERRIDE, ZONE_STORES

    stores = [s.strip() for s in data.get("project_stores", []) if s and s.strip()]
    zone_stores_in = data.get("zone_stores")
    if isinstance(zone_stores_in, dict):
        ZONE_STORES = {k: [Path(s.strip()) for s in v if s and s.strip()]
                       for k, v in zone_stores_in.items() if isinstance(v, list)}
    kdirs = [s.strip() for s in data.get("knowledge_dirs", []) if s and s.strip()]
    assets = (data.get("master_assets") or "").strip()
    out_dir = (data.get("default_output_dir") or "").strip()
    mojang = (data.get("mc_com_mojang_override") or "").strip() or None

    if not stores:
        raise ValueError("ต้องมี project store อย่างน้อย 1 รายการ")
    if not assets:
        raise ValueError("ต้องระบุ master_assets")
    if not out_dir:
        raise ValueError("ต้องระบุ default_output_dir")

    PROJECT_STORES = [Path(s) for s in stores]
    MASTER_ASSETS = Path(assets)
    DEFAULT_OUTPUT_DIR = Path(out_dir)
    KNOWLEDGE_DIRS = [Path(s) for s in kdirs]
    MC_COM_MOJANG_OVERRIDE = mojang

    SETTINGS_FILE.write_text(_json.dumps({
        "project_stores": stores,
        "master_assets": assets,
        "default_output_dir": out_dir,
        "knowledge_dirs": kdirs,
        "mc_com_mojang_override": mojang,
        "zone_stores": {k: [str(p) for p in v] for k, v in ZONE_STORES.items()},
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    return get_settings()


load_settings()
