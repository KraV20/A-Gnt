from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QStatusBar, QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
import app.config as cfg_module
from app.ui.styles import MAIN_STYLE
from app.ui.panels.email_panel import EmailPanel
from app.ui.panels.clients_panel import ClientsPanel
from app.ui.panels.orders_panel import OrdersPanel
from app.ui.panels.documents_panel import DocumentsPanel
from app.ui.panels.whokna_panel import WhoKnaPanel
from app.ui.panels.ai_panel import AiPanel
from app.ui.panels.pricing_panel import PricingPanel
from app.ui.dialogs.settings_dialog import SettingsDialog
import app.services.email_service as email_svc


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._cfg = cfg_module.load()
        self.setWindowTitle("A-Gnt – Zarządzanie klientami i zleceniami")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)
        self.setStyleSheet(MAIN_STYLE)
        self._setup_ui()
        self._refresh_unread_badge()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        app_title = QLabel("A-Gnt")
        app_title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(app_title)

        version_lbl = QLabel("v1.0.0  •  WHOkna Edition")
        version_lbl.setObjectName("sidebarVersion")
        sidebar_layout.addWidget(version_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2d3e52;")
        sidebar_layout.addWidget(sep)

        self._nav_buttons = []

        nav_items = [
            ("  Skrzynka", "email"),
            ("  Klienci", "clients"),
            ("  Zlecenia", "orders"),
            ("  Dokumenty", "documents"),
            ("  WHOkna", "whokna"),
            ("  AI Agent", "ai"),
            ("  Kalkulator", "pricing"),
        ]

        for label, name in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setProperty("panel", name)
            btn.clicked.connect(lambda checked, n=name: self._switch_panel(n))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        self._unread_label = QLabel("")
        self._unread_label.setObjectName("unreadBadge")
        self._unread_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._unread_label.hide()
        sidebar_layout.addWidget(self._unread_label)

        sidebar_layout.addStretch()

        settings_btn = QPushButton("  Ustawienia")
        settings_btn.setObjectName("navBtn")
        settings_btn.clicked.connect(self._open_settings)
        sidebar_layout.addWidget(settings_btn)

        root.addWidget(sidebar)

        # Content area
        content = QWidget()
        content.setObjectName("contentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._stack = QStackedWidget()

        self._email_panel = EmailPanel(self._cfg)
        self._email_panel.unread_changed.connect(self._update_unread_badge)
        self._clients_panel = ClientsPanel()
        self._orders_panel = OrdersPanel()
        self._documents_panel = DocumentsPanel()
        self._whokna_panel = WhoKnaPanel(self._cfg)
        self._whokna_panel.sync_done.connect(self._on_whokna_sync)
        self._ai_panel = AiPanel(self._cfg)
        self._pricing_panel = PricingPanel()

        self._stack.addWidget(self._email_panel)
        self._stack.addWidget(self._clients_panel)
        self._stack.addWidget(self._orders_panel)
        self._stack.addWidget(self._documents_panel)
        self._stack.addWidget(self._whokna_panel)
        self._stack.addWidget(self._ai_panel)
        self._stack.addWidget(self._pricing_panel)

        content_layout.addWidget(self._stack)
        root.addWidget(content)

        # Status bar
        self.statusBar().showMessage("Gotowy")

        # Select first panel
        self._switch_panel("email")

    def _switch_panel(self, name: str):
        panels = {
            "email": (0, self._email_panel),
            "clients": (1, self._clients_panel),
            "orders": (2, self._orders_panel),
            "documents": (3, self._documents_panel),
            "whokna": (4, self._whokna_panel),
            "ai": (5, self._ai_panel),
            "pricing": (6, self._pricing_panel),
        }
        if name not in panels:
            return
        idx, panel = panels[name]
        self._stack.setCurrentIndex(idx)

        for btn in self._nav_buttons:
            btn.setChecked(btn.property("panel") == name)

        if hasattr(panel, "refresh"):
            panel.refresh()

    def _open_settings(self):
        dlg = SettingsDialog(self._cfg, self)
        if dlg.exec():
            self._cfg = dlg.get_config()
            self._email_panel.cfg = self._cfg
            self._whokna_panel.refresh(self._cfg)
            self._ai_panel.refresh(self._cfg)
            self.statusBar().showMessage("Ustawienia zapisane.", 3000)

    def _refresh_unread_badge(self):
        count = email_svc.get_unread_count()
        self._update_unread_badge(count)

    def _update_unread_badge(self, count: int):
        for btn in self._nav_buttons:
            if btn.property("panel") == "email":
                if count > 0:
                    btn.setText(f"  Skrzynka ({count})")
                else:
                    btn.setText("  Skrzynka")
                break

    def _on_whokna_sync(self):
        self._clients_panel.refresh()
        self._orders_panel.refresh()
        self.statusBar().showMessage("Synchronizacja WHOkna zakończona.", 4000)
