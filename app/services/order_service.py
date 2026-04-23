from typing import List, Optional
from datetime import datetime
from app.database.connection import get_conn
from app.models.order import Order


def _next_number() -> str:
    conn = get_conn()
    year = datetime.now().year
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM orders WHERE number LIKE ?", (f"ZL/{year}/%",)
    ).fetchone()
    n = (row["cnt"] or 0) + 1
    return f"ZL/{year}/{n:04d}"


def get_all(status: str = None) -> List[Order]:
    conn = get_conn()
    sql = """SELECT o.*, c.name as client_name
             FROM orders o LEFT JOIN clients c ON o.client_id = c.id"""
    params = ()
    if status:
        sql += " WHERE o.status = ?"
        params = (status,)
    sql += " ORDER BY o.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [Order.from_row(r) for r in rows]


def get_by_id(order_id: int) -> Optional[Order]:
    conn = get_conn()
    row = conn.execute(
        """SELECT o.*, c.name as client_name
           FROM orders o LEFT JOIN clients c ON o.client_id = c.id
           WHERE o.id = ?""",
        (order_id,),
    ).fetchone()
    return Order.from_row(row) if row else None


def get_by_client(client_id: int) -> List[Order]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT o.*, c.name as client_name
           FROM orders o LEFT JOIN clients c ON o.client_id = c.id
           WHERE o.client_id = ? ORDER BY o.created_at DESC""",
        (client_id,),
    ).fetchall()
    return [Order.from_row(r) for r in rows]


def search(query: str) -> List[Order]:
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT o.*, c.name as client_name
           FROM orders o LEFT JOIN clients c ON o.client_id = c.id
           WHERE o.title LIKE ? OR o.number LIKE ? OR o.description LIKE ? OR c.name LIKE ?
           ORDER BY o.created_at DESC""",
        (q, q, q, q),
    ).fetchall()
    return [Order.from_row(r) for r in rows]


def create(order: Order) -> Order:
    conn = get_conn()
    if not order.number:
        order.number = _next_number()
    cur = conn.execute(
        """INSERT INTO orders (client_id, number, title, description, status, priority,
           order_date, deadline, value, currency, whokna_id, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (order.client_id, order.number, order.title, order.description,
         order.status, order.priority, order.order_date, order.deadline,
         order.value, order.currency, order.whokna_id, order.notes),
    )
    conn.commit()
    order.id = cur.lastrowid
    return order


def update(order: Order) -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE orders SET client_id=?, title=?, description=?, status=?, priority=?,
           order_date=?, deadline=?, completion_date=?, value=?, currency=?, whokna_id=?,
           notes=?, updated_at=datetime('now','localtime')
           WHERE id=?""",
        (order.client_id, order.title, order.description, order.status,
         order.priority, order.order_date, order.deadline, order.completion_date,
         order.value, order.currency, order.whokna_id, order.notes, order.id),
    )
    conn.commit()


def delete(order_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()


def get_stats() -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
    ).fetchall()
    return {r["status"]: r["cnt"] for r in rows}
