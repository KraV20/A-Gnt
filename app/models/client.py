from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Client:
    id: Optional[int] = None
    name: str = ""
    company: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    postal_code: str = ""
    nip: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def display_name(self) -> str:
        if self.company:
            return f"{self.company} ({self.name})"
        return self.name

    @classmethod
    def from_row(cls, row) -> "Client":
        return cls(**{k: row[k] or "" for k in row.keys()})
