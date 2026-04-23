from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QAbstractItemView,
    QSplitter, QGroupBox, QFormLayout, QTextEdit, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
import app.services.client_service as client_svc
import app.services.order_service as order_svc
import app.services.email_service as email_svc
from app.models.client import Client


class ClientsPanel(QWidget):
    client_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_client = None
        self._clients = []
        self._setup_ui()
        self._load_clients()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Klienci")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("Szukaj klienta...")
        self.search_input.textChanged.connect(self._on_search)
        header.addWidget(self.search_input)

        add_btn = QPushButton("+ Dodaj klienta")
        add_btn.clicked.connect(self._add_client)
        header.addWidget(add_btn)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Client list
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nazwa", "Firma", "E-mail", "Telefon", "Miasto"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.table)

        # Detail panel
        self.detail = ClientDetail()
        self.detail.saved.connect(self._on_save)
        self.detail.deleted.connect(self._on_delete)
        splitter.addWidget(self.detail)
        splitter.setSizes([450, 550])

        layout.addWidget(splitter)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.count_label)

    def _load_clients(self, query: str = ""):
        if query:
            clients = client_svc.search(query)
        else:
            clients = client_svc.get_all()
        self._clients = clients
        self.table.setRowCount(len(clients))
        for row, c in enumerate(clients):
            self.table.setItem(row, 0, QTableWidgetItem(c.name))
            self.table.setItem(row, 1, QTableWidgetItem(c.company))
            self.table.setItem(row, 2, QTableWidgetItem(c.email))
            self.table.setItem(row, 3, QTableWidgetItem(c.phone))
            self.table.setItem(row, 4, QTableWidgetItem(c.city))
        self.count_label.setText(f"Klientów: {len(clients)}")

    def _on_search(self, text: str):
        self._load_clients(text.strip())

    def _on_selection(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._clients):
            return
        client = self._clients[row]
        self.current_client = client
        orders = order_svc.get_by_client(client.id)
        emails = email_svc.get_all(client_id=client.id)
        self.detail.load(client, orders, emails)

    def _add_client(self):
        self.current_client = None
        self.detail.load(Client())

    def _on_save(self, client: Client):
        if client.id:
            client_svc.update(client)
        else:
            client = client_svc.create(client)
        self._load_clients(self.search_input.text().strip())

    def _on_delete(self, client_id: int):
        reply = QMessageBox.question(
            self, "Usuń klienta",
            "Czy na pewno chcesz usunąć tego klienta?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            client_svc.delete(client_id)
            self.detail.load(Client())
            self._load_clients(self.search_input.text().strip())

    def refresh(self):
        self._load_clients(self.search_input.text().strip())


class ClientDetail(QWidget):
    saved = pyqtSignal(Client)
    deleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = Client()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)

        form_box = QGroupBox("Dane klienta")
        form = QFormLayout(form_box)
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.company_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.address_edit = QLineEdit()
        self.city_edit = QLineEdit()
        self.postal_edit = QLineEdit()
        self.nip_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)

        form.addRow("Imię i nazwisko *", self.name_edit)
        form.addRow("Firma", self.company_edit)
        form.addRow("E-mail", self.email_edit)
        form.addRow("Telefon", self.phone_edit)
        form.addRow("Adres", self.address_edit)
        form.addRow("Miasto", self.city_edit)
        form.addRow("Kod pocztowy", self.postal_edit)
        form.addRow("NIP", self.nip_edit)
        form.addRow("Notatki", self.notes_edit)
        layout.addWidget(form_box)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Zapisz")
        self.save_btn.clicked.connect(self._save)
        btn_row.addWidget(self.save_btn)
        self.del_btn = QPushButton("Usuń")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Orders summary
        self.orders_label = QLabel("")
        self.orders_label.setWordWrap(True)
        self.orders_label.setStyleSheet("color: #374151; font-size: 12px; padding: 4px;")
        layout.addWidget(self.orders_label)
        layout.addStretch()

    def load(self, client: Client, orders=None, emails=None):
        self._client = client
        self.name_edit.setText(client.name)
        self.company_edit.setText(client.company)
        self.email_edit.setText(client.email)
        self.phone_edit.setText(client.phone)
        self.address_edit.setText(client.address)
        self.city_edit.setText(client.city)
        self.postal_edit.setText(client.postal_code)
        self.nip_edit.setText(client.nip)
        self.notes_edit.setPlainText(client.notes)
        self.del_btn.setEnabled(bool(client.id))

        if orders is not None:
            lines = [f"<b>Zlecenia ({len(orders)}):</b>"]
            for o in orders[:5]:
                lines.append(f"• {o.number} – {o.title} [{o.status}]")
            if emails:
                lines.append(f"<b>E-maile: {len(emails)}</b>")
            self.orders_label.setText("<br>".join(lines))
        else:
            self.orders_label.setText("")

    def _save(self):
        if not self.name_edit.text().strip():
            self.name_edit.setFocus()
            return
        self._client.name = self.name_edit.text().strip()
        self._client.company = self.company_edit.text().strip()
        self._client.email = self.email_edit.text().strip()
        self._client.phone = self.phone_edit.text().strip()
        self._client.address = self.address_edit.text().strip()
        self._client.city = self.city_edit.text().strip()
        self._client.postal_code = self.postal_edit.text().strip()
        self._client.nip = self.nip_edit.text().strip()
        self._client.notes = self.notes_edit.toPlainText().strip()
        self.saved.emit(self._client)

    def _delete(self):
        if self._client.id:
            self.deleted.emit(self._client.id)
