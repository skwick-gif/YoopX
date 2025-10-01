from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout


class DataConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Data Source")
        layout = QVBoxLayout()

        hl = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._on_browse)
        hl.addWidget(QLabel("Data folder or CSV:"))
        hl.addWidget(self.path_edit)
        hl.addWidget(browse)

        layout.addLayout(hl)

        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)

        self.setLayout(layout)

    def _on_browse(self):
        p = QFileDialog.getExistingDirectory(self, "Select data folder")
        if p:
            self.path_edit.setText(p)
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QHBoxLayout

class DataConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configure Data Source')
        self.resize(520, 200)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Data folder or CSV path:'))
        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        browse = QPushButton('Browse')
        browse.clicked.connect(self.on_browse)
        row.addWidget(self.path_edit)
        row.addWidget(browse)
        layout.addLayout(row)
        layout.addStretch()
        btn = QPushButton('OK')
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def on_browse(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Select data file or folder')
        if p:
            self.path_edit.setText(p)
