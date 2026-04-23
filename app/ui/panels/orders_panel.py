from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QAbstractItemView,
    QSplitter, QGroupBox, QFormLayout, QTextEdit, QComboBox,
    QDoubleSpinBox, QDateEdit, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QColor
import app.services.order_service as order_svc
import app.services.client_service as client_svc
from app.models.order import Order, ORDER_STATUSES, ORDER_PRIORITIES
from app.ui.styles import STATUS_COLORS, PRIORITY_COLORS


class OrdersPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._orders = []
        self._setup_ui()
        self._load_orders()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Zlecenia")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("Szukaj zlecenia...")
        self.search_input.textChanged.connect(self._on_search)
        header.addWidget(self.search_input)

        self.status_filter = QComboBox()
        self.status_filter.addItem("Wszystkie statusy", "")
        for s in ORDER_STATUSES:
            self.status_filter.addItem(s.capitalize(), s)
        self.status_filter.currentIndexChanged.connect(self._load_orders)
        header.addWidget(self.status_filter)

        add_btn = QPushButton("+ Nowe zlecenie")
        add_btn.clicked.connect(self._add_order)
        header.addWidget(add_btn)
        layout.addLayout(header)

        # Stats bar
        self.stats_bar = QHBoxLayout()
        self._stat_labels = {}
        for status in ORDER_STATUSES:
            lbl = QLabel("0")
            color = STATUS_COLORS.get(status, "#6b7280")
            lbl.setStyleSheet(
                f"background:{color}22;color:{color};border-radius:12px;"
                f"padding:3px 10px;font-size:11px;font-weight:bold;"
            )
            lbl.setToolTip(status.capitalize())
            self.stats_bar.addWidget(QLabel(f"{status.capitalize()}:"))
            self.stats_bar.addWidget(lbl)
            self._stat_labels[status] = lbl
        self.stats_bar.addStretch()
        layout.addLayout(self.stats_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Numer", "Klient", "Tytuł", "Status", "Priorytet", "Termin", "Wartość"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.table)

        self.detail = OrderDetail()
        self.detail.saved.connect(self._on_save)
        self.detail.deleted.connect(self._on_delete)
        splitter.addWidget(self.detail)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.count_label)

    def _load_orders(self, *_):
        query = self.search_input.text().strip()
        status = self.status_filter.currentData()

        if query:
            orders = order_svc.search(query)
        else:
            orders = order_svc.get_all(status=status or None)

        self._orders = orders
        self.table.setRowCount(len(orders))

        for row, o in enumerate(orders):
            color = STATUS_COLORS.get(o.status, "#6b7280")
            items = [
                QTableWidgetItem(o.number),
                QTableWidgetItem(o.client_name or ""),
                QTableWidgetItem(o.title),
                QTableWidgetItem(o.status),
                QTableWidgetItem(o.priority),
                QTableWidgetItem(o.deadline[:10] if o.deadline else ""),
                QTableWidgetItem(o.value_display),
            ]
            items[3].setForeground(QColor(color))
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

        stats = order_svc.get_stats()
        for s, lbl in self._stat_labels.items():
            lbl.setText(str(stats.get(s, 0)))

        self.count_label.setText(f"Zleceń: {len(orders)}")

    def _on_search(self, text: str):
        self._load_orders()

    def _on_selection(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._orders):
            return
        self.detail.load(self._orders[row])

    def _add_order(self):
        self.detail.load(Order())

    def _on_save(self, order: Order):
        if order.id:
            order_svc.update(order)
        else:
            order_svc.create(order)
        self._load_orders()

    def _on_delete(self, order_id: int):
        reply = QMessageBox.question(
            self, "Usuń zlecenie",
            "Czy na pewno chcesz usunąć to zlecenie?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            order_svc.delete(order_id)
            self.detail.load(Order())
            self._load_orders()

    def refresh(self):
        self.detail._populate_client_combo()
        self._load_orders()


class OrderDetail(QWidget):
    saved = pyqtSignal(Order)
    deleted = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._order = Order()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)

        box = QGroupBox("Szczegóły zlecenia")
        form = QFormLayout(box)
        form.setSpacing(8)

        self.title_edit = QLineEdit()
        self.client_combo = QComboBox()
        self._populate_client_combo()
        self.status_combo = QComboBox()
        for s in ORDER_STATUSES:
            self.status_combo.addItem(s.capitalize(), s)
        self.priority_combo = QComboBox()
        for p in ORDER_PRIORITIES:
            self.priority_combo.addItem(p.capitalize(), p)

        self.order_date_edit = QDateEdit(QDate.currentDate())
        self.order_date_edit.setCalendarPopup(True)
        self.order_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.deadline_edit = QDateEdit(QDate.currentDate())
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("yyyy-MM-dd")

        self.value_edit = QDoubleSpinBox()
        self.value_edit.setMaximum(9_999_999)
        self.value_edit.setPrefix("PLN ")
        self.value_edit.setDecimals(2)

        self.whokna_edit = QLineEdit()
        self.whokna_edit.setPlaceholderText("ID w WHOkna (opcjonalne)")
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(70)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(70)

        form.addRow("Tytuł *", self.title_edit)
        form.addRow("Klient", self.client_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Priorytet", self.priority_combo)
        form.addRow("Data zlecenia", self.order_date_edit)
        form.addRow("Termin realizacji", self.deadline_edit)
        form.addRow("Wartość", self.value_edit)
        form.addRow("ID WHOkna", self.whokna_edit)
        form.addRow("Opis", self.desc_edit)
        form.addRow("Notatki", self.notes_edit)
        layout.addWidget(box)

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Zapisz")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        self.del_btn = QPushButton("Usuń")
        self.del_btn.setObjectName("dangerBtn")
        self.del_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def _populate_client_combo(self):
        self.client_combo.clear()
        self.client_combo.addItem("— brak klienta —", None)
        for c in client_svc.get_all():
            self.client_combo.addItem(c.display_name, c.id)

    def load(self, order: Order):
        self._order = order
        self.title_edit.setText(order.title)
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == order.client_id:
                self.client_combo.setCurrentIndex(i)
                break
        else:
            self.client_combo.setCurrentIndex(0)
        idx_s = next((i for i in range(self.status_combo.count())
                      if self.status_combo.itemData(i) == order.status), 0)
        self.status_combo.setCurrentIndex(idx_s)
        idx_p = next((i for i in range(self.priority_combo.count())
                      if self.priority_combo.itemData(i) == order.priority), 1)
        self.priority_combo.setCurrentIndex(idx_p)
        if order.order_date:
            self.order_date_edit.setDate(QDate.fromString(order.order_date[:10], "yyyy-MM-dd"))
        if order.deadline:
            self.deadline_edit.setDate(QDate.fromString(order.deadline[:10], "yyyy-MM-dd"))
        self.value_edit.setValue(order.value or 0.0)
        self.whokna_edit.setText(order.whokna_id or "")
        self.desc_edit.setPlainText(order.description)
        self.notes_edit.setPlainText(order.notes)
        self.del_btn.setEnabled(bool(order.id))

    def _save(self):
        if not self.title_edit.text().strip():
            self.title_edit.setFocus()
            return
        self._order.title = self.title_edit.text().strip()
        self._order.client_id = self.client_combo.currentData()
        self._order.status = self.status_combo.currentData()
        self._order.priority = self.priority_combo.currentData()
        self._order.order_date = self.order_date_edit.date().toString("yyyy-MM-dd")
        self._order.deadline = self.deadline_edit.date().toString("yyyy-MM-dd")
        self._order.value = self.value_edit.value() or None
        self._order.whokna_id = self.whokna_edit.text().strip()
        self._order.description = self.desc_edit.toPlainText().strip()
        self._order.notes = self.notes_edit.toPlainText().strip()
        self.saved.emit(self._order)

    def _delete(self):
        if self._order.id:
            self.deleted.emit(self._order.id)
