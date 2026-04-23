"""
WHOkna integration via ODBC.

WHOkna is a Polish window/door manufacturing management software.
This service reads orders and clients from the WHOkna SQL Server database
and can synchronize them into the local A-Gnt database.
"""
from typing import List, Dict, Optional

try:
    import pyodbc
    _PYODBC_AVAILABLE = True
except ImportError:
    _PYODBC_AVAILABLE = False


def is_available() -> bool:
    return _PYODBC_AVAILABLE


def _build_conn_string(cfg: dict) -> str:
    if cfg.get("dsn"):
        cs = f"DSN={cfg['dsn']}"
    else:
        cs = (
            f"DRIVER={{{cfg.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg.get('database', 'WHOkna')};"
        )
    if cfg.get("username"):
        cs += f";UID={cfg['username']};PWD={cfg.get('password', '')}"
    else:
        cs += ";Trusted_Connection=yes"
    return cs


def test_connection(cfg: dict) -> tuple[bool, str]:
    if not _PYODBC_AVAILABLE:
        return False, "pyodbc nie jest zainstalowane"
    try:
        conn_str = _build_conn_string(cfg)
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return True, "Połączono pomyślnie"
    except Exception as e:
        return False, str(e)


def get_orders(cfg: dict, limit: int = 100) -> List[Dict]:
    """Fetch orders from WHOkna database."""
    if not _PYODBC_AVAILABLE:
        return []
    try:
        conn_str = _build_conn_string(cfg)
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP {limit}
                o.ID            as whokna_id,
                o.Numer         as number,
                o.Nazwa         as title,
                o.DataZlecenia  as order_date,
                o.DataRealizacji as deadline,
                o.Status        as status,
                o.Wartosc       as value,
                k.Nazwa         as client_name,
                k.Email         as client_email,
                k.Telefon       as client_phone
            FROM Zlecenia o
            LEFT JOIN Klienci k ON o.KlientID = k.ID
            ORDER BY o.DataZlecenia DESC
        """)
        columns = [col[0] for col in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(columns, row)))
        conn.close()
        return rows
    except Exception:
        return []


def get_clients(cfg: dict) -> List[Dict]:
    """Fetch clients from WHOkna database."""
    if not _PYODBC_AVAILABLE:
        return []
    try:
        conn_str = _build_conn_string(cfg)
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                k.ID        as whokna_id,
                k.Nazwa     as name,
                k.Firma     as company,
                k.Email     as email,
                k.Telefon   as phone,
                k.Adres     as address,
                k.Miasto    as city,
                k.KodPocztowy as postal_code,
                k.NIP       as nip
            FROM Klienci k
            ORDER BY k.Nazwa
        """)
        columns = [col[0] for col in cursor.description]
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(columns, row)))
        conn.close()
        return rows
    except Exception:
        return []


def sync_to_local(cfg: dict) -> tuple[int, int]:
    """Sync WHOkna orders and clients to local database. Returns (clients_added, orders_added)."""
    import app.services.client_service as client_svc
    import app.services.order_service as order_svc
    from app.models.client import Client
    from app.models.order import Order
    from app.database.connection import get_conn

    clients_added = 0
    orders_added = 0

    wh_clients = get_clients(cfg)
    whokna_id_to_local: Dict[str, int] = {}

    conn = get_conn()
    for wc in wh_clients:
        existing = conn.execute(
            "SELECT id FROM clients WHERE email = ?", (wc.get("email", ""),)
        ).fetchone()
        if existing:
            whokna_id_to_local[str(wc["whokna_id"])] = existing["id"]
            continue
        c = Client(
            name=wc.get("name", ""),
            company=wc.get("company", ""),
            email=wc.get("email", ""),
            phone=wc.get("phone", ""),
            address=wc.get("address", ""),
            city=wc.get("city", ""),
            postal_code=wc.get("postal_code", ""),
            nip=wc.get("nip", ""),
        )
        c = client_svc.create(c)
        whokna_id_to_local[str(wc["whokna_id"])] = c.id
        clients_added += 1

    wh_orders = get_orders(cfg, limit=500)
    for wo in wh_orders:
        existing = conn.execute(
            "SELECT id FROM orders WHERE whokna_id = ?", (str(wo.get("whokna_id", "")),)
        ).fetchone()
        if existing:
            continue
        client_id = whokna_id_to_local.get(str(wo.get("whokna_id", "")))
        o = Order(
            client_id=client_id,
            number=wo.get("number", ""),
            title=wo.get("title", ""),
            status=wo.get("status", "nowe"),
            order_date=str(wo.get("order_date", "")),
            deadline=str(wo.get("deadline", "")),
            value=wo.get("value"),
            whokna_id=str(wo.get("whokna_id", "")),
        )
        order_svc.create(o)
        orders_added += 1

    return clients_added, orders_added
