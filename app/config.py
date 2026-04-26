import os
import json
from pathlib import Path

APP_NAME = "A-Gnt"
APP_VERSION = "1.0.0"

# Dane aplikacji trzymamy obok pliku main.py (np. D:\A-Gnt\data\)
_APP_ROOT = Path(__file__).parent.parent
_BASE_DIR = _APP_ROOT / "data"
_BASE_DIR.mkdir(exist_ok=True)

DB_PATH = _BASE_DIR / "agnt.db"
DOCS_DIR = _BASE_DIR / "dokumenty"
DOCS_DIR.mkdir(exist_ok=True)
CONFIG_FILE = _BASE_DIR / "config.json"

_DEFAULTS = {
    "sync": {
        "enabled":            False,
        "server_url":         "",
        "api_key":            "",
        "device_id":          "",
        "auto_sync_minutes":  5,
    },
    "email": {
        "imap_host": "",
        "imap_port": 993,
        "imap_ssl": True,
        "smtp_host": "",
        "smtp_port": 587,
        "username": "",
        "password": "",
        "folder": "INBOX",
        "auto_fetch_minutes": 5,
    },
    "whokna": {
        "enabled": False,
        "dsn": "",
        "server": "",
        "database": "WHOkna",
        "username": "",
        "password": "",
        "driver": "ODBC Driver 17 for SQL Server",
    },
    "ui": {
        "theme": "light",
        "language": "pl",
    },
}


def load() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = _deep_merge(_DEFAULTS.copy(), data)
            return merged
        except Exception:
            pass
    return _DEFAULTS.copy()


def save(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
