#!/usr/bin/env python3
"""
QuantDesk Desktop Application Entry Point
Run this file to start the PySide6 application
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
# Ensure vendored BackTrader package is importable if present under BackTrader/backtrader
bt_vendor = current_dir / 'BackTrader'
if bt_vendor.is_dir() and str(bt_vendor) not in sys.path:
    sys.path.insert(0, str(bt_vendor))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont, QIcon
except ImportError:
    print("Error: PySide6 not found. Please install it with:")
    print("pip install PySide6")
    sys.exit(1)

# Import our modules
try:
    from main_window import QuantDeskMainWindow
    from styles import StyleManager
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Make sure all required files are in the same directory:")
    print("- main_window.py")
    print("- sidebar.py") 
    print("- main_content.py")
    print("- styles.py")
    sys.exit(1)


def setup_application():
    """Setup application-wide configurations"""
    app = QApplication(sys.argv)
    
    # Application metadata
    app.setApplicationName("QuantDesk")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("QuantDesk")
    
    # Set default font
    if sys.platform == "win32":
        font = QFont("Segoe UI", 9)
    elif sys.platform == "darwin":  # macOS
        font = QFont("SF Pro Display", 13)
    else:  # Linux
        font = QFont("Ubuntu", 9)
    
    app.setFont(font)
    
    # Enable high DPI support (updated for PySide6)
    # These attributes are deprecated in Qt 6.x as high DPI is enabled by default
    # app.setAttribute(Qt.AA_EnableHighDpiScaling, True)  # Deprecated in Qt 6
    # app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)     # Deprecated in Qt 6
    
    return app


def main():
    """Main application entry point"""
    print("Starting QuantDesk...")
    
    # Create application
    app = setup_application()
    
    # Create and configure main window
    try:
        main_window = QuantDeskMainWindow()
        try:
            has_log = hasattr(main_window, 'main_content') and hasattr(main_window.main_content, 'status_log')
            print(f"[Diagnostics] MainContent status_log present={has_log}")
        except Exception:
            pass
        
        # Set window properties
        main_window.setMinimumSize(1200, 800)
        main_window.resize(1400, 900)
        
        # Center window on screen
        screen = app.primaryScreen().geometry()
        window_geometry = main_window.geometry()
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        main_window.move(x, y)
        
        # Show window maximized
        try:
            main_window.showMaximized()
        except Exception:
            # fallback
            main_window.show()
        
        print("QuantDesk started successfully!")
        print("Application ready for use.")
        # Optional headless test mode: set QD_HEADLESS_TEST=1 to auto-exit after a short delay
        if os.environ.get('QD_HEADLESS_TEST'):
            # Headless: allow more time for loader thread to finish cleanly.
            def _graceful_exit():
                try:
                    # Ensure all workers are stopped before closing
                    if hasattr(main_window, 'main_content') and main_window.main_content:
                        main_window.main_content.stop_all_workers(timeout=3000)
                    main_window.close()
                except Exception:
                    pass
                # Give extra time for cleanup before quit
                QTimer.singleShot(2000, app.quit)
            # ~6s total runtime to reduce QThread warnings
            QTimer.singleShot(4000, _graceful_exit)
        
    except Exception as e:
        import traceback
        print(f"Error creating main window: {e}")
        traceback.print_exc()
        return 1
    
    # Start event loop
    try:
        return app.exec()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0
    except Exception as e:
        print(f"Runtime error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
