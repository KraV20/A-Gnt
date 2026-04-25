from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCalendarWidget,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QMessageBox, QMenu,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QBrush, QFont
from datetime import date, datetime

from app.models.calendar_event import CalendarEvent, EVENT_COLORS
import app.services.calendar_service as cal_svc
import app.services.client_service as client_svc
import app.services.order_service as order_svc
from app.ui.dialogs.event_dialog import EventDialog


class CalendarPanel(QWidget):
    events_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Kalendarz")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # Stats bar
        self.stats_bar = QFrame()
        self.stats_bar.setObjectName("statsBar")
        stats_layout = QHBoxLayout(self.stats_bar)
        stats_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_today = QLabel("Dzisiaj: 0")
        self.lbl_today.setStyleSheet("color:#2563eb;font-weight:600;font-size:13px;")
        self.lbl_week = QLabel("Najbliższy tydzień: 0")
        self.lbl_week.setStyleSheet("color:#16a34a;font-weight:600;font-size:13px;")
        self.lbl_overdue = QLabel("Zaległe: 0")
        self.lbl_overdue.setStyleSheet("color:#ef4444;font-weight:600;font-size:13px;")

        stats_layout.addWidget(self.lbl_today)
        stats_layout.addWidget(self._sep())
        stats_layout.addWidget(self.lbl_week)
        stats_layout.addWidget(self._sep())
        stats_layout.addWidget(self.lbl_overdue)
        stats_layout.addStretch()

        add_btn = QPushButton("+ Nowe wydarzenie")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self._add_event)
        stats_layout.addWidget(add_btn)

        layout.addWidget(self.stats_bar)

        # Splitter: left calendar, right event list
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left – calendar widget
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.cal = QCalendarWidget()
        self.cal.setGridVisible(True)
        self.cal.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.cal.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
        self.cal.clicked.connect(self._on_date_selected)
        self.cal.currentPageChanged.connect(lambda y, m: self._highlight_month(y, m))
        left_layout.addWidget(self.cal)

        legend = QHBoxLayout()
        legend.addWidget(QLabel("Legenda:"))
        for typ, color in EVENT_COLORS.items():
            dot = QLabel(f"● {typ}")
            dot.setStyleSheet(f"color:{color};font-size:11px;")
            legend.addWidget(dot)
        legend.addStretch()
        left_layout.addLayout(legend)

        splitter.addWidget(left)

        # Right – event list for selected date
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.date_label = QLabel("")
        self.date_label.setStyleSheet("font-size:14px;font-weight:600;color:#1f2937;")
        right_layout.addWidget(self.date_label)

        self.event_list = QListWidget()
        self.event_list.setAlternatingRowColors(True)
        self.event_list.itemDoubleClicked.connect(self._on_event_double_click)
        self.event_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.event_list.customContextMenuRequested.connect(self._show_context_menu)
        right_layout.addWidget(self.event_list, 1)

        upcoming_label = QLabel("Najbliższe wydarzenia (7 dni):")
        upcoming_label.setStyleSheet("font-size:12px;color:#6b7280;margin-top:6px;")
        right_layout.addWidget(upcoming_label)

        self.upcoming_list = QListWidget()
        self.upcoming_list.setMaximumHeight(180)
        self.upcoming_list.itemDoubleClicked.connect(self._on_upcoming_double_click)
        right_layout.addWidget(self.upcoming_list)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter, 1)

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFrameShape(QFrame.Shape.VLine)
        s.setStyleSheet("color:#e5e7eb;")
        return s

    # ── Data refresh ───────────────────────────────────────────────────────
    def refresh(self):
        self._refresh_stats()
        cur = self.cal.selectedDate()
        self._highlight_month(self.cal.yearShown(), self.cal.monthShown())
        self._on_date_selected(cur)
        self._refresh_upcoming()

    def _refresh_stats(self):
        s = cal_svc.get_stats()
        self.lbl_today.setText(f"Dzisiaj: {s['today']}")
        self.lbl_week.setText(f"Najbliższy tydzień: {s['week']}")
        self.lbl_overdue.setText(f"Zaległe: {s['overdue']}")

    def _highlight_month(self, year: int, month: int):
        # Reset all formats first
        empty = QTextCharFormat()
        self.cal.setDateTextFormat(QDate(), empty)

        dates = cal_svc.get_dates_with_events(year, month)
        for date_str, count in dates.items():
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            qd = QDate(d.year, d.month, d.day)
            fmt = QTextCharFormat()
            fmt.setBackground(QBrush(QColor("#dbeafe")))
            fmt.setFontWeight(QFont.Weight.Bold)
            fmt.setToolTip(f"{count} wydarz.")
            self.cal.setDateTextFormat(qd, fmt)

        # Highlight today
        today = QDate.currentDate()
        fmt_today = QTextCharFormat()
        fmt_today.setBackground(QBrush(QColor("#fef3c7")))
        fmt_today.setFontWeight(QFont.Weight.Bold)
        existing_count = dates.get(today.toString("yyyy-MM-dd"), 0)
        if existing_count:
            fmt_today.setBackground(QBrush(QColor("#fde68a")))
        self.cal.setDateTextFormat(today, fmt_today)

    def _on_date_selected(self, qd: QDate):
        date_str = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        self.date_label.setText(f"Wydarzenia – {date_str}")
        self._populate_list(self.event_list, cal_svc.get_events_for_date(date_str))

    def _refresh_upcoming(self):
        events = cal_svc.get_upcoming(days=7, limit=20)
        self._populate_list(self.upcoming_list, events, show_date=True)

    def _populate_list(self, widget: QListWidget, events, show_date: bool = False):
        widget.clear()
        if not events:
            item = QListWidgetItem("Brak wydarzeń")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            widget.addItem(item)
            return
        for ev in events:
            text = self._format_event(ev, show_date=show_date)
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, ev.id)
            color = QColor(ev.color)
            item.setForeground(QBrush(color))
            if ev.is_done:
                f = item.font()
                f.setStrikeOut(True)
                item.setFont(f)
                item.setForeground(QBrush(QColor("#9ca3af")))
            widget.addItem(item)

    def _format_event(self, ev: CalendarEvent, show_date: bool = False) -> str:
        time_part = ev.event_time if ev.event_time else "cały dzień"
        prefix = ev.event_date + " " if show_date else ""
        loc = f" @ {ev.location}" if ev.location else ""
        client = ""
        if ev.client_id:
            c = client_svc.get_by_id(ev.client_id)
            if c:
                client = f" – {c.display_name}"
        return f"{prefix}{time_part}  •  {ev.title}{loc}{client}"

    # ── Actions ────────────────────────────────────────────────────────────
    def _add_event(self):
        qd = self.cal.selectedDate()
        date_str = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        dlg = EventDialog(default_date=date_str, parent=self)
        if dlg.exec():
            ev = dlg.get_event()
            cal_svc.create_event(ev)
            self.refresh()
            self.events_changed.emit()

    def _edit_event(self, event_id: int):
        ev = cal_svc.get_event(event_id)
        if not ev:
            return
        dlg = EventDialog(event=ev, parent=self)
        if dlg.exec():
            updated = dlg.get_event()
            cal_svc.update_event(updated)
            self.refresh()
            self.events_changed.emit()

    def _delete_event(self, event_id: int):
        reply = QMessageBox.question(
            self, "Usunąć wydarzenie?",
            "Czy na pewno chcesz usunąć to wydarzenie?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            cal_svc.delete_event(event_id)
            self.refresh()
            self.events_changed.emit()

    def _toggle_done(self, event_id: int):
        cal_svc.toggle_done(event_id)
        self.refresh()
        self.events_changed.emit()

    def _on_event_double_click(self, item: QListWidgetItem):
        ev_id = item.data(Qt.ItemDataRole.UserRole)
        if ev_id:
            self._edit_event(ev_id)

    def _on_upcoming_double_click(self, item: QListWidgetItem):
        ev_id = item.data(Qt.ItemDataRole.UserRole)
        if not ev_id:
            return
        ev = cal_svc.get_event(ev_id)
        if ev:
            try:
                d = datetime.strptime(ev.event_date, "%Y-%m-%d").date()
                self.cal.setSelectedDate(QDate(d.year, d.month, d.day))
                self._on_date_selected(self.cal.selectedDate())
            except ValueError:
                pass
            self._edit_event(ev_id)

    def _show_context_menu(self, pos):
        item = self.event_list.itemAt(pos)
        if not item:
            return
        ev_id = item.data(Qt.ItemDataRole.UserRole)
        if not ev_id:
            return
        menu = QMenu(self)
        menu.addAction("Edytuj", lambda: self._edit_event(ev_id))
        menu.addAction("Oznacz / odznacz jako zakończone", lambda: self._toggle_done(ev_id))
        menu.addSeparator()
        menu.addAction("Usuń", lambda: self._delete_event(ev_id))
        menu.exec(self.event_list.mapToGlobal(pos))
