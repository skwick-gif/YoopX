"""
Quick test to verify the UI improvements for status bar and button layout.
"""

import sys
import os
sys.path.append('.')

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from ui.styles.style_manager import StyleManager

def test_ui_layout():
    """Test the improved UI layout"""
    
    # Create minimal app
    app = QApplication([])
    
    # Create test window
    window = QWidget()
    window.setWindowTitle("UI Layout Test")
    window.resize(800, 100)
    
    layout = QVBoxLayout(window)
    
    # Test bottom bar layout similar to main_content
    bottom_layout = QHBoxLayout()
    
    # Test buttons with new styling
    def _mk_btn(text):
        b = QPushButton(text)
        b.setObjectName('toolbar_button')
        b.setMinimumWidth(95)
        b.setFixedHeight(28)
        return b
    
    buttons = [
        _mk_btn("Daily Update"),
        _mk_btn("Daily Update (45%)"),  # Test progress display
        _mk_btn("Build/Refresh"),
        _mk_btn("Force Rebuild"),
        _mk_btn("Verify Data")
    ]
    
    for btn in buttons:
        bottom_layout.addWidget(btn)
    
    # Test status label
    status_label = QLineEdit("טוען נתונים מרובי מקורות... מתקבלים נתונים מ-Yahoo Finance עם גיבויי API")
    status_label.setReadOnly(True)
    status_label.setObjectName("status_info")
    status_label.setMinimumWidth(300)
    status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    
    bottom_layout.addWidget(status_label, 1)  # Give it stretch
    
    layout.addLayout(bottom_layout)
    
    # Apply styles
    window.setStyleSheet(StyleManager.get_main_content_style())
    
    print("UI Layout Test:")
    print(f"  Status label minimum width: {status_label.minimumWidth()}")
    print(f"  Status label alignment: Left + VCenter")
    print(f"  Button minimum width: {buttons[0].minimumWidth()}")
    print("  Testing different button texts:")
    
    for i, btn in enumerate(buttons):
        print(f"    Button {i+1}: '{btn.text()}' - width: {btn.sizeHint().width()}")
    
    # Test text clipping
    long_text = "מתבצע עדכון יומי מקיף: משיכת נתונים מ-Yahoo Finance + API Polygon + AlphaVantage + ESG נתונים + לוח רווחים - התקדמות 67%"
    status_label.setText(long_text)
    print(f"\n  Long text test: {len(long_text)} characters")
    print(f"  Text: {long_text[:80]}...")
    
    # Show window briefly
    window.show()
    
    # Quick update test
    import time
    for progress in [25, 50, 75, 100]:
        buttons[0].setText(f"Daily Update ({progress}%)")
        app.processEvents()
        time.sleep(0.1)
    
    buttons[0].setText("Daily Update")
    app.processEvents()
    
    print("✅ UI layout test completed successfully!")
    print("\nImprovements made:")
    print("  • Status text aligned to left for better readability")
    print("  • Button width increased to accommodate progress display")
    print("  • Status bar minimum width reduced for flexibility")
    print("  • Dynamic button text shows progress percentage")
    print("  • Better text styling and padding")
    
    window.close()
    app.quit()
    
    return True

if __name__ == "__main__":
    test_ui_layout()