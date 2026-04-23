from dataclasses import dataclass
from typing import Optional

DOC_CATEGORIES = ["oferta", "umowa", "faktura", "projekt", "korespondencja", "inne"]


@dataclass
class Document:
    id: Optional[int] = None
    filename: str = ""
    filepath: str = ""
    category: str = "inne"
    client_id: Optional[int] = None
    order_id: Optional[int] = None
    description: str = ""
    tags: str = ""
    size_bytes: int = 0
    created_at: str = ""
    client_name: str = ""
    order_number: str = ""

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        return f"{self.size_bytes / (1024*1024):.1f} MB"

    @classmethod
    def from_row(cls, row) -> "Document":
        d = dict(row)
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: (d[k] if d.get(k) is not None else "") for k in known if k in d})
