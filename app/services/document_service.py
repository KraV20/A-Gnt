import shutil
from pathlib import Path
from typing import List, Optional
from app.database.connection import get_conn
from app.models.document import Document
from app.config import DOCS_DIR


def _ensure_dir(client_id: int = None, order_id: int = None) -> Path:
    target = DOCS_DIR
    if client_id:
        target = target / f"klient_{client_id}"
    if order_id:
        target = target / f"zlecenie_{order_id}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_all(client_id: int = None, order_id: int = None, category: str = None) -> List[Document]:
    conn = get_conn()
    sql = """SELECT d.*, c.name as client_name, o.number as order_number
             FROM documents d
             LEFT JOIN clients c ON d.client_id = c.id
             LEFT JOIN orders o ON d.order_id = o.id"""
    conditions, params = [], []
    if client_id:
        conditions.append("d.client_id = ?")
        params.append(client_id)
    if order_id:
        conditions.append("d.order_id = ?")
        params.append(order_id)
    if category:
        conditions.append("d.category = ?")
        params.append(category)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY d.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [Document.from_row(r) for r in rows]


def search(query: str) -> List[Document]:
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT d.*, c.name as client_name, o.number as order_number
           FROM documents d
           LEFT JOIN clients c ON d.client_id = c.id
           LEFT JOIN orders o ON d.order_id = o.id
           WHERE d.filename LIKE ? OR d.description LIKE ? OR d.tags LIKE ?
           ORDER BY d.created_at DESC""",
        (q, q, q),
    ).fetchall()
    return [Document.from_row(r) for r in rows]


def add_file(
    source_path: str,
    filename: str,
    category: str = "inne",
    client_id: int = None,
    order_id: int = None,
    description: str = "",
    tags: str = "",
) -> Document:
    target_dir = _ensure_dir(client_id, order_id)
    dest = target_dir / filename
    if Path(source_path) != dest:
        shutil.copy2(source_path, dest)

    size = dest.stat().st_size
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO documents (filename, filepath, category, client_id, order_id,
           description, tags, size_bytes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (filename, str(dest), category, client_id, order_id, description, tags, size),
    )
    conn.commit()
    return Document(
        id=cur.lastrowid, filename=filename, filepath=str(dest),
        category=category, client_id=client_id, order_id=order_id,
        description=description, tags=tags, size_bytes=size,
    )


def update(doc: Document) -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE documents SET category=?, client_id=?, order_id=?, description=?, tags=?
           WHERE id=?""",
        (doc.category, doc.client_id, doc.order_id, doc.description, doc.tags, doc.id),
    )
    conn.commit()


def delete(doc_id: int) -> None:
    conn = get_conn()
    row = conn.execute("SELECT filepath FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row:
        p = Path(row["filepath"])
        if p.exists():
            p.unlink()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()


def get_by_id(doc_id: int) -> Optional[Document]:
    conn = get_conn()
    row = conn.execute(
        """SELECT d.*, c.name as client_name, o.number as order_number
           FROM documents d
           LEFT JOIN clients c ON d.client_id = c.id
           LEFT JOIN orders o ON d.order_id = o.id
           WHERE d.id = ?""",
        (doc_id,),
    ).fetchone()
    return Document.from_row(row) if row else None
