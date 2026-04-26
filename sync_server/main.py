"""A-Gnt Sync Server – lightweight FastAPI sync backend.

Protocol
--------
All syncable records carry:
  sync_id   : UUID (client-generated, immutable)
  updated_at: ISO-8601 UTC timestamp
  is_deleted: 0/1  (soft-delete flag)

Conflict resolution: last-write-wins by updated_at.
FK references are carried as {col}_ref fields (sync_id of the related row).

Usage
-----
  uvicorn main:app --host 0.0.0.0 --port 8000

Environment variables
---------------------
  API_KEY   - shared secret (required, change from default!)
  DB_PATH   - path to SQLite file (default: /data/sync_server.db)
  LOG_LEVEL - uvicorn log level (default: info)
"""
import json
import os
import sqlite3
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Configuration ─────────────────────────────────────────────────────────────

API_KEY  = os.environ.get("API_KEY", "zmien-to-haslo-produkcyjne")
DB_PATH  = os.environ.get("DB_PATH", "/data/sync_server.db")
VERSION  = "1.0.0"

app = FastAPI(title="A-Gnt Sync Server", version=VERSION)


# ── Database ──────────────────────────────────────────────────────────────────

def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_records (
            table_name TEXT NOT NULL,
            sync_id    TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            is_deleted INTEGER DEFAULT 0,
            data       TEXT NOT NULL,
            PRIMARY KEY (table_name, sync_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sync_updated "
        "ON sync_records(updated_at)"
    )
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT    DEFAULT (datetime('now')),
            device_id  TEXT,
            action     TEXT,
            n_records  INTEGER
        )
    """)
    conn.commit()
    return conn


def _check_key(x_api_key: str) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Nieprawidłowy klucz API")


# ── Models ────────────────────────────────────────────────────────────────────

class PushPayload(BaseModel):
    device_id: str = "unknown"
    changes: Dict[str, List[Dict[str, Any]]]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


@app.get("/pull")
def pull(
    since: str = Query("1970-01-01T00:00:00", description="ISO timestamp of last sync"),
    x_api_key: str = Header(...),
):
    _check_key(x_api_key)
    conn = _db()
    rows = conn.execute(
        "SELECT table_name, sync_id, updated_at, is_deleted, data "
        "FROM sync_records WHERE updated_at > ? ORDER BY updated_at",
        (since,),
    ).fetchall()

    changes: Dict[str, List[dict]] = {}
    for row in rows:
        table = row["table_name"]
        record = json.loads(row["data"])
        record["sync_id"]    = row["sync_id"]
        record["updated_at"] = row["updated_at"]
        record["is_deleted"] = row["is_deleted"]
        changes.setdefault(table, []).append(record)

    return {"changes": changes, "count": sum(len(v) for v in changes.values())}


@app.post("/push")
def push(payload: PushPayload, x_api_key: str = Header(...)):
    _check_key(x_api_key)
    conn = _db()
    accepted = 0

    for table, records in payload.changes.items():
        for record in records:
            sync_id    = record.get("sync_id")
            updated_at = record.get("updated_at", "")
            is_deleted = int(record.get("is_deleted", 0))
            if not sync_id or not updated_at:
                continue

            existing = conn.execute(
                "SELECT updated_at FROM sync_records "
                "WHERE table_name=? AND sync_id=?",
                (table, sync_id),
            ).fetchone()

            if existing and existing["updated_at"] >= updated_at:
                continue  # server version is same or newer

            conn.execute(
                """INSERT INTO sync_records
                       (table_name, sync_id, updated_at, is_deleted, data)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(table_name, sync_id) DO UPDATE SET
                       updated_at = excluded.updated_at,
                       is_deleted = excluded.is_deleted,
                       data       = excluded.data""",
                (table, sync_id, updated_at, is_deleted, json.dumps(record)),
            )
            accepted += 1

    conn.execute(
        "INSERT INTO server_log(device_id, action, n_records) VALUES(?,?,?)",
        (payload.device_id, "push", accepted),
    )
    conn.commit()
    return {"accepted": accepted}


@app.get("/stats")
def stats(x_api_key: str = Header(...)):
    """Admin endpoint – record counts per table on server."""
    _check_key(x_api_key)
    conn = _db()
    rows = conn.execute(
        "SELECT table_name, COUNT(*) AS cnt, "
        "SUM(is_deleted) AS deleted "
        "FROM sync_records GROUP BY table_name"
    ).fetchall()
    return {r["table_name"]: {"total": r["cnt"], "deleted": r["deleted"]} for r in rows}
