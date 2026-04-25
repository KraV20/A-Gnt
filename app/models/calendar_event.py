from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date

EVENT_TYPES = ["spotkanie", "montaż", "pomiar", "rozmowa", "zadanie", "inne"]
EVENT_COLORS = {
    "spotkanie": "#2563eb",
    "montaż":    "#16a34a",
    "pomiar":    "#f59e0b",
    "rozmowa":   "#8b5cf6",
    "zadanie":   "#ef4444",
    "inne":      "#6b7280",
}
REMINDER_OPTIONS = [
    ("Bez przypomnienia", 0),
    ("5 min przed", 5),
    ("15 min przed", 15),
    ("30 min przed", 30),
    ("1 godz przed", 60),
    ("1 dzień przed", 1440),
]


@dataclass
class CalendarEvent:
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    event_date: str = ""           # YYYY-MM-DD
    event_time: Optional[str] = None  # HH:MM or None for all-day
    duration_min: int = 60
    event_type: str = "spotkanie"
    location: str = ""
    client_id: Optional[int] = None
    order_id: Optional[int] = None
    is_done: bool = False
    reminder_min: int = 0
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_all_day(self) -> bool:
        return not self.event_time

    @property
    def datetime_display(self) -> str:
        if self.is_all_day:
            return f"{self.event_date} (cały dzień)"
        return f"{self.event_date} {self.event_time}"

    @property
    def color(self) -> str:
        return EVENT_COLORS.get(self.event_type, "#6b7280")

    @classmethod
    def from_row(cls, row) -> "CalendarEvent":
        d = dict(row)
        return cls(
            id=d.get("id"),
            title=d.get("title", ""),
            description=d.get("description") or "",
            event_date=d.get("event_date", ""),
            event_time=d.get("event_time"),
            duration_min=int(d.get("duration_min") or 60),
            event_type=d.get("event_type") or "spotkanie",
            location=d.get("location") or "",
            client_id=d.get("client_id"),
            order_id=d.get("order_id"),
            is_done=bool(d.get("is_done") or 0),
            reminder_min=int(d.get("reminder_min") or 0),
            created_at=d.get("created_at") or "",
            updated_at=d.get("updated_at") or "",
        )
