from dataclasses import dataclass
from typing import Optional

ORDER_STATUSES = ["nowe", "w trakcie", "wstrzymane", "zakończone", "anulowane"]
ORDER_PRIORITIES = ["niski", "normalny", "wysoki", "pilny"]


@dataclass
class Order:
    id: Optional[int] = None
    client_id: Optional[int] = None
    number: str = ""
    title: str = ""
    description: str = ""
    status: str = "nowe"
    priority: str = "normalny"
    order_date: str = ""
    deadline: str = ""
    completion_date: str = ""
    value: Optional[float] = None
    currency: str = "PLN"
    whokna_id: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    client_name: str = ""

    @property
    def value_display(self) -> str:
        try:
            v = float(self.value) if self.value not in (None, "") else None
            if v is not None:
                return f"{v:,.2f} {self.currency}"
        except (TypeError, ValueError):
            pass
        return ""

    @classmethod
    def from_row(cls, row) -> "Order":
        d = dict(row)
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: (d[k] if d[k] is not None else "") for k in known if k in d})
