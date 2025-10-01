"""
🔍 Debug Rigorous Scan Integration
=================================
בדיקת האינטגרציה של הסריקה הנוקשה במערכת הקיימת
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_enhanced_worker_import():
    """בדיקת ייבוא ה-enhanced worker"""
    print("🔍 Testing Enhanced Worker Import")
    print("-" * 40)
    
    try:
        from ui.enhanced_worker_thread import EnhancedWorkerThread, create_worker_thread
        print("✅ Enhanced worker imported successfully")
        
        # Test creating worker
        params = {'use_enhanced_scan': True, 'use_rigorous_scan': True}
        worker = create_worker_thread('scan', params, {}, use_enhanced=True)
        print(f"✅ Enhanced worker created: {type(worker)}")
        
        # Check if rigorous method exists
        if hasattr(worker, '_apply_rigorous_filtering'):
            print("✅ Rigorous filtering method found")
        else:
            print("❌ Rigorous filtering method NOT found")
            
    except Exception as e:
        print(f"❌ Enhanced worker import failed: {e}")

def debug_rigorous_scanner_import():
    """בדיקת ייבוא הסורק הנוקשה"""
    print("\n🎯 Testing Rigorous Scanner Import")
    print("-" * 40)
    
    try:
        from logic.rigorous_scanner import RigorousPremiumScanner, rigorous_scan_symbols
        print("✅ Rigorous scanner imported successfully")
        
        scanner = RigorousPremiumScanner()
        print(f"✅ Rigorous scanner created: {type(scanner)}")
        
        profiles = ['conservative', 'growth', 'elite']
        for profile in profiles:
            criteria = getattr(scanner, f'{profile}_criteria', None)
            if criteria:
                print(f"✅ {profile.title()} criteria found")
            else:
                print(f"❌ {profile.title()} criteria NOT found")
                
    except Exception as e:
        print(f"❌ Rigorous scanner import failed: {e}")

def debug_ui_integration():
    """בדיקת האינטגרציה עם ה-UI"""
    print("\n🖥️ Testing UI Integration")
    print("-" * 40)
    
    try:
        # Test UI imports
        from PySide6.QtWidgets import QApplication, QWidget
        from ui.tabs.scan_tab import ScanTab
        print("✅ UI imports successful")
        
        # Create minimal app for testing
        app = QApplication([]) if not QApplication.instance() else QApplication.instance()
        
        scan_tab = ScanTab()
        
        # Check if rigorous button exists
        if hasattr(scan_tab, 'rigorous_mode_btn'):
            print("✅ Rigorous button found in UI")
            print(f"   Text: {scan_tab.rigorous_mode_btn.text()}")
            print(f"   Checkable: {scan_tab.rigorous_mode_btn.isCheckable()}")
        else:
            print("❌ Rigorous button NOT found in UI")
            
        # Check if profile combo exists  
        if hasattr(scan_tab, 'rigorous_profile_combo'):
            print("✅ Rigorous profile combo found")
            items = [scan_tab.rigorous_profile_combo.itemText(i) 
                    for i in range(scan_tab.rigorous_profile_combo.count())]
            print(f"   Items: {items}")
        else:
            print("❌ Rigorous profile combo NOT found")
            
        # Check rigorous toggle method
        if hasattr(scan_tab, '_toggle_rigorous_mode'):
            print("✅ Rigorous toggle method found")
        else:
            print("❌ Rigorous toggle method NOT found")
            
        app.quit() if app else None
        
    except Exception as e:
        print(f"❌ UI integration test failed: {e}")

def debug_scan_params():
    """בדיקת פרמטרי הסריקה"""
    print("\n📊 Testing Scan Parameters")
    print("-" * 40)
    
    # Simulate scan parameters
    base_params = {
        'scan_strategies': ['Donchian Breakout'],
        'patterns': 'HAMMER,DOJI',
        'lookback': 30,
        'use_enhanced_scan': True,
        'use_rigorous_scan': True,
        'rigorous_profile': 'conservative'
    }
    
    print(f"✅ Base parameters: {base_params}")
    
    # Test parameter validation
    required_for_rigorous = [
        'use_enhanced_scan',
        'use_rigorous_scan', 
        'rigorous_profile'
    ]
    
    missing = [param for param in required_for_rigorous if param not in base_params]
    if not missing:
        print("✅ All rigorous parameters present")
    else:
        print(f"❌ Missing rigorous parameters: {missing}")

def debug_worker_connection():
    """בדיקת החיבור של ה-worker thread"""
    print("\n🔗 Testing Worker Thread Connection")
    print("-" * 40)
    
    try:
        from ui.enhanced_worker_thread import EnhancedWorkerThread
        
        params = {
            'use_enhanced_scan': True,
            'use_rigorous_scan': True,
            'rigorous_profile': 'conservative'
        }
        
        worker = EnhancedWorkerThread('scan', params, {})
        print(f"✅ Worker created: {type(worker)}")
        
        # Check signals
        signals_to_check = [
            'progress_updated',
            'status_updated', 
            'results_ready',
            'enhanced_results_ready',
            'error_occurred'
        ]
        
        for signal_name in signals_to_check:
            if hasattr(worker, signal_name):
                print(f"✅ Signal found: {signal_name}")
            else:
                print(f"❌ Signal missing: {signal_name}")
                
        # Check rigorous method
        if hasattr(worker, '_apply_rigorous_filtering'):
            print("✅ Rigorous filtering method exists in worker")
        else:
            print("❌ Rigorous filtering method missing in worker")
            
    except Exception as e:
        print(f"❌ Worker connection test failed: {e}")

def create_test_fix():
    """יצירת קובץ תיקון אם נמצאות בעיות"""
    print("\n🔧 Creating Integration Fix")
    print("-" * 40)
    
    fix_code = '''
# Quick fix for rigorous scan integration issues

def ensure_rigorous_scan_working():
    """Make sure rigorous scan is properly integrated"""
    
    # 1. Check if enhanced worker has rigorous method
    try:
        from ui.enhanced_worker_thread import EnhancedWorkerThread
        
        # Add missing method if needed
        if not hasattr(EnhancedWorkerThread, '_apply_rigorous_filtering'):
            def _apply_rigorous_filtering(self, enhanced_results):
                """Apply rigorous filtering to enhanced results"""
                if not self.params.get('use_rigorous_scan', False):
                    return enhanced_results
                    
                try:
                    from logic.rigorous_scanner import RigorousPremiumScanner
                    scanner = RigorousPremiumScanner()
                    profile = self.params.get('rigorous_profile', 'conservative')
                    
                    self.status_updated.emit(f"🎯 Applying {profile} rigorous filtering...")
                    filtered = scanner.apply_rigorous_filters(enhanced_results, profile)
                    self.status_updated.emit(f"🏆 {len(filtered)} stocks passed rigorous filtering")
                    
                    return filtered
                except Exception as e:
                    self.error_occurred.emit(f"Rigorous filtering failed: {e}")
                    return enhanced_results
            
            EnhancedWorkerThread._apply_rigorous_filtering = _apply_rigorous_filtering
            print("✅ Added rigorous filtering method to worker")
            
    except Exception as e:
        print(f"❌ Worker fix failed: {e}")
    
    print("Fix applied - try running scan again")
    '''
    
    with open('rigorous_scan_fix.py', 'w', encoding='utf-8') as f:
        f.write(fix_code)
    
    print("💾 Fix saved to: rigorous_scan_fix.py")

if __name__ == "__main__":
    print("🔍 Debugging Rigorous Scan Integration")
    print("=" * 50)
    
    debug_enhanced_worker_import()
    debug_rigorous_scanner_import()
    debug_ui_integration() 
    debug_scan_params()
    debug_worker_connection()
    create_test_fix()
    
    print("\n" + "=" * 50)
    print("🎯 Diagnosis Complete!")
    print("If any ❌ appeared above, run the fix file:")
    print("   py rigorous_scan_fix.py")
    print("Then try the scan again.")