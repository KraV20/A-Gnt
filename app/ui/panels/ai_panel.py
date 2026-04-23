from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QLineEdit, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
import app.services.ai_service as ai_svc


class ChatWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, cfg: dict, messages: list):
        super().__init__()
        self.cfg = cfg
        self.messages = messages

    def run(self):
        response = ai_svc.chat(self.cfg, self.messages)
        self.finished.emit(response)


class MessageBubble(QLabel):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if is_user:
            self.setStyleSheet(
                "background:#2563eb;color:white;border-radius:12px;"
                "padding:10px 14px;font-size:13px;margin:2px 40px 2px 80px;"
            )
        else:
            self.setStyleSheet(
                "background:#ffffff;color:#1f2937;border:1px solid #e0e0e0;"
                "border-radius:12px;padding:10px 14px;font-size:13px;"
                "margin:2px 80px 2px 40px;"
            )


class AiPanel(QWidget):
    def __init__(self, app_config: dict, parent=None):
        super().__init__(parent)
        self.cfg = app_config
        self._messages = []
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("AI Agent")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self.provider_label = QLabel("")
        self.provider_label.setStyleSheet("color:#6b7280;font-size:11px;")
        header.addWidget(self.provider_label)

        clear_btn = QPushButton("Wyczyść czat")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.clicked.connect(self._clear_chat)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._update_provider_label()

        # Quick actions
        quick = QHBoxLayout()
        for label, prompt in [
            ("Zaległe zlecenia", "Które zlecenia są po terminie realizacji lub mają status 'nowe' od dawna?"),
            ("Statystyki", "Podaj mi podsumowanie: ile mamy klientów, ile zleceń w każdym statusie i ile nieprzeczytanych maili."),
            ("Nieprzeczytane maile", "Pokaż mi listę nieprzeczytanych maili."),
        ]:
            btn = QPushButton(label)
            btn.setObjectName("secondaryBtn")
            btn.clicked.connect(lambda _, p=prompt: self._send(p))
            quick.addWidget(btn)
        quick.addStretch()
        layout.addLayout(quick)

        # Chat area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background:#f5f5f5;")

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background:#f5f5f5;")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_widget)
        layout.addWidget(self.scroll)

        # Input area
        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Zapytaj agenta... np. 'jakie mam zlecenia na ten tydzień?'")
        self.input.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input)
        self.send_btn = QPushButton("Wyślij")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color:#6b7280;font-size:11px;")
        layout.addWidget(self.status_label)

        # Welcome message
        self._add_bubble(
            "Cześć! Jestem Twoim asystentem AI. Mogę sprawdzić zlecenia, klientów, "
            "maile i pomóc w zarządzaniu firmą. O co chcesz zapytać?",
            is_user=False,
        )

    def _update_provider_label(self):
        ai_cfg = self.cfg.get("ai", {})
        provider = ai_cfg.get("provider", "—")
        configured = bool(ai_cfg.get("api_key", ""))
        status = "✓ skonfigurowany" if configured else "⚠ brak klucza API"
        self.provider_label.setText(f"{provider}  |  {status}")

    def _add_bubble(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        )

    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._send(text)

    def _send(self, text: str):
        if self._worker and self._worker.isRunning():
            return
        self._add_bubble(text, is_user=True)
        self._messages.append({"role": "user", "content": text})

        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self.status_label.setText("Agent myśli...")

        ai_cfg = self.cfg.get("ai", {})
        self._worker = ChatWorker(ai_cfg, list(self._messages))
        self._worker.finished.connect(self._on_response)
        self._worker.start()

    def _on_response(self, response: str):
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.status_label.setText("")
        self._messages.append({"role": "assistant", "content": response})
        self._add_bubble(response, is_user=False)

    def _clear_chat(self):
        self._messages.clear()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._add_bubble(
            "Czat wyczyszczony. O co chcesz zapytać?",
            is_user=False,
        )

    def refresh(self, cfg: dict = None):
        if cfg:
            self.cfg = cfg
        self._update_provider_label()
