from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QAbstractItemView, QGroupBox,
    QFormLayout, QLineEdit, QCheckBox, QMessageBox, QProgressDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import app.services.whokna_service as whokna_svc


class SyncWorker(QThread):
    finished = pyqtSignal(int, int, str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            clients, orders = whokna_svc.sync_to_local(self.cfg)
            self.finished.emit(clients, orders, "")
        except Exception as e:
            self.finished.emit(0, 0, str(e))


class WhoKnaPanel(QWidget):
    sync_done = pyqtSignal()

    def __init__(self, app_config: dict, parent=None):
        super().__init__(parent)
        self.cfg = app_config
        self._orders = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        title = QLabel("Integracja z WHOkna")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # Connection info
        status_box = QGroupBox("Status połączenia")
        status_layout = QVBoxLayout(status_box)
        self.conn_status = QLabel("Nie skonfigurowano")
        self.conn_status.setStyleSheet("color: #6b7280; font-size: 13px;")
        status_layout.addWidget(self.conn_status)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("Testuj połączenie")
        test_btn.clicked.connect(self._test_connection)
        btn_row.addWidget(test_btn)

        self.sync_btn = QPushButton("Synchronizuj z WHOkna")
        self.sync_btn.setObjectName("successBtn")
        self.sync_btn.clicked.connect(self._sync)
        btn_row.addWidget(self.sync_btn)
        btn_row.addStretch()
        status_layout.addLayout(btn_row)
        layout.addWidget(status_box)

        # Orders preview
        orders_box = QGroupBox("Zlecenia z WHOkna (podgląd)")
        orders_layout = QVBoxLayout(orders_box)

        preview_btn = QPushButton("Załaduj podgląd")
        preview_btn.clicked.connect(self._load_preview)
        orders_layout.addWidget(preview_btn)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID WHOkna", "Numer", "Tytuł", "Klient", "Data", "Wartość"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        orders_layout.addWidget(self.table)
        layout.addWidget(orders_box)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #374151; font-size: 12px;")
        layout.addWidget(self.info_label)
        layout.addStretch()

        self._update_status()

    def _update_status(self):
        whokna_cfg = self.cfg.get("whokna", {})
        if not whokna_cfg.get("enabled"):
            self.conn_status.setText("WHOkna integracja wyłączona. Włącz w Ustawieniach.")
            self.conn_status.setStyleSheet("color: #6b7280;")
            self.sync_btn.setEnabled(False)
        elif not whokna_cfg.get("server") and not whokna_cfg.get("dsn"):
            self.conn_status.setText("Brak konfiguracji serwera. Skonfiguruj w Ustawieniach.")
            self.conn_status.setStyleSheet("color: #f59e0b;")
            self.sync_btn.setEnabled(False)
        else:
            self.conn_status.setText(
                f"Serwer: {whokna_cfg.get('server', '–')}  "
                f"Baza: {whokna_cfg.get('database', 'WHOkna')}"
            )
            self.conn_status.setStyleSheet("color: #374151;")
            self.sync_btn.setEnabled(True)

    def _test_connection(self):
        whokna_cfg = self.cfg.get("whokna", {})
        if not whokna_cfg.get("enabled"):
            QMessageBox.information(self, "WHOkna", "Integracja jest wyłączona w ustawieniach.")
            return
        ok, msg = whokna_svc.test_connection(whokna_cfg)
        if ok:
            QMessageBox.information(self, "Połączenie", f"Sukces: {msg}")
        else:
            QMessageBox.critical(self, "Błąd połączenia", msg)

    def _load_preview(self):
        whokna_cfg = self.cfg.get("whokna", {})
        if not whokna_cfg.get("enabled"):
            self.info_label.setText("Integracja WHOkna jest wyłączona.")
            return
        orders = whokna_svc.get_orders(whokna_cfg, limit=100)
        if not orders:
            self.info_label.setText("Brak danych lub błąd połączenia.")
            self.table.setRowCount(0)
            return
        self.table.setRowCount(len(orders))
        for row, o in enumerate(orders):
            self.table.setItem(row, 0, QTableWidgetItem(str(o.get("whokna_id", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(o.get("number", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(o.get("title", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(o.get("client_name", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(str(o.get("order_date", ""))[:10]))
            val = o.get("value")
            self.table.setItem(row, 5, QTableWidgetItem(f"{val:,.2f} PLN" if val else ""))
        self.info_label.setText(f"Załadowano {len(orders)} zleceń z WHOkna.")

    def _sync(self):
        whokna_cfg = self.cfg.get("whokna", {})
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("Synchronizuję...")
        self._worker = SyncWorker(whokna_cfg)
        self._worker.finished.connect(self._on_sync_done)
        self._worker.start()

    def _on_sync_done(self, clients: int, orders: int, error: str):
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("Synchronizuj z WHOkna")
        if error:
            QMessageBox.critical(self, "Błąd synchronizacji", error)
        else:
            self.info_label.setText(
                f"Synchronizacja zakończona. Dodano: {clients} klientów, {orders} zleceń."
            )
            self.sync_done.emit()

    def refresh(self, cfg: dict):
        self.cfg = cfg
        self._update_status()
