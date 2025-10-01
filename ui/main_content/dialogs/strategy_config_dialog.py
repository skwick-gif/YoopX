from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QMessageBox
import json


class StrategyConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Strategy Configuration")
        self.parsed_params = None
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Enter strategy params as JSON:"))
        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText('{"fast": 8, "slow": 24}')
        layout.addWidget(self.params_edit)

        ok = QPushButton("Save")
        ok.clicked.connect(self._on_save)
        layout.addWidget(ok)

        self.setLayout(layout)

    def _on_save(self):
        txt = self.params_edit.toPlainText().strip()
        if not txt:
            # empty is allowed (means use defaults); store empty dict
            self.parsed_params = {}
            self.accept()
            return
        try:
            obj = json.loads(txt)
            if not isinstance(obj, dict):
                raise ValueError('Top-level JSON must be an object/dict')
            self.parsed_params = obj
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, 'Invalid JSON', f'Please enter valid JSON object for strategy params.\nError: {e}')
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit

class StrategyConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Strategy Configuration')
        self.resize(640, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Strategy params JSON:'))
        self.params_edit = QTextEdit()
        self.params_edit.setPlaceholderText('{\n  "fast": 8,\n  "slow": 20\n}')
        layout.addWidget(self.params_edit)
        btn = QPushButton('Save')
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
