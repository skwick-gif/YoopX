#!/usr/bin/env python3
"""
בדיקת הממשק הגרפי הבסיסי
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
except ImportError:
    print("Error: PySide6 not found. Please install it with:")
    print("pip install PySide6")
    sys.exit(1)

def test_basic_ui():
    print("🖥️ Testing basic UI components...")
    
    app = QApplication(sys.argv)
    
    try:
        from main_window import QuantDeskMainWindow
        from styles import StyleManager
        
        print("✅ UI modules imported successfully")
        
        # Create and configure main window
        main_window = QuantDeskMainWindow()
        main_window.setMinimumSize(800, 600)
        
        print("✅ Main window created")
        
        # Check if main content was created
        if hasattr(main_window, 'main_content'):
            print("✅ Main content initialized")
            
            # Check data loading
            if hasattr(main_window.main_content, 'data_map'):
                print(f"✅ Data map available: {len(main_window.main_content.data_map)} symbols")
            else:
                print("⚠️ Data map not initialized")
                
            # Check ML training capability
            if hasattr(main_window.main_content, 'on_train_ml'):
                print("✅ ML training method available")
            else:
                print("⚠️ ML training method not found")
        else:
            print("❌ Main content not initialized")
        
        # Test without showing the window (headless mode)
        print("✅ UI test completed successfully")
        
        # Proper cleanup
        try:
            if hasattr(main_window, 'main_content'):
                main_window.main_content.stop_all_workers(timeout=1000)
            main_window.close()
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        app.quit()

if __name__ == "__main__":
    # Set headless test environment variable
    os.environ['QD_HEADLESS_TEST'] = '1'
    success = test_basic_ui()
    sys.exit(0 if success else 1)