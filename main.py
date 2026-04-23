#!/usr/bin/env python3
"""A-Gnt – desktop application for email, clients, orders, documents and WHOkna."""
import sys
import os

# Ensure app package is importable when run from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.config import APP_VERSION
from app.database.connection import init_db
from app.ui.main_window import MainWindow


def main():
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    app = QApplication(sys.argv)
    app.setApplicationName("A-Gnt")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("A-Gnt")

    init_db()

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
