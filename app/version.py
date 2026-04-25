"""Application version & build counter.

VERSION    – human-readable semver (manually bumped on releases)
EDITION    – short tagline
build counter – auto-incremented on each application start, persisted in
                data/version_info.json
"""
import json
from datetime import datetime
from pathlib import Path

from app.config import _BASE_DIR

VERSION = "1.1.0"
EDITION = "WHOkna Edition"

_VERSION_FILE = _BASE_DIR / "version_info.json"


def _load() -> dict:
    if _VERSION_FILE.exists():
        try:
            with open(_VERSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "version": VERSION,
        "build": 0,
        "first_run": "",
        "last_run": "",
        "version_history": [],
    }


def _save(data: dict) -> None:
    with open(_VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def bump_build() -> dict:
    """Called once on app startup. Returns updated info dict."""
    info = _load()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    info["build"] = int(info.get("build", 0)) + 1
    if not info.get("first_run"):
        info["first_run"] = now
    info["last_run"] = now

    last_logged = ""
    history = info.get("version_history") or []
    if history:
        last_logged = history[-1].get("version", "")
    if VERSION != last_logged:
        history.append({
            "version": VERSION,
            "build": info["build"],
            "date": now,
        })
        info["version_history"] = history

    info["version"] = VERSION
    _save(info)
    return info


def get_info() -> dict:
    return _load()


def display_string() -> str:
    info = _load()
    build = info.get("build", 0)
    return f"v{VERSION}  •  build {build}  •  {EDITION}"
