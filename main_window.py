import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                               QVBoxLayout, QScrollArea, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from main_content import MainContent
from styles import StyleManager


class QuantDeskMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuantDesk")
        # Enlarge default size per user request
        self.setMinimumSize(1600, 900)
        self.setup_ui()
        self.apply_styles()
        
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Main horizontal layout (sidebar + content)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create main content area (takes full width now that sidebar is removed)
        self.main_content = MainContent()
        main_layout.addWidget(self.main_content, 1)
        # Leave alignment unset so the main content may expand vertically and
        # the layout distributes height according to its size policy.
    def apply_styles(self):
        StyleManager.apply_main_window_style(self)
        
    # Sidebar removed — no additional signal wiring required here

    def closeEvent(self, event):
        try:
            if hasattr(self, 'main_content') and self.main_content:
                try:
                    self.main_content.stop_all_workers(timeout=3000)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            super().closeEvent(event)
        except Exception:
            try:
                event.accept()
            except Exception:
                pass


def main():
    app = QApplication(sys.argv)
    
    # Set application font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    # Create and show main window
    window = QuantDeskMainWindow()
    window.showMaximized()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
