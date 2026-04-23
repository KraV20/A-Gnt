import subprocess
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel,
    QGroupBox, QFormLayout, QSpinBox, QComboBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QFileDialog,
    QMessageBox, QProgressBar, QTextEdit,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import app.services.pricing_service as pricing_svc
from app.models.pricing import (
    SmartSlideConfig, CONFIGURATIONS, GLASS_TYPES,
    COLORS, THRESHOLDS, HARDWARE,
)


class TrainWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, filenames):
        super().__init__()
        self.filenames = filenames

    def run(self):
        try:
            meta = pricing_svc.train(self.filenames)
            self.finished.emit(meta)
        except Exception as e:
            self.error.emit(str(e))


class PricingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)

        title = QLabel("Kalkulator – Smart-Slide")
        title.setObjectName("panelTitle")
        title.setContentsMargins(0, 0, 0, 10)
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_calculator_tab(), "Kalkulator")
        tabs.addTab(self._build_datasets_tab(), "Datasety")
        tabs.addTab(self._build_model_tab(), "Model ML")
        layout.addWidget(tabs)

    # ── Calculator tab ────────────────────────────────────────────────────────

    def _build_calculator_tab(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # Left: parameters
        left = QGroupBox("Parametry okna Smart-Slide")
        form = QFormLayout(left)
        form.setSpacing(8)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(1000, 8000)
        self.width_spin.setValue(2000)
        self.width_spin.setSuffix(" mm")
        self.width_spin.setSingleStep(100)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(1500, 3200)
        self.height_spin.setValue(2200)
        self.height_spin.setSuffix(" mm")
        self.height_spin.setSingleStep(50)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 99)
        self.qty_spin.setValue(1)
        self.qty_spin.setSuffix(" szt.")

        self.config_combo = QComboBox()
        self.config_combo.addItems(CONFIGURATIONS)

        self.glass_combo = QComboBox()
        self.glass_combo.addItems(GLASS_TYPES)
        self.glass_combo.setCurrentText("niskoemisyjne")

        self.color_combo = QComboBox()
        self.color_combo.addItems(COLORS)

        self.threshold_combo = QComboBox()
        self.threshold_combo.addItems(THRESHOLDS)

        self.hardware_combo = QComboBox()
        self.hardware_combo.addItems(HARDWARE)

        self.mosquito_cb = QCheckBox("Siatka przeciwko owadom")
        self.install_cb = QCheckBox("Montaż (+12% netto)")

        self.ml_cb = QCheckBox("Używaj modelu ML (jeśli wytrenowany)")
        self.ml_cb.setChecked(True)

        form.addRow("Szerokość:", self.width_spin)
        form.addRow("Wysokość:", self.height_spin)
        form.addRow("Ilość:", self.qty_spin)
        form.addRow("Konfiguracja:", self.config_combo)
        form.addRow("Szkło:", self.glass_combo)
        form.addRow("Kolor:", self.color_combo)
        form.addRow("Próg:", self.threshold_combo)
        form.addRow("Okucia:", self.hardware_combo)
        form.addRow("", self.mosquito_cb)
        form.addRow("", self.install_cb)
        form.addRow("", self.ml_cb)

        calc_btn = QPushButton("Oblicz cenę")
        calc_btn.clicked.connect(self._calculate)
        form.addRow("", calc_btn)
        layout.addWidget(left)

        # Right: result
        right = QVBoxLayout()

        self.result_box = QGroupBox("Wynik wyceny")
        result_layout = QVBoxLayout(self.result_box)

        self.source_label = QLabel("")
        self.source_label.setStyleSheet("font-size:11px;color:#6b7280;")
        result_layout.addWidget(self.source_label)

        self.area_label = QLabel("")
        self.area_label.setStyleSheet("color:#374151;")
        result_layout.addWidget(self.area_label)

        self.net_label = QLabel("— PLN netto")
        font = QFont()
        font.setPointSize(22)
        font.setBold(True)
        self.net_label.setFont(font)
        self.net_label.setStyleSheet("color:#2563eb;")
        result_layout.addWidget(self.net_label)

        self.vat_label = QLabel("")
        self.vat_label.setStyleSheet("color:#6b7280;font-size:12px;")
        result_layout.addWidget(self.vat_label)

        self.gross_label = QLabel("")
        gfont = QFont()
        gfont.setPointSize(14)
        gfont.setBold(True)
        self.gross_label.setFont(gfont)
        self.gross_label.setStyleSheet("color:#16a34a;")
        result_layout.addWidget(self.gross_label)

        result_layout.addSpacing(8)
        breakdown_lbl = QLabel("Rozbicie ceny:")
        breakdown_lbl.setStyleSheet("font-weight:bold;color:#374151;")
        result_layout.addWidget(breakdown_lbl)

        self.breakdown_table = QTableWidget()
        self.breakdown_table.setColumnCount(2)
        self.breakdown_table.setHorizontalHeaderLabels(["Pozycja", "Kwota (PLN)"])
        self.breakdown_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.breakdown_table.verticalHeader().setVisible(False)
        self.breakdown_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.breakdown_table.setMaximumHeight(200)
        result_layout.addWidget(self.breakdown_table)

        right.addWidget(self.result_box)
        right.addStretch()
        layout.addLayout(right)
        return w

    def _calculate(self):
        cfg = SmartSlideConfig(
            width_mm=self.width_spin.value(),
            height_mm=self.height_spin.value(),
            configuration=self.config_combo.currentText(),
            glass_type=self.glass_combo.currentText(),
            color=self.color_combo.currentText(),
            threshold=self.threshold_combo.currentText(),
            hardware=self.hardware_combo.currentText(),
            mosquito_net=self.mosquito_cb.isChecked(),
            installation=self.install_cb.isChecked(),
            quantity=self.qty_spin.value(),
        )
        result = pricing_svc.calculate(cfg, prefer_ml=self.ml_cb.isChecked())

        self.area_label.setText(f"Powierzchnia: {cfg.area_m2:.2f} m²  ×  {cfg.quantity} szt.")
        self.net_label.setText(f"{result.net_price:,.2f} PLN netto")
        self.vat_label.setText(f"VAT 23%: {result.vat_amount:,.2f} PLN")
        self.gross_label.setText(f"{result.gross_price:,.2f} PLN brutto")

        src = "Model ML" if result.source == "ml" else "Cennik reguł"
        conf = f" – pewność: {result.ml_confidence}" if result.ml_confidence else ""
        self.source_label.setText(f"Źródło: {src}{conf}")

        items = list(result.breakdown.items())
        self.breakdown_table.setRowCount(len(items))
        for row, (name, val) in enumerate(items):
            self.breakdown_table.setItem(row, 0, QTableWidgetItem(name))
            amt = QTableWidgetItem(f"{val:,.2f}" if isinstance(val, float) else str(val))
            amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.breakdown_table.setItem(row, 1, amt)

    # ── Datasets tab ─────────────────────────────────────────────────────────

    def _build_datasets_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        btn_row = QHBoxLayout()
        upload_btn = QPushButton("+ Wgraj dataset (CSV / XLSX)")
        upload_btn.clicked.connect(self._upload_dataset)
        btn_row.addWidget(upload_btn)

        pdf_btn = QPushButton("+ Wgraj cennik PDF")
        pdf_btn.clicked.connect(self._upload_pdf_dataset)
        btn_row.addWidget(pdf_btn)

        sample_btn = QPushButton("Generuj przykładowy dataset")
        sample_btn.setObjectName("secondaryBtn")
        sample_btn.clicked.connect(self._generate_sample)
        btn_row.addWidget(sample_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        info = QLabel(
            "Dataset musi zawierać kolumny: width_mm, height_mm, configuration, glass_type, "
            "color, threshold, hardware, mosquito_net, installation, price_net.\n"
            "Możesz też wgrać PDF z tabelą — system spróbuje automatycznie wyodrębnić rekordy."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#6b7280;font-size:11px;")
        layout.addWidget(info)

        self.dataset_table = QTableWidget()
        self.dataset_table.setColumnCount(3)
        self.dataset_table.setHorizontalHeaderLabels(["Plik", "Rozmiar", ""])
        self.dataset_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dataset_table.verticalHeader().setVisible(False)
        self.dataset_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.dataset_table)

        self.preview_box = QGroupBox("Podgląd")
        preview_layout = QVBoxLayout(self.preview_box)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setMaximumHeight(180)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(self.preview_box)

        self._refresh_datasets()
        return w

    def _refresh_datasets(self):
        datasets = pricing_svc.list_datasets()
        self.dataset_table.setRowCount(len(datasets))
        for row, p in enumerate(datasets):
            self.dataset_table.setItem(row, 0, QTableWidgetItem(p.name))
            size = f"{p.stat().st_size / 1024:.1f} KB"
            self.dataset_table.setItem(row, 1, QTableWidgetItem(size))
            del_btn = QPushButton("Usuń")
            del_btn.setObjectName("dangerBtn")
            del_btn.clicked.connect(lambda _, n=p.name: self._delete_dataset(n))
            self.dataset_table.setCellWidget(row, 2, del_btn)
        self.dataset_table.itemSelectionChanged.connect(self._preview_selected)

    def _upload_dataset(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Wybierz dataset", "", "CSV / Excel (*.csv *.xlsx *.xls)"
        )
        for path in paths:
            p = Path(path)
            pricing_svc.save_dataset(path, p.name)
        self._refresh_datasets()

    def _upload_pdf_dataset(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Wybierz cennik PDF", "", "PDF (*.pdf)"
        )
        if not paths:
            return
        converted = []
        failed = []
        for path in paths:
            p = Path(path)
            try:
                out, rows = pricing_svc.import_pdf_to_dataset(path, f"{p.stem}_from_pdf.csv")
                converted.append(f"{out.name} ({rows} rekordów)")
            except Exception as e:
                failed.append(f"{p.name}: {e}")

        self._refresh_datasets()
        msg = ""
        if converted:
            msg += "Przekonwertowano:\n- " + "\n- ".join(converted)
        if failed:
            if msg:
                msg += "\n\n"
            msg += "Błędy:\n- " + "\n- ".join(failed)
        if failed and not converted:
            QMessageBox.warning(self, "Import PDF", msg)
        else:
            QMessageBox.information(self, "Import PDF", msg or "Brak danych do importu.")

    def _generate_sample(self):
        dest = pricing_svc.generate_sample_dataset()
        QMessageBox.information(self, "Wygenerowano", f"Zapisano: {dest.name}\n200 przykładowych wierszy.")
        self._refresh_datasets()

    def _delete_dataset(self, name: str):
        if QMessageBox.question(self, "Usuń", f"Usunąć '{name}'?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) == QMessageBox.StandardButton.Yes:
            pricing_svc.delete_dataset(name)
            self._refresh_datasets()

    def _preview_selected(self):
        row = self.dataset_table.currentRow()
        datasets = pricing_svc.list_datasets()
        if row < 0 or row >= len(datasets):
            return
        try:
            cols, rows = pricing_svc.load_dataset_preview(datasets[row].name)
            self.preview_table.setColumnCount(len(cols))
            self.preview_table.setHorizontalHeaderLabels(cols)
            self.preview_table.setRowCount(len(rows))
            for r, row_data in enumerate(rows):
                for c, val in enumerate(row_data):
                    self.preview_table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ""))
        except Exception as e:
            QMessageBox.warning(self, "Błąd podglądu", str(e))

    # ── Model tab ─────────────────────────────────────────────────────────────

    def _build_model_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Model status
        self.model_status_box = QGroupBox("Status modelu")
        sl = QVBoxLayout(self.model_status_box)
        self.model_status_lbl = QLabel("Brak wytrenowanego modelu")
        self.model_status_lbl.setStyleSheet("font-size:13px;color:#6b7280;")
        sl.addWidget(self.model_status_lbl)
        self.model_detail_lbl = QLabel("")
        self.model_detail_lbl.setStyleSheet("font-size:11px;color:#374151;")
        self.model_detail_lbl.setWordWrap(True)
        sl.addWidget(self.model_detail_lbl)
        layout.addWidget(self.model_status_box)
        self._refresh_model_status()

        # Dataset selection for training
        sel_box = QGroupBox("Wybierz datasety do treningu")
        sel_layout = QVBoxLayout(sel_box)
        self.train_dataset_table = QTableWidget()
        self.train_dataset_table.setColumnCount(2)
        self.train_dataset_table.setHorizontalHeaderLabels(["Plik", "Zaznacz"])
        self.train_dataset_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.train_dataset_table.verticalHeader().setVisible(False)
        self.train_dataset_table.setMaximumHeight(150)
        sel_layout.addWidget(self.train_dataset_table)
        layout.addWidget(sel_box)
        self._refresh_train_list()

        # Train button + progress
        self.train_btn = QPushButton("Trenuj model ML")
        self.train_btn.setObjectName("successBtn")
        self.train_btn.clicked.connect(self._train)
        layout.addWidget(self.train_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.train_log = QTextEdit()
        self.train_log.setReadOnly(True)
        self.train_log.setMaximumHeight(120)
        self.train_log.setPlaceholderText("Log treningu...")
        layout.addWidget(self.train_log)

        # Feature importance
        self.importance_box = QGroupBox("Ważność cech (ostatni model)")
        imp_layout = QVBoxLayout(self.importance_box)
        self.importance_table = QTableWidget()
        self.importance_table.setColumnCount(2)
        self.importance_table.setHorizontalHeaderLabels(["Cecha", "Ważność (%)"])
        self.importance_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.importance_table.verticalHeader().setVisible(False)
        self.importance_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        imp_layout.addWidget(self.importance_table)
        layout.addWidget(self.importance_box)

        del_btn = QPushButton("Usuń model")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self._delete_model)
        layout.addWidget(del_btn)
        layout.addStretch()

        self._refresh_importances()
        return w

    def _refresh_model_status(self):
        meta = pricing_svc.get_model_meta()
        if meta:
            r2 = meta.get("r2", 0)
            color = "#16a34a" if r2 > 0.90 else "#f59e0b" if r2 > 0.75 else "#dc2626"
            self.model_status_lbl.setText(f"Model aktywny  |  R² = {r2:.3f}")
            self.model_status_lbl.setStyleSheet(f"font-size:14px;font-weight:bold;color:{color};")
            self.model_detail_lbl.setText(
                f"Próbki: {meta.get('samples')}  |  "
                f"Datasety: {', '.join(meta.get('datasets', []))}  |  "
                f"Odch. std R²: ±{meta.get('r2_std', 0):.3f}"
            )
        else:
            self.model_status_lbl.setText("Brak wytrenowanego modelu – używane są reguły cennikowe")
            self.model_status_lbl.setStyleSheet("font-size:13px;color:#6b7280;")
            self.model_detail_lbl.setText("")

    def _refresh_train_list(self):
        datasets = pricing_svc.list_datasets()
        self.train_dataset_table.setRowCount(len(datasets))
        for row, p in enumerate(datasets):
            self.train_dataset_table.setItem(row, 0, QTableWidgetItem(p.name))
            cb = QCheckBox()
            cb.setChecked(True)
            self.train_dataset_table.setCellWidget(row, 1, cb)

    def _refresh_importances(self):
        meta = pricing_svc.get_model_meta()
        if not meta or "importances" not in meta:
            self.importance_table.setRowCount(0)
            return
        imp = sorted(meta["importances"].items(), key=lambda x: x[1], reverse=True)
        self.importance_table.setRowCount(len(imp))
        for row, (feat, val) in enumerate(imp):
            self.importance_table.setItem(row, 0, QTableWidgetItem(feat))
            pct = QTableWidgetItem(f"{val * 100:.1f}%")
            pct.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if val > 0.3:
                pct.setForeground(QColor("#16a34a"))
            self.importance_table.setItem(row, 1, pct)

    def _train(self):
        datasets = pricing_svc.list_datasets()
        selected = []
        for row in range(self.train_dataset_table.rowCount()):
            cb = self.train_dataset_table.cellWidget(row, 1)
            if cb and cb.isChecked() and row < len(datasets):
                selected.append(datasets[row].name)

        if not selected:
            QMessageBox.warning(self, "Brak danych", "Zaznacz przynajmniej jeden dataset.")
            return

        self.train_btn.setEnabled(False)
        self.progress.show()
        self.train_log.clear()
        self.train_log.append(f"Trenuję na: {', '.join(selected)}")

        self._worker = TrainWorker(selected)
        self._worker.finished.connect(self._on_train_done)
        self._worker.error.connect(self._on_train_error)
        self._worker.start()

    def _on_train_done(self, meta: dict):
        self.train_btn.setEnabled(True)
        self.progress.hide()
        r2 = meta.get("r2", 0)
        self.train_log.append(f"✓ Gotowe!  R² = {r2:.4f} (±{meta.get('r2_std', 0):.4f})")
        self.train_log.append(f"Próbek: {meta.get('samples')}  |  Cechy: {len(meta.get('features', []))}")
        self._refresh_model_status()
        self._refresh_importances()

    def _on_train_error(self, error: str):
        self.train_btn.setEnabled(True)
        self.progress.hide()
        self.train_log.append(f"✗ Błąd: {error}")
        QMessageBox.critical(self, "Błąd treningu", error)

    def _delete_model(self):
        if QMessageBox.question(self, "Usuń model", "Usunąć wytrenowany model?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) == QMessageBox.StandardButton.Yes:
            pricing_svc.delete_model()
            self._refresh_model_status()
            self._refresh_importances()
            self.train_log.append("Model usunięty.")

    def refresh(self):
        self._refresh_datasets()
        self._refresh_train_list()
        self._refresh_model_status()
        self._refresh_importances()
