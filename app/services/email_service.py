import imaplib
import email
import email.header
import email.utils
import re
import hashlib
import base64
from typing import List, Optional, Tuple
from datetime import datetime
from app.database.connection import get_conn
from app.models.email_message import EmailMessage, EmailAttachment
from app.config import DOCS_DIR
import app.services.client_service as client_svc


def _decode_header(value: str) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    result = []
    for part, enc in parts:
        if isinstance(part, bytes):
            result.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _get_body(msg) -> Tuple[str, str]:
    text, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            charset = part.get_content_charset() or "utf-8"
            if ct == "text/plain" and not text:
                text = part.get_payload(decode=True).decode(charset, errors="replace")
            elif ct == "text/html" and not html:
                html = part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            if msg.get_content_type() == "text/html":
                html = payload.decode(charset, errors="replace")
            else:
                text = payload.decode(charset, errors="replace")
    return text, html


def _get_attachments(msg, email_id: int) -> List[EmailAttachment]:
    attachments = []
    att_dir = DOCS_DIR / "email_attachments"
    att_dir.mkdir(exist_ok=True)
    for part in msg.walk():
        disp = str(part.get("Content-Disposition", ""))
        if "attachment" not in disp:
            continue
        filename = _decode_header(part.get_filename() or "plik")
        safe_name = re.sub(r"[^\w\.\-]", "_", filename)
        data = part.get_payload(decode=True)
        if not data:
            continue
        filepath = att_dir / f"{email_id}_{safe_name}"
        filepath.write_bytes(data)
        attachments.append(EmailAttachment(
            email_id=email_id,
            filename=filename,
            filepath=str(filepath),
            mime_type=part.get_content_type(),
            size_bytes=len(data),
        ))
    return attachments


def _imap_login(imap, username: str, password: str) -> None:
    """Login to IMAP, falling back to AUTHENTICATE PLAIN if LOGIN is rejected.

    Some servers (or some passwords with special chars) require AUTHENTICATE
    PLAIN instead of plain-text LOGIN. We try LOGIN first (most compatible)
    and on failure fall back.
    """
    try:
        imap.login(username, password)
        return
    except imaplib.IMAP4.error as exc:
        first_err = str(exc)

    # Fallback: AUTHENTICATE PLAIN  (\0user\0pass base64-encoded)
    try:
        auth_str = f"\0{username}\0{password}"
        imap.authenticate("PLAIN", lambda _: auth_str.encode("utf-8"))
        return
    except imaplib.IMAP4.error as exc2:
        raise imaplib.IMAP4.error(
            f"LOGIN: {first_err} | AUTHENTICATE PLAIN: {exc2}"
        )


def test_connection(cfg: dict) -> Tuple[bool, str]:
    """Test IMAP connection. Returns (ok, message)."""
    try:
        if cfg.get("imap_ssl", True):
            imap = imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993))
        else:
            imap = imaplib.IMAP4(cfg["imap_host"], cfg.get("imap_port", 143))
        _imap_login(imap, cfg["username"], cfg["password"])
        imap.select(cfg.get("folder", "INBOX"))
        imap.logout()
        return True, "Połączenie i logowanie OK"
    except imaplib.IMAP4.error as e:
        return False, f"Błąd IMAP: {e}"
    except Exception as e:
        return False, f"Błąd połączenia: {e}"


