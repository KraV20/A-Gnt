from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QLabel, QDateEdit, QTimeEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import QDate, QTime, Qt
from datetime import datetime

from app.models.calendar_event import (
    CalendarEvent, EVENT_TYPES, REMINDER_OPTIONS,
)
import app.services.client_service as client_svc
import app.services.order_service as order_svc


class EventDialog(QDialog):
    def __init__(self, event: CalendarEvent = None, default_date: str = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wydarzenie" if event and event.id else "Nowe wydarzenie")
        self.setMinimumWidth(480)
        self._event = event or CalendarEvent()
        if default_date and not self._event.event_date:
            self._event.event_date = default_date
        self._setup_ui()
        self._load_event()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Tytuł wydarzenia")
        form.addRow("Tytuł*:", self.title_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(EVENT_TYPES)
        form.addRow("Typ:", self.type_combo)

        date_row = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        date_row.addWidget(self.date_edit)

        self.all_day_cb = QCheckBox("Cały dzień")
        self.all_day_cb.toggled.connect(self._on_all_day)
        date_row.addWidget(self.all_day_cb)
        form.addRow("Data*:", date_row)

        time_row = QHBoxLayout()
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(QTime(9, 0))
        time_row.addWidget(self.time_edit)
        time_row.addWidget(QLabel("Czas trwania (min):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 1440)
        self.duration_spin.setSingleStep(15)
        self.duration_spin.setValue(60)
        time_row.addWidget(self.duration_spin)
        form.addRow("Godzina:", time_row)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("np. siedziba klienta, biuro")
        form.addRow("Lokalizacja:", self.location_edit)

        self.client_combo = QComboBox()
        self.client_combo.addItem("— brak —", None)
        for c in client_svc.get_all():
            self.client_combo.addItem(c.display_name, c.id)
        form.addRow("Klient:", self.client_combo)

        self.order_combo = QComboBox()
        self.order_combo.addItem("— brak —", None)
        for o in order_svc.get_all():
            self.order_combo.addItem(f"{o.number} – {o.title}", o.id)
        form.addRow("Zlecenie:", self.order_combo)

        self.reminder_combo = QComboBox()
        for label, mins in REMINDER_OPTIONS:
            self.reminder_combo.addItem(label, mins)
        form.addRow("Przypomnienie:", self.reminder_combo)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("Notatki, agenda, szczegóły...")
        form.addRow("Opis:", self.desc_edit)

        self.done_cb = QCheckBox("Wydarzenie zakończone")
        form.addRow("", self.done_cb)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_all_day(self, checked: bool):
        self.time_edit.setEnabled(not checked)
        self.duration_spin.setEnabled(not checked)

    def _load_event(self):
        ev = self._event
        self.title_edit.setText(ev.title)
        if ev.event_type in EVENT_TYPES:
            self.type_combo.setCurrentText(ev.event_type)
        if ev.event_date:
            try:
                d = datetime.strptime(ev.event_date, "%Y-%m-%d").date()
                self.date_edit.setDate(QDate(d.year, d.month, d.day))
            except ValueError:
                pass
        if ev.event_time:
            try:
                t = datetime.strptime(ev.event_time, "%H:%M").time()
                self.time_edit.setTime(QTime(t.hour, t.minute))
            except ValueError:
                pass
        else:
            if ev.id:
                self.all_day_cb.setChecked(True)
        self.duration_spin.setValue(ev.duration_min)
        self.location_edit.setText(ev.location)
        if ev.client_id:
            idx = self.client_combo.findData(ev.client_id)
            if idx >= 0:
                self.client_combo.setCurrentIndex(idx)
        if ev.order_id:
            idx = self.order_combo.findData(ev.order_id)
            if idx >= 0:
                self.order_combo.setCurrentIndex(idx)
        idx = self.reminder_combo.findData(ev.reminder_min)
        if idx >= 0:
            self.reminder_combo.setCurrentIndex(idx)
        self.desc_edit.setPlainText(ev.description)
        self.done_cb.setChecked(ev.is_done)

    def _on_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            self.title_edit.setFocus()
            return
        self.accept()

    def get_event(self) -> CalendarEvent:
        ev = self._event
        ev.title = self.title_edit.text().strip()
        ev.event_type = self.type_combo.currentText()
        qd = self.date_edit.date()
        ev.event_date = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        if self.all_day_cb.isChecked():
            ev.event_time = None
        else:
            qt = self.time_edit.time()
            ev.event_time = f"{qt.hour():02d}:{qt.minute():02d}"
        ev.duration_min = self.duration_spin.value()
        ev.location = self.location_edit.text().strip()
        ev.client_id = self.client_combo.currentData()
        ev.order_id = self.order_combo.currentData()
        ev.reminder_min = self.reminder_combo.currentData() or 0
        ev.description = self.desc_edit.toPlainText().strip()
        ev.is_done = self.done_cb.isChecked()
        return ev
