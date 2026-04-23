import subprocess
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QHeaderView, QAbstractItemView,
    QComboBox, QFileDialog, QMessageBox, QMenu, QGroupBox, QFormLayout,
    QTextEdit,
)
from PyQt6.QtCore import Qt, QPoint
import app.services.document_service as doc_svc
import app.services.client_service as client_svc
import app.services.order_service as order_svc
from app.models.document import Document, DOC_CATEGORIES


class DocumentsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._documents = []
        self._setup_ui()
        self._load_documents()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Dokumenty")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("Szukaj dokumentu...")
        self.search_input.textChanged.connect(self._load_documents)
        header.addWidget(self.search_input)

        self.cat_filter = QComboBox()
        self.cat_filter.addItem("Wszystkie kategorie", "")
        for cat in DOC_CATEGORIES:
            self.cat_filter.addItem(cat.capitalize(), cat)
        self.cat_filter.currentIndexChanged.connect(self._load_documents)
        header.addWidget(self.cat_filter)

        self.client_filter = QComboBox()
        self.client_filter.setMinimumWidth(150)
        self._populate_client_filter()
        self.client_filter.currentIndexChanged.connect(self._load_documents)
        header.addWidget(self.client_filter)

        add_btn = QPushButton("+ Dodaj dokument")
        add_btn.clicked.connect(self._add_document)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nazwa pliku", "Kategoria", "Klient", "Zlecenie", "Rozmiar", "Data"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._open_file)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.count_label)

    def _populate_client_filter(self):
        self.client_filter.clear()
        self.client_filter.addItem("Wszyscy klienci", None)
        for c in client_svc.get_all():
            self.client_filter.addItem(c.display_name, c.id)

    def _load_documents(self, *_):
        query = self.search_input.text().strip()
        category = self.cat_filter.currentData() or None
        client_id = self.client_filter.currentData()

        if query:
            docs = doc_svc.search(query)
        else:
            docs = doc_svc.get_all(client_id=client_id, category=category)

        self._documents = docs
        self.table.setRowCount(len(docs))
        for row, d in enumerate(docs):
            self.table.setItem(row, 0, QTableWidgetItem(d.filename))
            self.table.setItem(row, 1, QTableWidgetItem(d.category))
            self.table.setItem(row, 2, QTableWidgetItem(d.client_name or ""))
            self.table.setItem(row, 3, QTableWidgetItem(d.order_number or ""))
            self.table.setItem(row, 4, QTableWidgetItem(d.size_display))
            self.table.setItem(row, 5, QTableWidgetItem(d.created_at[:10]))
        self.count_label.setText(f"Dokumentów: {len(docs)}")

    def _add_document(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Wybierz dokumenty")
        if not paths:
            return
        dlg = AddDocumentDialog(paths, self)
        if dlg.exec():
            self._load_documents()

    def _open_file(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._documents):
            return
        doc = self._documents[row]
        p = Path(doc.filepath)
        if not p.exists():
            QMessageBox.warning(self, "Błąd", f"Plik nie istnieje:\n{doc.filepath}")
            return
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", str(p)])
        elif sys.platform == "win32":
            import os
            os.startfile(str(p))
        else:
            subprocess.Popen(["open", str(p)])

    def _context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0 or row >= len(self._documents):
            return
        doc = self._documents[row]
        menu = QMenu(self)
        menu.addAction("Otwórz", self._open_file)
        menu.addAction("Pokaż w folderze", lambda: self._show_in_folder(doc))
        menu.addSeparator()
        menu.addAction("Usuń", lambda: self._delete_doc(doc))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _show_in_folder(self, doc: Document):
        p = Path(doc.filepath).parent
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", str(p)])
        elif sys.platform == "win32":
            import os
            os.startfile(str(p))
        else:
            subprocess.Popen(["open", str(p)])

    def _delete_doc(self, doc: Document):
        reply = QMessageBox.question(
            self, "Usuń dokument",
            f"Usunąć '{doc.filename}'?\nPlik zostanie usunięty z dysku.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            doc_svc.delete(doc.id)
            self._load_documents()

    def refresh(self):
        self._populate_client_filter()
        self._load_documents()


class AddDocumentDialog(QWidget):
    def __init__(self, paths: list, parent=None):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        super().__init__(parent)

    def exec(self):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QLabel
        from PyQt6.QtCore import Qt
        dlg = _AddDocDialog(getattr(self, '_paths', []), self.parent())
        return dlg.exec()


class _AddDocDialog:
    def __init__(self, paths, parent):
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, QComboBox, QLineEdit
        self._paths = paths
        self._parent = parent

        self.dlg = QDialog(parent)
        self.dlg.setWindowTitle("Dodaj dokumenty")
        self.dlg.setMinimumWidth(400)
        layout = QVBoxLayout(self.dlg)

        form = QFormLayout()
        self.cat_combo = QComboBox()
        for cat in DOC_CATEGORIES:
            self.cat_combo.addItem(cat.capitalize(), cat)

        self.client_combo = QComboBox()
        self.client_combo.addItem("— brak —", None)
        for c in client_svc.get_all():
            self.client_combo.addItem(c.display_name, c.id)

        self.order_combo = QComboBox()
        self.order_combo.addItem("— brak —", None)
        for o in order_svc.get_all():
            self.order_combo.addItem(f"{o.number} – {o.title}", o.id)

        self.desc_edit = QLineEdit()
        form.addRow("Kategoria", self.cat_combo)
        form.addRow("Klient", self.client_combo)
        form.addRow("Zlecenie", self.order_combo)
        form.addRow("Opis", self.desc_edit)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.dlg.reject)
        layout.addWidget(btns)

    def _accept(self):
        cat = self.cat_combo.currentData()
        client_id = self.client_combo.currentData()
        order_id = self.order_combo.currentData()
        desc = self.desc_edit.text().strip()
        for path in self._paths:
            p = Path(path)
            doc_svc.add_file(path, p.name, cat, client_id, order_id, desc)
        self.dlg.accept()

    def exec(self):
        return self.dlg.exec()
