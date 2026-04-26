from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QComboBox, QPushButton,
    QDialogButtonBox, QGroupBox, QMessageBox,
)
from app.services.ai_service import PROVIDERS
from PyQt6.QtCore import Qt
import app.config as cfg_module
import app.services.whokna_service as whokna_svc
import app.services.sync_service as sync_svc


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
        self.show_pass_cb = QCheckBox("Pokaż hasło")
        self.show_pass_cb.toggled.connect(
            lambda c: self.email_pass.setEchoMode(
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
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
        el.addRow("", self.show_pass_cb)
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

        # --- Synchronizacja tab ---
        sync_tab = QWidget()
        sl = QFormLayout(sync_tab)

        self.sync_enabled = QCheckBox("Włącz synchronizację przez internet")
        sl.addRow("", self.sync_enabled)

        self.sync_url = QLineEdit()
        self.sync_url.setPlaceholderText("http://twoj-serwer:8000")
        sl.addRow("URL serwera:", self.sync_url)

        self.sync_key = QLineEdit()
        self.sync_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.sync_key.setPlaceholderText("Tajny klucz API (min. 20 znaków)")
        self.sync_show_key = QCheckBox("Pokaż klucz")
        self.sync_show_key.toggled.connect(
            lambda c: self.sync_key.setEchoMode(
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
        sl.addRow("Klucz API:", self.sync_key)
        sl.addRow("", self.sync_show_key)

        self.sync_interval = QSpinBox()
        self.sync_interval.setRange(0, 60)
        self.sync_interval.setSuffix(" min")
        self.sync_interval.setSpecialValueText("ręcznie")
        sl.addRow("Auto-sync co:", self.sync_interval)

        self.sync_device_id = QLineEdit()
        self.sync_device_id.setReadOnly(True)
        self.sync_device_id.setStyleSheet("color:#6b7280;font-size:10px;")
        sl.addRow("ID urządzenia:", self.sync_device_id)

        sync_note = QLabel(
            "Serwer sync możesz uruchomić samodzielnie za pomocą Docker:\n"
            "  cd sync_server && cp .env.example .env\n"
            "  (edytuj .env – ustaw API_KEY)\n"
            "  docker-compose up -d\n\n"
            "Wszystkie komputery muszą mieć ten sam URL i klucz API."
        )
        sync_note.setStyleSheet("color:#6b7280;font-size:11px;font-family:Consolas,monospace;")
        sl.addRow("", sync_note)

        test_sync_btn = QPushButton("Testuj połączenie")
        test_sync_btn.clicked.connect(self._test_sync)
        sl.addRow("", test_sync_btn)

        tabs.addTab(sync_tab, "Synchronizacja")
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

        sc = self._cfg.get("sync", {})
        self.sync_enabled.setChecked(sc.get("enabled", False))
        self.sync_url.setText(sc.get("server_url", ""))
        self.sync_key.setText(sc.get("api_key", ""))
        self.sync_interval.setValue(sc.get("auto_sync_minutes", 5))
        self.sync_device_id.setText(sc.get("device_id", "(zostanie nadane przy pierwszym sync)"))

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
        self._cfg["sync"] = {
            "enabled":           self.sync_enabled.isChecked(),
            "server_url":        self.sync_url.text().strip().rstrip("/"),
            "api_key":           self.sync_key.text().strip(),
            "device_id":         self._cfg.get("sync", {}).get("device_id", ""),
            "auto_sync_minutes": self.sync_interval.value(),
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
            QMessageBox.critical(self, "Błąd IMAP", msg + self._imap_hint(host, msg, user))

    def _imap_hint(self, host: str, error_msg: str, user: str) -> str:
        h = host.lower()
        low = error_msg.lower()
        is_auth = (
            "authenticationfailed" in low
            or "błędne dane" in low
            or "authentication fail" in low
            or "invalid credentials" in low
        )

        if "gmail.com" in h or "googlemail" in h:
            return (
                "\n\n→ Gmail wymaga **hasła aplikacji**:\n"
                "1. Włącz 2FA na koncie Google\n"
                "2. Wejdź: myaccount.google.com → Bezpieczeństwo → Hasła do aplikacji\n"
                "3. Wygeneruj 16-znakowe hasło i wpisz je TUTAJ (zamiast normalnego hasła)\n"
                "4. Włącz IMAP w ustawieniach Gmaila"
            )
        if "outlook" in h or "office365" in h or "hotmail" in h or "live.com" in h:
            return (
                "\n\n→ Outlook / Office 365 wymaga **hasła aplikacji** lub OAuth2:\n"
                "1. Włącz 2FA: account.microsoft.com → Zabezpieczenia\n"
                "2. Utwórz hasło aplikacji i wpisz je TUTAJ\n"
                "3. Sprawdź czy IMAP jest włączony w portal.office.com"
            )
        if "wp.pl" in h or "o2.pl" in h or "interia.pl" in h:
            hint = "\n\n→ Polskie portale (wp/o2/interia):\n"
            if "@" in user:
                hint += "• SPRÓBUJ loginu BEZ @domena (sam nick)\n"
            hint += (
                "• Włącz IMAP w ustawieniach poczty na stronie portalu\n"
                "• wp.pl często wymaga osobnego hasła do aplikacji POP3/IMAP"
            )
            return hint
        if "icloud" in h or "me.com" in h:
            return (
                "\n\n→ iCloud wymaga **hasła specyficznego dla aplikacji**:\n"
                "1. appleid.apple.com → Logowanie i bezpieczeństwo\n"
                "2. Hasła specyficzne dla aplikacji → Wygeneruj"
            )

        if is_auth:
            return (
                "\n\nSerwer odrzucił hasło. Sprawdź:\n"
                "• Czy hasło nie ma spacji na końcu / początku\n"
                "• Czy CapsLock jest wyłączony (zaznacz Pokaż hasło)\n"
                "• Czy konto nie wymaga hasła aplikacji (Gmail/Outlook/iCloud)\n"
                "• Czy login jest w pełnej formie (np. user@domena.pl)"
            )
        return (
            "\n\nMożliwe przyczyny:\n"
            "• Złe hasło lub login\n"
            "• Serwer wymaga hasła aplikacji (Gmail/Outlook/iCloud)\n"
            "• IMAP jest wyłączony na koncie"
        )

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

    def _test_sync(self):
        url = self.sync_url.text().strip().rstrip("/")
        key = self.sync_key.text().strip()
        if not url or not key:
            QMessageBox.warning(self, "Brak danych", "Uzupełnij URL serwera i klucz API.")
            return
        ok, msg = sync_svc.test_connection(url, key)
        if ok:
            QMessageBox.information(self, "Synchronizacja", msg)
        else:
            QMessageBox.critical(self, "Błąd synchronizacji", msg)

    def get_config(self) -> dict:
        return self._cfg
