MAIN_STYLE = """
QMainWindow, QDialog {
    background-color: #f5f5f5;
}

QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

/* Sidebar */
#sidebar {
    background-color: #1e2a3a;
    min-width: 200px;
    max-width: 200px;
}

#sidebarTitle {
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    padding: 20px 16px 8px 16px;
    border-bottom: 1px solid #2d3e52;
}

#sidebarVersion {
    color: #7a8fa6;
    font-size: 10px;
    padding: 4px 16px 16px 16px;
}

QPushButton#navBtn {
    background-color: transparent;
    color: #bdc8d4;
    border: none;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
}

QPushButton#navBtn:hover {
    background-color: #2d3e52;
    color: #ffffff;
}

QPushButton#navBtn:checked {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
}

/* Main content */
#contentArea {
    background-color: #f5f5f5;
}

#panelTitle {
    font-size: 20px;
    font-weight: bold;
    color: #1e2a3a;
    padding: 8px 0;
}

/* Tables */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    gridline-color: #f0f0f0;
    selection-background-color: #dbeafe;
    selection-color: #1e2a3a;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #f5f5f5;
}

QTableWidget::item:selected {
    background-color: #dbeafe;
    color: #1e2a3a;
}

QHeaderView::section {
    background-color: #f8f9fa;
    border: none;
    border-bottom: 2px solid #e0e0e0;
    padding: 8px;
    font-weight: bold;
    color: #4a5568;
}

/* Buttons */
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 7px 16px;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton#dangerBtn {
    background-color: #dc2626;
}

QPushButton#dangerBtn:hover {
    background-color: #b91c1c;
}

QPushButton#secondaryBtn {
    background-color: #6b7280;
}

QPushButton#secondaryBtn:hover {
    background-color: #4b5563;
}

QPushButton#successBtn {
    background-color: #16a34a;
}

QPushButton#successBtn:hover {
    background-color: #15803d;
}

/* Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 5px;
    padding: 6px 10px;
    color: #1f2937;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border-color: #2563eb;
    outline: none;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

/* Labels */
QLabel#fieldLabel {
    color: #6b7280;
    font-size: 11px;
    font-weight: bold;
}

/* Cards / group boxes */
QGroupBox {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 12px;
    background-color: #ffffff;
    padding: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    color: #374151;
    font-weight: bold;
    padding: 0 4px;
}

/* Status bar */
QStatusBar {
    background-color: #1e2a3a;
    color: #bdc8d4;
    font-size: 11px;
}

/* Splitter */
QSplitter::handle {
    background-color: #e0e0e0;
}

/* Scroll bars */
QScrollBar:vertical {
    background: #f5f5f5;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #c0c0c0;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #a0a0a0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #f3f4f6;
    padding: 7px 16px;
    border: 1px solid #e0e0e0;
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #2563eb;
    font-weight: bold;
}

/* Search bar */
#searchBar {
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 20px;
    font-size: 13px;
    min-width: 220px;
}

/* Status badge */
QLabel#statusNew { background: #dbeafe; color: #1d4ed8; border-radius: 10px; padding: 2px 8px; font-size: 11px; }
QLabel#statusDone { background: #dcfce7; color: #15803d; border-radius: 10px; padding: 2px 8px; font-size: 11px; }
QLabel#statusProgress { background: #fef9c3; color: #a16207; border-radius: 10px; padding: 2px 8px; font-size: 11px; }
QLabel#statusCancelled { background: #fee2e2; color: #b91c1c; border-radius: 10px; padding: 2px 8px; font-size: 11px; }

/* Unread badge */
#unreadBadge {
    background-color: #ef4444;
    color: white;
    border-radius: 9px;
    min-width: 18px;
    max-width: 28px;
    font-size: 10px;
    font-weight: bold;
    padding: 1px 4px;
    text-align: center;
}
"""

STATUS_COLORS = {
    "nowe": "#3b82f6",
    "w trakcie": "#f59e0b",
    "wstrzymane": "#6b7280",
    "zakończone": "#22c55e",
    "anulowane": "#ef4444",
}

PRIORITY_COLORS = {
    "niski": "#6b7280",
    "normalny": "#3b82f6",
    "wysoki": "#f59e0b",
    "pilny": "#ef4444",
}
