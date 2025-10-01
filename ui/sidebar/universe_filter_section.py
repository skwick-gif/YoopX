# UniverseFilterSection for sidebar UI
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel

class UniverseFilterSection(QGroupBox):
    def __init__(self):
        super().__init__("סינון יקום")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Universe filter section (stub)"))
