from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class EmailAttachment:
    id: Optional[int] = None
    email_id: Optional[int] = None
    filename: str = ""
    filepath: str = ""
    mime_type: str = ""
    size_bytes: int = 0


@dataclass
class EmailMessage:
    id: Optional[int] = None
    uid: str = ""
    folder: str = "INBOX"
    subject: str = ""
    sender: str = ""
    recipients: str = ""
    date: str = ""
    body_text: str = ""
    body_html: str = ""
    is_read: bool = False
    is_flagged: bool = False
    client_id: Optional[int] = None
    order_id: Optional[int] = None
    created_at: str = ""
    attachments: List[EmailAttachment] = field(default_factory=list)
    client_name: str = ""

    @classmethod
    def from_row(cls, row) -> "EmailMessage":
        d = dict(row)
        known = {f for f in cls.__dataclass_fields__ if f != "attachments"}
        obj = cls(**{k: (d[k] if d.get(k) is not None else "") for k in known if k in d})
        obj.is_read = bool(d.get("is_read", 0))
        obj.is_flagged = bool(d.get("is_flagged", 0))
        return obj
