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
