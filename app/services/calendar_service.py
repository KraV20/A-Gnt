"""Calendar service – CRUD for calendar_events table."""
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta

from app.database.connection import get_conn
from app.models.calendar_event import CalendarEvent


def list_events(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    client_id: Optional[int] = None,
    order_id: Optional[int] = None,
    include_done: bool = True,
) -> List[CalendarEvent]:
    sql = "SELECT * FROM calendar_events WHERE 1=1"
    params: list = []
    if date_from:
        sql += " AND event_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND event_date <= ?"
        params.append(date_to)
    if client_id is not None:
        sql += " AND client_id = ?"
        params.append(client_id)
    if order_id is not None:
        sql += " AND order_id = ?"
        params.append(order_id)
    if not include_done:
        sql += " AND is_done = 0"
    sql += " ORDER BY event_date ASC, event_time ASC NULLS FIRST"
    rows = get_conn().execute(sql, params).fetchall()
    return [CalendarEvent.from_row(r) for r in rows]


def get_event(event_id: int) -> Optional[CalendarEvent]:
    row = get_conn().execute(
        "SELECT * FROM calendar_events WHERE id = ?", (event_id,)
    ).fetchone()
    return CalendarEvent.from_row(row) if row else None


def get_events_for_date(d: str) -> List[CalendarEvent]:
    return list_events(date_from=d, date_to=d)


def get_events_for_month(year: int, month: int) -> List[CalendarEvent]:
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return list_events(date_from=first.isoformat(), date_to=last.isoformat())


def get_dates_with_events(year: int, month: int) -> Dict[str, int]:
    """Returns {YYYY-MM-DD: count} for the given month."""
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    rows = get_conn().execute(
        "SELECT event_date, COUNT(*) AS cnt FROM calendar_events "
        "WHERE event_date >= ? AND event_date <= ? "
        "GROUP BY event_date",
        (first.isoformat(), last.isoformat()),
    ).fetchall()
    return {r["event_date"]: int(r["cnt"]) for r in rows}


def get_upcoming(days: int = 7, limit: int = 50) -> List[CalendarEvent]:
    today = date.today()
    end = today + timedelta(days=days)
    sql = (
        "SELECT * FROM calendar_events "
        "WHERE event_date >= ? AND event_date <= ? AND is_done = 0 "
        "ORDER BY event_date ASC, event_time ASC NULLS FIRST LIMIT ?"
    )
    rows = get_conn().execute(sql, (today.isoformat(), end.isoformat(), limit)).fetchall()
    return [CalendarEvent.from_row(r) for r in rows]


def create_event(ev: CalendarEvent) -> int:
    sql = (
        "INSERT INTO calendar_events "
        "(title, description, event_date, event_time, duration_min, event_type, "
        " location, client_id, order_id, is_done, reminder_min) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    cur = get_conn().execute(sql, (
        ev.title, ev.description, ev.event_date, ev.event_time,
        ev.duration_min, ev.event_type, ev.location,
        ev.client_id, ev.order_id, int(ev.is_done), ev.reminder_min,
    ))
    get_conn().commit()
    return cur.lastrowid


def update_event(ev: CalendarEvent) -> None:
    if ev.id is None:
        return
    sql = (
        "UPDATE calendar_events SET "
        "title=?, description=?, event_date=?, event_time=?, duration_min=?, "
        "event_type=?, location=?, client_id=?, order_id=?, is_done=?, "
        "reminder_min=?, updated_at=datetime('now','localtime') "
        "WHERE id=?"
    )
    get_conn().execute(sql, (
        ev.title, ev.description, ev.event_date, ev.event_time,
        ev.duration_min, ev.event_type, ev.location,
        ev.client_id, ev.order_id, int(ev.is_done), ev.reminder_min,
        ev.id,
    ))
    get_conn().commit()


def delete_event(event_id: int) -> None:
    get_conn().execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
    get_conn().commit()


def toggle_done(event_id: int) -> None:
    get_conn().execute(
        "UPDATE calendar_events SET is_done = 1 - is_done, "
        "updated_at = datetime('now','localtime') WHERE id = ?",
        (event_id,),
    )
    get_conn().commit()


def get_stats() -> dict:
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()
    rows = get_conn().execute(
        "SELECT "
        "  SUM(CASE WHEN event_date = ? AND is_done = 0 THEN 1 ELSE 0 END) AS today, "
        "  SUM(CASE WHEN event_date > ? AND event_date <= ? AND is_done = 0 THEN 1 ELSE 0 END) AS week, "
        "  SUM(CASE WHEN event_date < ? AND is_done = 0 THEN 1 ELSE 0 END) AS overdue "
        "FROM calendar_events",
        (today, today, week_end, today),
    ).fetchone()
    return {
        "today":   int(rows["today"] or 0),
        "week":    int(rows["week"] or 0),
        "overdue": int(rows["overdue"] or 0),
    }
