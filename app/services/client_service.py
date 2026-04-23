from typing import List, Optional
from app.database.connection import get_conn
from app.models.client import Client


def get_all() -> List[Client]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM clients ORDER BY name COLLATE NOCASE"
    ).fetchall()
    return [Client.from_row(r) for r in rows]


def get_by_id(client_id: int) -> Optional[Client]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    return Client.from_row(row) if row else None


def search(query: str) -> List[Client]:
    conn = get_conn()
    q = f"%{query}%"
    rows = conn.execute(
        """SELECT * FROM clients
           WHERE name LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR nip LIKE ?
           ORDER BY name COLLATE NOCASE""",
        (q, q, q, q, q),
    ).fetchall()
    return [Client.from_row(r) for r in rows]


def create(client: Client) -> Client:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO clients (name, company, email, phone, address, city, postal_code, nip, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (client.name, client.company, client.email, client.phone,
         client.address, client.city, client.postal_code, client.nip, client.notes),
    )
    conn.commit()
    client.id = cur.lastrowid
    return client


def update(client: Client) -> None:
    conn = get_conn()
    conn.execute(
        """UPDATE clients SET name=?, company=?, email=?, phone=?, address=?, city=?,
           postal_code=?, nip=?, notes=?, updated_at=datetime('now','localtime')
           WHERE id=?""",
        (client.name, client.company, client.email, client.phone,
         client.address, client.city, client.postal_code, client.nip,
         client.notes, client.id),
    )
    conn.commit()


def delete(client_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()


def find_by_email(email: str) -> Optional[Client]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM clients WHERE email = ? LIMIT 1", (email,)
    ).fetchone()
    return Client.from_row(row) if row else None