def fetch_emails(cfg: dict, limit: int = 50) -> Tuple[int, int]:
    """Connect via IMAP and fetch new emails. Returns (new_count, error_count).

    On error, the message is stored in module-level _LAST_ERROR for UI display.
    """
    global _LAST_ERROR
    _LAST_ERROR = ""
    new_count = 0
    try:
        if cfg.get("imap_ssl", True):
            imap = imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993))
        else:
            imap = imaplib.IMAP4(cfg["imap_host"], cfg.get("imap_port", 143))
        _imap_login(imap, cfg["username"], cfg["password"])
        folder = cfg.get("folder", "INBOX")
        imap.select(folder)

        _, data = imap.search(None, "ALL")
        uids = data[0].split()
        uids = uids[-limit:]

        conn = get_conn()
        for uid_bytes in uids:
            uid = f"{folder}:{uid_bytes.decode()}"
            exists = conn.execute("SELECT id FROM emails WHERE uid = ?", (uid,)).fetchone()
            if exists:
                continue

            _, msg_data = imap.fetch(uid_bytes, "(RFC822)")
            raw = msg_data[0][1] if msg_data and msg_data[0] else None
            if not raw:
                continue

            msg = email.message_from_bytes(raw)
            subject = _decode_header(msg.get("Subject", "(brak tematu)"))
            sender = _decode_header(msg.get("From", ""))
            recipients = _decode_header(msg.get("To", ""))
            date_str = msg.get("Date", "")
            try:
                date_parsed = email.utils.parsedate_to_datetime(date_str).isoformat()
            except Exception:
                date_parsed = datetime.now().isoformat()

            body_text, body_html = _get_body(msg)

            sender_email = email.utils.parseaddr(sender)[1]
            client = client_svc.find_by_email(sender_email)
            client_id = client.id if client else None

            cur = conn.execute(
                """INSERT OR IGNORE INTO emails
                   (uid, folder, subject, sender, recipients, date, body_text, body_html, is_read, client_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (uid, folder, subject, sender, recipients, date_parsed,
                 body_text, body_html, client_id),
            )
            conn.commit()
            if cur.lastrowid:
                atts = _get_attachments(msg, cur.lastrowid)
                for att in atts:
                    conn.execute(
                        """INSERT INTO email_attachments (email_id, filename, filepath, mime_type, size_bytes)
                           VALUES (?, ?, ?, ?, ?)""",
                        (att.email_id, att.filename, att.filepath, att.mime_type, att.size_bytes),
                    )
                conn.commit()
                new_count += 1

        imap.logout()
    except Exception as exc:
        _LAST_ERROR = f"{type(exc).__name__}: {exc}"
        return new_count, 1

    return new_count, 0


def get_last_error() -> str:
    return _LAST_ERROR


_LAST_ERROR = ""


def get_all(unread_only: bool = False, client_id: int = None) -> List[EmailMessage]:
    conn = get_conn()
    sql = """SELECT e.*, c.name as client_name
             FROM emails e LEFT JOIN clients c ON e.client_id = c.id"""
    conditions, params = [], []
    if unread_only:
        conditions.append("e.is_read = 0")
    if client_id:
        conditions.append("e.client_id = ?")
        params.append(client_id)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY e.date DESC"
    rows = conn.execute(sql, params).fetchall()
    return [EmailMessage.from_row(r) for r in rows]


def get_by_id(email_id: int) -> Optional[EmailMessage]:
    conn = get_conn()
    row = conn.execute(
        """SELECT e.*, c.name as client_name
           FROM emails e LEFT JOIN clients c ON e.client_id = c.id
           WHERE e.id = ?""",
        (email_id,),
    ).fetchone()
    if not row:
        return None
    msg = EmailMessage.from_row(row)
    att_rows = conn.execute(
        "SELECT * FROM email_attachments WHERE email_id = ?", (email_id,)
    ).fetchall()
    msg.attachments = [
        EmailAttachment(**{k: r[k] for k in r.keys()}) for r in att_rows
    ]
    return msg


def mark_read(email_id: int, read: bool = True) -> None:
    conn = get_conn()
    conn.execute("UPDATE emails SET is_read = ? WHERE id = ?", (int(read), email_id))
    conn.commit()


def assign_client(email_id: int, client_id: Optional[int]) -> None:
    conn = get_conn()
    conn.execute("UPDATE emails SET client_id = ? WHERE id = ?", (client_id, email_id))
    conn.commit()


def assign_order(email_id: int, order_id: Optional[int]) -> None:
    conn = get_conn()
    conn.execute("UPDATE emails SET order_id = ? WHERE id = ?", (order_id, email_id))
    conn.commit()


def delete(email_id: int) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
    conn.commit()


def get_unread_count() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM emails WHERE is_read = 0").fetchone()
    return row["cnt"] if row else 0
