from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QGroupBox, QMessageBox,
)
from app.services.ai_service import PROVIDERS
from PyQt6.QtCore import Qt
import app.config as cfg_module
import app.services.whokna_service as whokna_svc


class SettingsDialog(QDialog):
    def __init__(self, app_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia – A-Gnt")
        self.setMinimumSize(520, 500)
        self._cfg = app_config
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- Email tab ---
        email_tab = QWidget()
        el = QFormLayout(email_tab)
        self.imap_host = QLineEdit()
        self.imap_host.setPlaceholderText("np. imap.gmail.com")
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_ssl = QCheckBox("Użyj SSL/TLS")
        self.imap_ssl.setChecked(True)
        self.smtp_host = QLineEdit()
        self.smtp_host.setPlaceholderText("np. smtp.gmail.com")
        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        self.email_user = QLineEdit()
        self.email_user.setPlaceholderText("adres@domena.pl")
        self.email_pass = QLineEdit()
        self.email_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_folder = QLineEdit()
        self.email_folder.setText("INBOX")
        self.auto_fetch = QSpinBox()
        self.auto_fetch.setRange(0, 120)
        self.auto_fetch.setSuffix(" min")
        self.auto_fetch.setSpecialValueText("wyłączone")

        el.addRow("Serwer IMAP:", self.imap_host)
        el.addRow("Port IMAP:", self.imap_port)
        el.addRow("", self.imap_ssl)
        el.addRow("Serwer SMTP:", self.smtp_host)
        el.addRow("Port SMTP:", self.smtp_port)
        el.addRow("Użytkownik:", self.email_user)
        el.addRow("Hasło:", self.email_pass)
        el.addRow("Folder:", self.email_folder)
        el.addRow("Autoodświeżanie:", self.auto_fetch)

        test_email_btn = QPushButton("Testuj połączenie IMAP")
        test_email_btn.clicked.connect(self._test_imap)
        el.addRow("", test_email_btn)
        tabs.addTab(email_tab, "E-mail")

        # --- WHOkna tab ---
        wh_tab = QWidget()
        wl = QFormLayout(wh_tab)
        self.wh_enabled = QCheckBox("Włącz integrację WHOkna")
        self.wh_server = QLineEdit()
        self.wh_server.setPlaceholderText("np. 192.168.1.100\\SQLEXPRESS")
        self.wh_database = QLineEdit()
        self.wh_database.setText("WHOkna")
        self.wh_driver = QComboBox()
        for d in [
            "ODBC Driver 17 for SQL Server",
            "ODBC Driver 18 for SQL Server",
            "SQL Server",
            "SQL Server Native Client 11.0",
        ]:
            self.wh_driver.addItem(d)
        self.wh_dsn = QLineEdit()
        self.wh_dsn.setPlaceholderText("Opcjonalnie: nazwa DSN")
        self.wh_user = QLineEdit()
        self.wh_pass = QLineEdit()
        self.wh_pass.setEchoMode(QLineEdit.EchoMode.Password)

        wl.addRow("", self.wh_enabled)
        wl.addRow("Serwer SQL:", self.wh_server)
        wl.addRow("Baza danych:", self.wh_database)
        wl.addRow("Sterownik ODBC:", self.wh_driver)
        wl.addRow("DSN (opcja):", self.wh_dsn)
        wl.addRow("Użytkownik SQL:", self.wh_user)
        wl.addRow("Hasło SQL:", self.wh_pass)

        note = QLabel(
            "WHOkna używa SQL Server. Zainstaluj sterownik ODBC\n"
            "i skonfiguruj połączenie z bazą danych programu WHOkna."
        )
        note.setStyleSheet("color: #6b7280; font-size: 11px;")
        wl.addRow("", note)

        test_wh_btn = QPushButton("Testuj połączenie WHOkna")
        test_wh_btn.clicked.connect(self._test_whokna)
        wl.addRow("", test_wh_btn)
        tabs.addTab(wh_tab, "WHOkna")

        # --- AI Agent tab ---
        ai_tab = QWidget()
        al = QFormLayout(ai_tab)

        self.ai_provider = QComboBox()
        for p in PROVIDERS:
            self.ai_provider.addItem(p)
        self.ai_provider.currentIndexChanged.connect(self._update_ai_model_hint)

        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_key.setPlaceholderText("sk-... / AIza... / anthropic key")

        self.ai_model = QLineEdit()
        self.ai_model_hint = QLabel("")
        self.ai_model_hint.setStyleSheet("color:#6b7280;font-size:11px;")

        al.addRow("Provider:", self.ai_provider)
        al.addRow("Klucz API:", self.ai_key)
        al.addRow("Model (opcja):", self.ai_model)
        al.addRow("", self.ai_model_hint)

        ai_note = QLabel(
            "Claude: claude-sonnet-4-6\n"
            "Gemini: gemini-2.0-flash\n"
            "OpenAI: gpt-4o-mini\n\n"
            "Klucze API nie są wysyłane nigdzie poza wybranym providerem."
        )
        ai_note.setStyleSheet("color:#6b7280;font-size:11px;")
        al.addRow("", ai_note)

        test_ai_btn = QPushButton("Testuj połączenie AI")
        test_ai_btn.clicked.connect(self._test_ai)
        al.addRow("", test_ai_btn)
        tabs.addTab(ai_tab, "AI Agent")

        layout.addWidget(tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load(self):
        ec = self._cfg.get("email", {})
        self.imap_host.setText(ec.get("imap_host", ""))
        self.imap_port.setValue(ec.get("imap_port", 993))
        self.imap_ssl.setChecked(ec.get("imap_ssl", True))
        self.smtp_host.setText(ec.get("smtp_host", ""))
        self.smtp_port.setValue(ec.get("smtp_port", 587))
        self.email_user.setText(ec.get("username", ""))
        self.email_pass.setText(ec.get("password", ""))
        self.email_folder.setText(ec.get("folder", "INBOX"))
        self.auto_fetch.setValue(ec.get("auto_fetch_minutes", 5))

        ac = self._cfg.get("ai", {})
        idx = self.ai_provider.findText(ac.get("provider", PROVIDERS[0]))
        self.ai_provider.setCurrentIndex(idx if idx >= 0 else 0)
        self.ai_key.setText(ac.get("api_key", ""))
        self.ai_model.setText(ac.get("model", ""))
        self._update_ai_model_hint()

        wc = self._cfg.get("whokna", {})
        self.wh_enabled.setChecked(wc.get("enabled", False))
        self.wh_server.setText(wc.get("server", ""))
        self.wh_database.setText(wc.get("database", "WHOkna"))
        drv = wc.get("driver", "ODBC Driver 17 for SQL Server")
        idx = self.wh_driver.findText(drv)
        if idx >= 0:
            self.wh_driver.setCurrentIndex(idx)
        self.wh_dsn.setText(wc.get("dsn", ""))
        self.wh_user.setText(wc.get("username", ""))
        self.wh_pass.setText(wc.get("password", ""))

    def _save(self):
        self._cfg["email"] = {
            "imap_host": self.imap_host.text().strip(),
            "imap_port": self.imap_port.value(),
            "imap_ssl": self.imap_ssl.isChecked(),
            "smtp_host": self.smtp_host.text().strip(),
            "smtp_port": self.smtp_port.value(),
            "username": self.email_user.text().strip(),
            "password": self.email_pass.text(),
            "folder": self.email_folder.text().strip() or "INBOX",
            "auto_fetch_minutes": self.auto_fetch.value(),
        }
        self._cfg["whokna"] = {
            "enabled": self.wh_enabled.isChecked(),
            "server": self.wh_server.text().strip(),
            "database": self.wh_database.text().strip() or "WHOkna",
            "driver": self.wh_driver.currentText(),
            "dsn": self.wh_dsn.text().strip(),
            "username": self.wh_user.text().strip(),
            "password": self.wh_pass.text(),
        }
        self._cfg["ai"] = {
            "provider": self.ai_provider.currentText(),
            "api_key": self.ai_key.text().strip(),
            "model": self.ai_model.text().strip(),
        }
        cfg_module.save(self._cfg)
        self.accept()

    def _test_imap(self):
        import app.services.email_service as email_svc
        host = self.imap_host.text().strip()
        user = self.email_user.text().strip()
        if not host or not user:
            QMessageBox.warning(self, "Błąd", "Uzupełnij host i użytkownika.")
            return
        cfg = {
            "imap_host": host,
            "imap_port": self.imap_port.value(),
            "imap_ssl": self.imap_ssl.isChecked(),
            "username": user,
            "password": self.email_pass.text(),
            "folder": self.email_folder.text().strip() or "INBOX",
        }
        ok, msg = email_svc.test_connection(cfg)
        if ok:
            QMessageBox.information(self, "IMAP", msg)
        else:
            hint = ""
            low = msg.lower()
            if "login" in low and ("bad" in low or "failed" in low or "invalid" in low):
                hint = (
                    "\n\nMożliwe przyczyny:\n"
                    "• Gmail / Outlook 365 wymagają hasła aplikacji (nie zwykłego hasła konta)\n"
                    "• Hasło zawiera znaki specjalne – sprawdź, czy nie ma spacji na końcu\n"
                    "• Konto wymaga 2FA + tokenu aplikacji\n"
                    "• Niektóre serwery (np. wp.pl) wymagają loginu BEZ @domena"
                )
            QMessageBox.critical(self, "Błąd IMAP", msg + hint)

    def _test_whokna(self):
        cfg = {
            "enabled": True,
            "server": self.wh_server.text().strip(),
            "database": self.wh_database.text().strip() or "WHOkna",
            "driver": self.wh_driver.currentText(),
            "dsn": self.wh_dsn.text().strip(),
            "username": self.wh_user.text().strip(),
            "password": self.wh_pass.text(),
        }
        ok, msg = whokna_svc.test_connection(cfg)
        if ok:
            QMessageBox.information(self, "WHOkna", f"Połączono pomyślnie!\n{msg}")
        else:
            QMessageBox.critical(self, "Błąd WHOkna", msg)

    def _update_ai_model_hint(self):
        provider = self.ai_provider.currentText()
        hints = {
            "Claude (Anthropic)": "domyślnie: claude-sonnet-4-6",
            "Gemini (Google)": "domyślnie: gemini-2.0-flash",
            "OpenAI": "domyślnie: gpt-4o-mini",
        }
        self.ai_model_hint.setText(hints.get(provider, ""))

    def _test_ai(self):
        import app.services.ai_service as ai_svc
        cfg = {
            "provider": self.ai_provider.currentText(),
            "api_key": self.ai_key.text().strip(),
            "model": self.ai_model.text().strip(),
        }
        if not cfg["api_key"]:
            QMessageBox.warning(self, "Błąd", "Wpisz klucz API.")
            return
        try:
            resp = ai_svc.chat(cfg, [{"role": "user", "content": "Odpowiedz jednym słowem: cześć"}])
            QMessageBox.information(self, "AI Agent", f"Połączono!\nOdpowiedź: {resp}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd AI", str(e))

    def get_config(self) -> dict:
        return self._cfg
