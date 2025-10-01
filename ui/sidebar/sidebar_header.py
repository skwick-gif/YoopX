# SidebarHeader component for sidebar UI
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QFont
from ui.styles.style_manager import StyleManager

class SidebarHeader(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
    def setup_ui(self):
        # ensure the widget has the sidebar_header name early so styles apply
        self.setObjectName("sidebar_header")
        layout = QVBoxLayout(self)
        # remove top margin so the header content sits flush with top of the sidebar
        layout.setContentsMargins(12, 0, 12, 8)
        logo_label = QLabel("QuantDesk")
        logo_label.setObjectName("logo")
        subtitle_label = QLabel("מערכת מסחר כמותית")
        subtitle_label.setObjectName("subtitle")
        layout.addWidget(logo_label)
        layout.addWidget(subtitle_label)
        # keep a small stretch to push content to the top while allowing the
        # header to occupy the natural height required by its contents
        layout.addStretch()
