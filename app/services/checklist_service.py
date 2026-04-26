"""Order workflow checklist – step definitions and progress tracking."""
from typing import List, Tuple, Dict
from datetime import datetime
from app.database.connection import get_conn

# Step definitions: status → [(step_key, label)]
WORKFLOW: Dict[str, List[Tuple[str, str]]] = {
    "nowe": [
        ("kontakt_klient",   "Skontaktuj się z klientem"),
        ("zbierz_wymiary",   "Zbierz wymiary i wymagania techniczne"),
        ("przygotuj_wycene", "Przygotuj wycenę w kalkulatorze"),
        ("wyslij_oferte",    "Wyślij ofertę do klienta"),
    ],
    "w trakcie": [
        ("potwierdzenie",    "Odbierz pisemne potwierdzenie zamówienia"),
        ("zaliczka",         "Pobierz zaliczkę (jeśli wymagana)"),
        ("zamow_produkcje",  "Złóż zamówienie u producenta / dostawcy"),
        ("termin_dostawy",   "Potwierdź termin dostawy towaru"),
        ("zaplanuj_montaz",  "Zaplanuj montaż w Kalendarzu"),
        ("wykonaj_montaz",   "Wykonaj montaż / dostawę"),
        ("protokol",         "Podpisz protokół odbioru z klientem"),
    ],
    "wstrzymane": [
        ("przyczyna",        "Zapisz przyczynę wstrzymania w notatkach"),
        ("info_klient",      "Poinformuj klienta o wstrzymaniu"),
        ("termin_wznowienia","Ustal termin wznowienia prac"),
    ],
    "zakończone": [
        ("faktura",          "Wystaw fakturę końcową"),
        ("platnosc",         "Odbierz / zaksięguj płatność"),
        ("dokumenty_arch",   "Archiwizuj dokumenty w panelu Dokumenty"),
        ("opinia",           "Poproś klienta o opinię / referencje"),
    ],
    "anulowane": [
        ("powod_anulacji",   "Zapisz powód anulacji w notatkach"),
        ("zwrot",            "Zrealizuj ewentualny zwrot zaliczki"),
    ],
}


def _ensure_steps(order_id: int, status: str) -> None:
    """Insert missing steps for the given status (idempotent)."""
    steps = WORKFLOW.get(status, [])
    conn = get_conn()
    for key, _ in steps:
        conn.execute(
            "INSERT OR IGNORE INTO order_checklist (order_id, step_key) VALUES (?, ?)",
            (order_id, key),
        )
    conn.commit()


def get_progress(order_id: int, status: str) -> List[dict]:
    """Return list of step dicts for the current status with done state."""
    _ensure_steps(order_id, status)
    steps = WORKFLOW.get(status, [])
    if not steps:
        return []

    keys = [k for k, _ in steps]
    conn = get_conn()
    rows = conn.execute(
        f"SELECT step_key, is_done, done_at FROM order_checklist "
        f"WHERE order_id = ? AND step_key IN ({','.join('?' * len(keys))})",
        (order_id, *keys),
    ).fetchall()
    done_map = {r["step_key"]: (bool(r["is_done"]), r["done_at"]) for r in rows}

    result = []
    for key, label in steps:
        is_done, done_at = done_map.get(key, (False, None))
        result.append({
            "key": key,
            "label": label,
            "is_done": is_done,
            "done_at": done_at or "",
        })
    return result


def toggle_step(order_id: int, step_key: str, is_done: bool) -> None:
    done_at = datetime.now().strftime("%Y-%m-%d %H:%M") if is_done else None
    get_conn().execute(
        "INSERT INTO order_checklist (order_id, step_key, is_done, done_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(order_id, step_key) DO UPDATE SET is_done=excluded.is_done, done_at=excluded.done_at",
        (order_id, step_key, int(is_done), done_at),
    )
    get_conn().commit()


def completion_pct(order_id: int, status: str) -> int:
    """Returns 0-100 completion % for the current status steps."""
    steps = get_progress(order_id, status)
    if not steps:
        return 100
    done = sum(1 for s in steps if s["is_done"])
    return int(done / len(steps) * 100)


def incomplete_steps(order_id: int, status: str) -> List[str]:
    """Return labels of incomplete steps for the given status."""
    return [s["label"] for s in get_progress(order_id, status) if not s["is_done"]]
