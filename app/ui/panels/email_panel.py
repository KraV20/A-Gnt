from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QSplitter, QTextBrowser, QLineEdit, QComboBox,
    QCheckBox, QFrame, QHeaderView, QAbstractItemView, QMenu,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor
import app.services.email_service as email_svc
import app.services.client_service as client_svc
import app.services.order_service as order_svc
from app.models.email_message import EmailMessage


class FetchWorker(QThread):
    finished = pyqtSignal(int, int)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg

    def run(self):
        new, err = email_svc.fetch_emails(self.cfg)
        self.finished.emit(new, err)


class EmailPanel(QWidget):
    unread_changed = pyqtSignal(int)

    def __init__(self, app_config: dict, parent=None):
        super().__init__(parent)
        self.cfg = app_config
        self.current_email = None
        self._fetch_worker = None
        self._setup_ui()
        self._load_emails()
        self._setup_auto_fetch()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Skrzynka pocztowa")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("Szukaj w mailach...")
        self.search_input.returnPressed.connect(self._load_emails)
        header.addWidget(self.search_input)

        self.unread_cb = QCheckBox("Tylko nieprzeczytane")
        self.unread_cb.stateChanged.connect(self._load_emails)
        header.addWidget(self.unread_cb)

        self.fetch_btn = QPushButton("Pobierz maile")
        self.fetch_btn.clicked.connect(self._fetch_emails)
        header.addWidget(self.fetch_btn)

        layout.addLayout(header)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Email list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nadawca", "Temat", "Data", "Klient"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        list_layout.addWidget(self.table)
        splitter.addWidget(list_widget)

        # Email detail
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(8, 0, 0, 0)

        self.detail_header = QLabel("")
        self.detail_header.setWordWrap(True)
        self.detail_header.setStyleSheet("background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:10px;")
        detail_layout.addWidget(self.detail_header)

        self.detail_body = QTextBrowser()
        self.detail_body.setOpenExternalLinks(True)
        detail_layout.addWidget(self.detail_body)

        assign_row = QHBoxLayout()
        assign_row.addWidget(QLabel("Klient:"))
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(160)
        assign_row.addWidget(self.client_combo)
        assign_row.addWidget(QLabel("Zlecenie:"))
        self.order_combo = QComboBox()
        self.order_combo.setMinimumWidth(160)
        assign_row.addWidget(self.order_combo)
        self.assign_btn = QPushButton("Przypisz")
        self.assign_btn.clicked.connect(self._assign)
        assign_row.addWidget(self.assign_btn)
        assign_row.addStretch()
        detail_layout.addLayout(assign_row)

        splitter.addWidget(detail_widget)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.status_label)

        self._populate_combos()

    def _populate_combos(self):
        self.client_combo.clear()
        self.client_combo.addItem("— brak —", None)
        for c in client_svc.get_all():
            self.client_combo.addItem(c.display_name, c.id)

        self.order_combo.clear()
        self.order_combo.addItem("— brak —", None)
        for o in order_svc.get_all():
            self.order_combo.addItem(f"{o.number} – {o.title}", o.id)

    def _load_emails(self):
        query = self.search_input.text().strip()
        unread_only = self.unread_cb.isChecked()
        emails = email_svc.get_all(unread_only=unread_only)

        if query:
            q = query.lower()
            emails = [e for e in emails if q in e.subject.lower() or q in e.sender.lower()]

        self.table.setRowCount(len(emails))
        self._emails = emails
        for row, msg in enumerate(emails):
            sender_item = QTableWidgetItem(msg.sender[:40])
            subject_item = QTableWidgetItem(msg.subject)
            date_item = QTableWidgetItem(msg.date[:16])
            client_item = QTableWidgetItem(msg.client_name or "")

            if not msg.is_read:
                font = QFont()
                font.setBold(True)
                for item in (sender_item, subject_item, date_item, client_item):
                    item.setFont(font)

            self.table.setItem(row, 0, sender_item)
            self.table.setItem(row, 1, subject_item)
            self.table.setItem(row, 2, date_item)
            self.table.setItem(row, 3, client_item)

        unread = email_svc.get_unread_count()
        self.unread_changed.emit(unread)
        self.status_label.setText(f"Wyświetlono: {len(emails)} | Nieprzeczytane: {unread}")

    def _on_selection(self):
        rows = self.table.selectedItems()
        if not rows:
            return
        row = self.table.currentRow()
        if row < 0 or row >= len(self._emails):
            return
        msg = self._emails[row]
        full = email_svc.get_by_id(msg.id)
        if not full:
            return
        self.current_email = full
        email_svc.mark_read(full.id, True)

        header_html = (
            f"<b>Od:</b> {full.sender}<br>"
            f"<b>Do:</b> {full.recipients}<br>"
            f"<b>Temat:</b> {full.subject}<br>"
            f"<b>Data:</b> {full.date}"
        )
        if full.attachments:
            names = ", ".join(a.filename for a in full.attachments)
            header_html += f"<br><b>Załączniki:</b> {names}"
        self.detail_header.setText(header_html)

        if full.body_html:
            self.detail_body.setHtml(full.body_html)
        else:
            self.detail_body.setPlainText(full.body_text)

        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == full.client_id:
                self.client_combo.setCurrentIndex(i)
                break

        for i in range(self.order_combo.count()):
            if self.order_combo.itemData(i) == full.order_id:
                self.order_combo.setCurrentIndex(i)
                break

        self._load_emails()

    def _assign(self):
        if not self.current_email:
            return
        client_id = self.client_combo.currentData()
        order_id = self.order_combo.currentData()
        email_svc.assign_client(self.current_email.id, client_id)
        email_svc.assign_order(self.current_email.id, order_id)
        self._load_emails()

    def _fetch_emails(self):
        email_cfg = self.cfg.get("email", {})
        if not email_cfg.get("imap_host") or not email_cfg.get("username"):
            self.status_label.setText("Skonfiguruj konto e-mail w Ustawieniach")
            return
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Pobieranie...")
        self._fetch_worker = FetchWorker(email_cfg)
        self._fetch_worker.finished.connect(self._on_fetch_done)
        self._fetch_worker.start()

    def _on_fetch_done(self, new_count: int, errors: int):
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Pobierz maile")
        self._load_emails()
        if errors:
            err = email_svc.get_last_error()
            self.status_label.setText(f"Błąd IMAP: {err}")
            self.status_label.setStyleSheet("color:#dc2626;font-size:11px;")
        else:
            self.status_label.setText(f"Pobrano {new_count} nowych wiadomości.")
            self.status_label.setStyleSheet("color:#16a34a;font-size:11px;")

    def _setup_auto_fetch(self):
        if not hasattr(self, "_timer"):
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._fetch_emails)
        self._timer.stop()
        minutes = self.cfg.get("email", {}).get("auto_fetch_minutes", 5)
        if minutes > 0:
            self._timer.start(minutes * 60 * 1000)

    def _context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self._emails):
            return
        msg = self._emails[row]
        menu = QMenu(self)
        if msg.is_read:
            menu.addAction("Oznacz jako nieprzeczytane", lambda: (email_svc.mark_read(msg.id, False), self._load_emails()))
        else:
            menu.addAction("Oznacz jako przeczytane", lambda: (email_svc.mark_read(msg.id, True), self._load_emails()))
        menu.addSeparator()
        menu.addAction("Usuń", lambda: (email_svc.delete(msg.id), self._load_emails()))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def refresh(self):
        self._populate_combos()
        self._load_emails()
        self._setup_auto_fetch()
