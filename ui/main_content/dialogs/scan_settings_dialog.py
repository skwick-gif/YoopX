from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton)
from PySide6.QtCore import Qt


class ScanSettingsDialog(QDialog):
    """Dialog to edit Scan parameters (patterns, lookback, RR target, min R:R)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan Settings")
        self.resize(480, 320)
        self.layout = QVBoxLayout(self)

        self.patterns_edit = QTextEdit()
        self.patterns_edit.setPlaceholderText("ENGULFING,DOJI,HAMMER...")
        self.patterns_edit.setMaximumHeight(120)

        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(5, 365)
        self.lookback_spin.setValue(30)

        self.rr_target_combo = QComboBox()
        self.rr_target_combo.addItems(["2xATR", "Boll mid", "Donchian high"])

        self.min_rr_spin = QDoubleSpinBox()
        self.min_rr_spin.setRange(0.0, 100.0)
        self.min_rr_spin.setSingleStep(0.1)

        def add_row(label, widget):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(widget)
            self.layout.addLayout(row)

        self.layout.addWidget(QLabel('Patterns (comma-separated):'))
        self.layout.addWidget(self.patterns_edit)
        add_row('Lookback (days):', self.lookback_spin)
        add_row('RR Target:', self.rr_target_combo)
        add_row('Min R:R:', self.min_rr_spin)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.ok_btn = QPushButton('OK')
        self.cancel_btn = QPushButton('Cancel')
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.ok_btn)
        self.layout.addLayout(btn_row)

    def set_values(self, values: dict):
        if not isinstance(values, dict):
            return
        try:
            self.patterns_edit.setPlainText(values.get('patterns', '') or '')
        except Exception:
            pass
        try:
            self.lookback_spin.setValue(int(values.get('lookback', 30) or 30))
        except Exception:
            pass
        try:
            rt = values.get('rr_target')
            if rt:
                idx = self.rr_target_combo.findText(rt)
                if idx >= 0:
                    self.rr_target_combo.setCurrentIndex(idx)
        except Exception:
            pass
        try:
            self.min_rr_spin.setValue(float(values.get('min_rr', 0.0) or 0.0))
        except Exception:
            pass

    def get_values(self) -> dict:
        return {
            'patterns': self.patterns_edit.toPlainText().strip(),
            'lookback': int(self.lookback_spin.value()),
            'rr_target': self.rr_target_combo.currentText(),
            'min_rr': float(self.min_rr_spin.value()),
        }
