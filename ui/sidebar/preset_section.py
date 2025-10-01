# PresetSection for sidebar UI
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel

class PresetSection(QGroupBox):
    def __init__(self):
        super().__init__("קביעת תצורה")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Preset section (stub)"))
