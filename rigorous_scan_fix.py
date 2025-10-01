
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
    