"""Application configuration.

Load order (later wins):
1. built-in defaults
2. config.yaml next to the app (optional)
3. ~/.config/j315scan/settings.json (user preferences)
4. ./settings.json (legacy / local override)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
USER_SETTINGS = Path.home() / ".config" / "j315scan" / "settings.json"
LOCAL_SETTINGS = APP_DIR / "settings.json"
LOCAL_YAML = APP_DIR / "config.yaml"

DEFAULTS: dict[str, Any] = {
    "host": "192.168.0.80",
    "port": 54921,
    "mode": "color",
    "dpi": 200,
    "brightness": 50,
    "contrast": 50,
    "split": True,
    "outdir": str(Path.home() / "Pictures"),
    "filename_prefix": "scan",
    "language": "auto",
    "jpeg_quality": 92,
    "idle_timeout": 25.0,
    "max_seconds": 180.0,
}


def default_pictures() -> Path:
    home = Path.home()
    for candidate in (home / "Pictures", home / "My Pictures"):
        if candidate.exists():
            return candidate
    return home / "Pictures"


DEFAULTS["outdir"] = str(default_pictures())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip().strip("\"'")
        if not key:
            continue
        low = val.lower()
        if low in ("true", "yes"):
            out[key] = True
        elif low in ("false", "no"):
            out[key] = False
        else:
            try:
                out[key] = int(val)
            except ValueError:
                try:
                    out[key] = float(val)
                except ValueError:
                    out[key] = val
    return out


def load_config() -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    cfg.update(_read_yaml(LOCAL_YAML))
    if USER_SETTINGS.exists():
        cfg.update(_read_json(USER_SETTINGS))
    if LOCAL_SETTINGS.exists():
        cfg.update(_read_json(LOCAL_SETTINGS))
    cfg["outdir"] = str(Path(str(cfg.get("outdir") or DEFAULTS["outdir"])).expanduser())
    return cfg


def save_user_settings(data: dict[str, Any], path: Path | None = None) -> None:
    dest = path or LOCAL_SETTINGS
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
