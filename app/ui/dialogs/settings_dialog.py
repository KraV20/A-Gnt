from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QGroupBox, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from app.services.ai_service import PROVIDERS
import app.config as cfg_module
import app.services.ai_service as ai_svc
import app.services.whokna_service as whokna_svc


class SettingsDialog(QDialog):
    def __init__(self, app_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ustawienia - A-Gnt")
        self.setMinimumSize(520, 500)
        self._cfg = app_config
        self._ai_models_loaded_for = None
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        email_tab = QWidget()
        el = QFormLayout(email_tab)
        self.imap_host = QLineEdit()
        self.imap_host.setPlaceholderText("np. imap.gmail.com")
        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        self.imap_ssl = QCheckBox("Uzyj SSL/TLS")
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
        self.auto_fetch.setSpecialValueText("wylaczone")

        el.addRow("Serwer IMAP:", self.imap_host)
        el.addRow("Port IMAP:", self.imap_port)
        el.addRow("", self.imap_ssl)
        el.addRow("Serwer SMTP:", self.smtp_host)
        el.addRow("Port SMTP:", self.smtp_port)
        el.addRow("Uzytkownik:", self.email_user)
        el.addRow("Haslo:", self.email_pass)
        el.addRow("Folder:", self.email_folder)
        el.addRow("Autoodswiezanie:", self.auto_fetch)

        test_email_btn = QPushButton("Testuj polaczenie IMAP")
        test_email_btn.clicked.connect(self._test_imap)
        el.addRow("", test_email_btn)
        tabs.addTab(email_tab, "E-mail")

        wh_tab = QWidget()
        wl = QFormLayout(wh_tab)
        self.wh_enabled = QCheckBox("Wlacz integracje WHOkna")
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
        wl.addRow("Uzytkownik SQL:", self.wh_user)
        wl.addRow("Haslo SQL:", self.wh_pass)

        note = QLabel(
            "WHOkna uzywa SQL Server. Zainstaluj sterownik ODBC\n"
            "i skonfiguruj polaczenie z baza danych programu WHOkna."
        )
        note.setStyleSheet("color: #6b7280; font-size: 11px;")
        wl.addRow("", note)

        test_wh_btn = QPushButton("Testuj polaczenie WHOkna")
        test_wh_btn.clicked.connect(self._test_whokna)
        wl.addRow("", test_wh_btn)
        tabs.addTab(wh_tab, "WHOkna")

        ai_tab = QWidget()
        al = QFormLayout(ai_tab)

        self.ai_provider = QComboBox()
        for p in PROVIDERS:
            self.ai_provider.addItem(p)
        self.ai_provider.currentIndexChanged.connect(self._on_ai_provider_changed)

        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_key.setPlaceholderText("sk-... / AIza... / anthropic key")
        self.ai_key.textChanged.connect(self._schedule_ai_models_refresh)

        self.ai_model = QComboBox()
        self.ai_model.setEditable(False)

        self.ai_model_hint = QLabel("")
        self.ai_model_hint.setStyleSheet("color:#6b7280;font-size:11px;")

        self.ai_model_status = QLabel("")
        self.ai_model_status.setStyleSheet("color:#6b7280;font-size:11px;")

        self.ai_model_refresh_btn = QPushButton("Odswiez modele")
        self.ai_model_refresh_btn.setObjectName("secondaryBtn")
        self.ai_model_refresh_btn.clicked.connect(self._refresh_ai_models)

        self.ai_model_refresh_timer = QTimer(self)
        self.ai_model_refresh_timer.setSingleShot(True)
        self.ai_model_refresh_timer.timeout.connect(self._refresh_ai_models)

        al.addRow("Provider:", self.ai_provider)
        al.addRow("Klucz API:", self.ai_key)
        al.addRow("Model:", self.ai_model)
        al.addRow("", self.ai_model_hint)
        al.addRow("", self.ai_model_refresh_btn)
        al.addRow("", self.ai_model_status)

        ai_note = QLabel(
            "Claude: claude-sonnet-4-6\n"
            "Gemini: gemini-2.0-flash\n"
            "OpenAI: gpt-4o-mini\n\n"
            "Klucze API nie sa wysylane nigdzie poza wybranym providerem."
        )
        ai_note.setStyleSheet("color:#6b7280;font-size:11px;")
        al.addRow("", ai_note)

        test_ai_btn = QPushButton("Testuj polaczenie AI")
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
        saved_model = ac.get("model", "")
        if saved_model:
            self.ai_model.addItem(saved_model)
            self.ai_model.setCurrentText(saved_model)
        self._update_ai_model_hint()
        self._schedule_ai_models_refresh()

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
            "model": self.ai_model.currentText().strip(),
        }
        cfg_module.save(self._cfg)
        self.accept()

    def _test_imap(self):
        import imaplib

        host = self.imap_host.text().strip()
        port = self.imap_port.value()
        ssl = self.imap_ssl.isChecked()
        user = self.email_user.text().strip()
        pwd = self.email_pass.text()
        if not host or not user:
            QMessageBox.warning(self, "Blad", "Uzupelnij host i uzytkownika.")
            return
        try:
            if ssl:
                imap = imaplib.IMAP4_SSL(host, port)
            else:
                imap = imaplib.IMAP4(host, port)
            imap.login(user, pwd)
            imap.logout()
            QMessageBox.information(self, "IMAP", "Polaczono i zalogowano pomyslnie!")
        except Exception as e:
            QMessageBox.critical(self, "Blad IMAP", str(e))

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
            QMessageBox.information(self, "WHOkna", f"Polaczono pomyslnie!\n{msg}")
        else:
            QMessageBox.critical(self, "Blad WHOkna", msg)

    def _update_ai_model_hint(self):
        provider = self.ai_provider.currentText()
        hints = {
            "Claude (Anthropic)": "domyslnie: claude-sonnet-4-6",
            "Gemini (Google)": "domyslnie: gemini-2.0-flash",
            "OpenAI": "domyslnie: gpt-4o-mini",
        }
        self.ai_model_hint.setText(hints.get(provider, ""))

    def _on_ai_provider_changed(self):
        self._ai_models_loaded_for = None
        self._update_ai_model_hint()
        self._schedule_ai_models_refresh()

    def _schedule_ai_models_refresh(self):
        self._ai_models_loaded_for = None
        self.ai_model_refresh_timer.start(700)

    def _refresh_ai_models(self):
        cfg = {
            "provider": self.ai_provider.currentText(),
            "api_key": self.ai_key.text().strip(),
        }
        current_model = self.ai_model.currentText().strip()
        cache_key = (cfg["provider"], cfg["api_key"])

        if not cfg["api_key"]:
            self.ai_model_status.setText("Wpisz klucz API, aby pobrac liste modeli.")
            return
        if self._ai_models_loaded_for == cache_key:
            return

        self.ai_model_refresh_btn.setEnabled(False)
        self.ai_model_status.setText("Pobieranie modeli...")
        try:
            models = ai_svc.list_models(cfg)
            self.ai_model.blockSignals(True)
            self.ai_model.clear()
            self.ai_model.addItems(models)
            self.ai_model.setCurrentText(current_model or (models[0] if models else ""))
            self.ai_model.blockSignals(False)
            self._ai_models_loaded_for = cache_key
            if models:
                self.ai_model_status.setText(f"Pobrano {len(models)} modeli.")
            else:
                self.ai_model_status.setText("Brak modeli do wyswietlenia dla tego klucza.")
        except Exception as e:
            self.ai_model_status.setText(f"Nie udalo sie pobrac modeli: {e}")
        finally:
            self.ai_model_refresh_btn.setEnabled(True)

    def _test_ai(self):
        cfg = {
            "provider": self.ai_provider.currentText(),
            "api_key": self.ai_key.text().strip(),
            "model": self.ai_model.currentText().strip(),
        }
        if not cfg["api_key"]:
            QMessageBox.warning(self, "Blad", "Wpisz klucz API.")
            return
        try:
            resp = ai_svc.chat(cfg, [{"role": "user", "content": "Odpowiedz jednym slowem: czesc"}])
            QMessageBox.information(self, "AI Agent", f"Polaczono!\nOdpowiedz: {resp}")
        except Exception as e:
            QMessageBox.critical(self, "Blad AI", str(e))

    def get_config(self) -> dict:
        return self._cfg
