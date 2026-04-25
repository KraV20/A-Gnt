CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    company     TEXT,
    email       TEXT,
    phone       TEXT,
    address     TEXT,
    city        TEXT,
    postal_code TEXT,
    nip         TEXT,
    notes       TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id       INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    number          TEXT UNIQUE,
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT DEFAULT 'nowe',
    priority        TEXT DEFAULT 'normalny',
    order_date      TEXT,
    deadline        TEXT,
    completion_date TEXT,
    value           REAL,
    currency        TEXT DEFAULT 'PLN',
    whokna_id       TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS emails (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uid         TEXT UNIQUE,
    folder      TEXT,
    subject     TEXT,
    sender      TEXT,
    recipients  TEXT,
    date        TEXT,
    body_text   TEXT,
    body_html   TEXT,
    is_read     INTEGER DEFAULT 0,
    is_flagged  INTEGER DEFAULT 0,
    client_id   INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    filepath    TEXT NOT NULL,
    category    TEXT DEFAULT 'inne',
    client_id   INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    order_id    INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    description TEXT,
    tags        TEXT,
    size_bytes  INTEGER,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS email_attachments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id    INTEGER REFERENCES emails(id) ON DELETE CASCADE,
    filename    TEXT,
    filepath    TEXT,
    mime_type   TEXT,
    size_bytes  INTEGER
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    title        TEXT NOT NULL,
    description  TEXT,
    event_date   TEXT NOT NULL,
    event_time   TEXT,
    duration_min INTEGER DEFAULT 60,
    event_type   TEXT DEFAULT 'spotkanie',
    location     TEXT,
    client_id    INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    order_id     INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    is_done      INTEGER DEFAULT 0,
    reminder_min INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now','localtime')),
    updated_at   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_orders_client ON orders(client_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_emails_client ON emails(client_id);
CREATE INDEX IF NOT EXISTS idx_emails_order ON emails(order_id);
CREATE INDEX IF NOT EXISTS idx_emails_is_read ON emails(is_read);
CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);
CREATE INDEX IF NOT EXISTS idx_documents_order ON documents(order_id);
CREATE INDEX IF NOT EXISTS idx_calendar_date ON calendar_events(event_date);
CREATE INDEX IF NOT EXISTS idx_calendar_client ON calendar_events(client_id);
CREATE INDEX IF NOT EXISTS idx_calendar_order ON calendar_events(order_id);
