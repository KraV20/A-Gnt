"""A-Gnt client-side sync service.

Bidirectional sync with the A-Gnt Sync Server via HTTP REST.

Sync protocol
-------------
1. ensure_sync_ids() – give UUIDs to all rows that lack one
2. pull(since)       – download server changes and apply to local DB
3. push(since)       – collect local changes and upload to server
4. update last_sync timestamp in sync_state table

Conflict resolution: last-write-wins by updated_at.

FK references
-------------
When pushing, FK columns (client_id, order_id) are supplemented with
corresponding *_ref fields containing the sync_id of the related row.
When pulling, *_ref fields are resolved to local IDs.
"""
import json
import sqlite3
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.database.connection import get_conn

# Tables that participate in sync (order matters – parents before children)
SYNC_TABLES = [
    "clients",
    "orders",
    "calendar_events",
    "order_checklist",
    "documents",
]

# FK columns that need sync_id cross-referencing: col → parent table
_FK_REFS: Dict[str, Dict[str, str]] = {
    "orders":          {"client_id": "clients"},
    "calendar_events": {"client_id": "clients", "order_id": "orders"},
    "order_checklist": {"order_id": "orders"},
    "documents":       {"client_id": "clients", "order_id": "orders"},
}

# Columns to exclude when serializing (local-only fields)
_EXCLUDE = {"id"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _get_last_sync() -> str:
    row = get_conn().execute(
        "SELECT value FROM sync_state WHERE key='last_sync'"
    ).fetchone()
    return row["value"] if row else "1970-01-01T00:00:00"


def _set_last_sync(ts: str) -> None:
    get_conn().execute(
        "INSERT INTO sync_state(key,value) VALUES('last_sync',?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (ts,),
    )
    get_conn().commit()


def get_device_id(cfg: dict) -> str:
    dev_id = cfg.get("sync", {}).get("device_id", "")
    if not dev_id:
        dev_id = str(uuid.uuid4())
        cfg.setdefault("sync", {})["device_id"] = dev_id
        import app.config as cfg_module
        cfg_module.save(cfg)
    return dev_id


# ── Sync-id management ────────────────────────────────────────────────────────

def ensure_sync_ids() -> None:
    """Assign UUIDs to all rows that have sync_id IS NULL."""
    conn = get_conn()
    for table in SYNC_TABLES:
        try:
            rows = conn.execute(
                f"SELECT id FROM {table} WHERE sync_id IS NULL"
            ).fetchall()
            for r in rows:
                conn.execute(
                    f"UPDATE {table} SET sync_id=? WHERE id=?",
                    (str(uuid.uuid4()), r[0]),
                )
        except Exception:
            pass
    conn.commit()


# ── Serialization ─────────────────────────────────────────────────────────────

def _serialize(table: str, row: sqlite3.Row) -> dict:  # type: ignore[name-defined]
    data = {k: row[k] for k in row.keys() if k not in _EXCLUDE}
    conn = get_conn()
    for fk_col, ref_table in _FK_REFS.get(table, {}).items():
        local_id = data.get(fk_col)
        if local_id:
            ref = conn.execute(
                f"SELECT sync_id FROM {ref_table} WHERE id=?", (local_id,)
            ).fetchone()
            if ref:
                data[f"{fk_col}_ref"] = ref["sync_id"]
    # Normalise updated_at – use created_at as fallback
    if not data.get("updated_at"):
        data["updated_at"] = data.get("created_at") or _now_utc()
    return data


def _resolve_fks(table: str, data: dict) -> dict:
    """Replace *_ref fields with local integer IDs."""
    conn = get_conn()
    for fk_col, ref_table in _FK_REFS.get(table, {}).items():
        ref_key = f"{fk_col}_ref"
        ref_sync_id = data.pop(ref_key, None)
        if ref_sync_id:
            ref = conn.execute(
                f"SELECT id FROM {ref_table} WHERE sync_id=?", (ref_sync_id,)
            ).fetchone()
            data[fk_col] = ref["id"] if ref else None
    return data


# ── Apply incoming record ─────────────────────────────────────────────────────

def _apply(table: str, data: dict) -> None:
    data = _resolve_fks(table, dict(data))
    sync_id = data.get("sync_id")
    if not sync_id:
        return

    conn = get_conn()
    existing = conn.execute(
        f"SELECT id, updated_at FROM {table} WHERE sync_id=?", (sync_id,)
    ).fetchone()

    remote_ts = data.get("updated_at", "")

    if data.get("is_deleted") == 1:
        if existing:
            conn.execute(f"DELETE FROM {table} WHERE id=?", (existing["id"],))
            conn.commit()
        return

    data.pop("id", None)

    if existing:
        if remote_ts <= (existing["updated_at"] or ""):
            return  # local is same or newer
        local_id = existing["id"]
        pairs = [(k, v) for k, v in data.items() if k != "sync_id"]
        set_clause = ", ".join(f"{k}=?" for k, _ in pairs)
        vals = [v for _, v in pairs] + [local_id]
        conn.execute(f"UPDATE {table} SET {set_clause} WHERE id=?", vals)
    else:
        cols = ", ".join(data.keys())
        phs  = ", ".join("?" * len(data))
        conn.execute(
            f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({phs})",
            list(data.values()),
        )
    conn.commit()


# ── Local changes collector ───────────────────────────────────────────────────

def _collect_changes(since: str) -> Dict[str, List[dict]]:
    ensure_sync_ids()
    conn = get_conn()
    result: Dict[str, List[dict]] = {}
    for table in SYNC_TABLES:
        try:
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE updated_at > ?", (since,)
            ).fetchall()
            result[table] = [_serialize(table, r) for r in rows]
        except Exception:
            result[table] = []
    return result


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _http_get(url: str, api_key: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"X-API-Key": api_key})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _http_post(url: str, api_key: str, body: dict, timeout: int = 60) -> dict:
    data = json.dumps(body, default=str).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


