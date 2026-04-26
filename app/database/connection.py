import sqlite3
import threading
from pathlib import Path
from app.config import DB_PATH

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA foreign_keys = ON")
        _local.conn.execute("PRAGMA journal_mode = WAL")
    return _local.conn


def init_db() -> None:
    conn = get_conn()
    schema = Path(__file__).parent / "schema.sql"
    with open(schema, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    _migrate_sync()


def _migrate_sync() -> None:
    """Add sync columns to existing tables (idempotent)."""
    conn = get_conn()
    migrations = [
        ("clients",         "sync_id",    "TEXT"),
        ("clients",         "is_deleted", "INTEGER DEFAULT 0"),
        ("orders",          "sync_id",    "TEXT"),
        ("orders",          "is_deleted", "INTEGER DEFAULT 0"),
        ("calendar_events", "sync_id",    "TEXT"),
        ("calendar_events", "is_deleted", "INTEGER DEFAULT 0"),
        ("order_checklist", "sync_id",    "TEXT"),
        ("order_checklist", "updated_at", "TEXT"),
        ("order_checklist", "is_deleted", "INTEGER DEFAULT 0"),
        ("documents",       "sync_id",    "TEXT"),
        ("documents",       "updated_at", "TEXT DEFAULT (datetime('now','localtime'))"),
        ("documents",       "is_deleted", "INTEGER DEFAULT 0"),
    ]
    for table, col, dtype in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
        except Exception:
            pass  # column already exists

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()

