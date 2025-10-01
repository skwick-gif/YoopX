# RiskManagementSection for sidebar UI
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QCheckBox

class RiskManagementSection(QGroupBox):
    def __init__(self):
        super().__init__("⚖️ ניהול סיכונים")
        self.setup_ui()
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.regime_cb = QCheckBox("Regime (SPY>EMA200)")
        layout.addWidget(self.regime_cb)