# ── Public API ────────────────────────────────────────────────────────────────

def test_connection(server_url: str, api_key: str) -> Tuple[bool, str]:
    try:
        result = _http_get(f"{server_url.rstrip('/')}/health", api_key, timeout=10)
        return True, f"Połączono z serwerem sync (v{result.get('version','?')})"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Błędny klucz API"
        return False, f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        return False, f"Brak połączenia: {e}"


def pull(server_url: str, api_key: str, since: str) -> Tuple[int, str]:
    """Download and apply server changes. Returns (n_applied, error)."""
    try:
        url = f"{server_url.rstrip('/')}/pull?since={since}"
        payload = _http_get(url, api_key)
    except Exception as e:
        return 0, str(e)

    applied = 0
    for table in SYNC_TABLES:
        for record in payload.get("changes", {}).get(table, []):
            try:
                _apply(table, record)
                applied += 1
            except Exception:
                pass
    return applied, ""


def push(server_url: str, api_key: str, since: str, device_id: str) -> Tuple[int, str]:
    """Collect local changes and upload. Returns (n_pushed, error)."""
    changes = _collect_changes(since)
    total = sum(len(v) for v in changes.values())
    if total == 0:
        return 0, ""
    try:
        result = _http_post(
            f"{server_url.rstrip('/')}/push", api_key,
            {"device_id": device_id, "changes": changes},
        )
        return result.get("accepted", 0), ""
    except Exception as e:
        return 0, str(e)


def sync(cfg: dict) -> Tuple[int, int, str]:
    """Full bidirectional sync. Returns (pulled, pushed, error)."""
    sync_cfg = cfg.get("sync", {})
    if not sync_cfg.get("enabled"):
        return 0, 0, "disabled"

    server_url = sync_cfg.get("server_url", "").strip()
    api_key    = sync_cfg.get("api_key", "").strip()
    device_id  = get_device_id(cfg)

    if not server_url or not api_key:
        return 0, 0, "Brak adresu serwera lub klucza API"

    last_sync = _get_last_sync()

    pulled, err = pull(server_url, api_key, last_sync)
    if err:
        return 0, 0, f"Pull: {err}"

    now = _now_utc()
    pushed, err = push(server_url, api_key, last_sync, device_id)
    if err:
        return pulled, 0, f"Push: {err}"

    _set_last_sync(now)
    return pulled, pushed, ""


