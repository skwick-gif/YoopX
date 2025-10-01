# DataSourceSection for sidebar UI
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal

class DataSourceSection(QGroupBox):
    load_data_requested = Signal(dict)
    configure_requested = Signal()
    def __init__(self):
        super().__init__("מקור נתונים")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Data source section (stub)"))
        cfg_btn = QPushButton('Configure Data...')
        cfg_btn.clicked.connect(lambda: self.configure_requested.emit())
        layout.addWidget(cfg_btn)
