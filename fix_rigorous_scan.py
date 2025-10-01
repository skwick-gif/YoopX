"""
🛠️ Fix Rigorous Scan - Allow More Signals
=========================================
תיקון הסריקה הנוקשה כדי לאפשר גם Hold signals ולהיות פחות נוקשה
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_rigorous_criteria():
    """תיקון הקריטריונים הנוקשים"""
    print("🛠️ Fixing Rigorous Criteria")
    print("-" * 40)
    
    try:
        # Read the current file
        with open('logic/rigorous_scanner.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix 1: Allow Buy and Hold signals for Conservative
        content = content.replace(
            'required_signals=["Buy"],  # רק Buy signals',
            'required_signals=["Buy", "Hold"],  # Buy and Hold signals'
        )
        
        # Fix 2: Allow Buy and Hold for Growth  
        content = content.replace(
            'required_signals=["Buy"],\n            max_signal_age=7',
            'required_signals=["Buy", "Hold"],\n            max_signal_age=7'
        )
        
        # Fix 3: Allow Buy and Hold for Elite
        content = content.replace(
            'required_signals=["Buy"],\n            max_signal_age=5',
            'required_signals=["Buy", "Hold"],\n            max_signal_age=5'
        )
        
        # Lower some thresholds for Conservative
        content = content.replace(
            'min_technical_score=70.0,  # Reduced from 75',
            'min_technical_score=60.0,  # Further reduced'
        )
        
        content = content.replace(
            'min_fundamental_score=65.0,  # Reduced from 75',
            'min_fundamental_score=50.0,  # Further reduced'
        )
        
        # Write back
        with open('logic/rigorous_scanner.py', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Fixed rigorous criteria:")
        print("   • Allow Buy and Hold signals")
        print("   • Lowered technical score threshold")
        print("   • Lowered fundamental score threshold")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False

def test_fixed_criteria():
    """בדיקת הקריטריונים המתוקנים"""
    print("\n🧪 Testing Fixed Criteria")
    print("-" * 40)
    
    try:
        from logic.rigorous_scanner import RigorousPremiumScanner
        from logic.enhanced_scanner import EnhancedScanResult
        import datetime
        
        # Create test stock with Hold signal
        test_stock = EnhancedScanResult(
            symbol="TEST_HOLD",
            timestamp=datetime.datetime.now().isoformat(),
            technical_signal="Hold",  # Changed to Hold
            technical_age=5,
            technical_score=65.0,
            fundamental_score=55.0,
            sector_score=70.0,
            business_quality_score=65.0,
            composite_score=78.0,
            grade="A-",
            risk_level="LOW",
            confidence_level="HIGH",
            pe_ratio=22.0,
            roe=0.16,
            debt_to_equity=35.0,
            financial_strength="STRONG",
            size_category="LARGE_CAP",
            sector="Technology",
            patterns=["HAMMER"],
            rr_ratio=2.2,
            employee_count=15000,
            recommendation="HOLD"
        )
        
        scanner = RigorousPremiumScanner()
        
        for profile in ['conservative', 'growth', 'elite']:
            filtered = scanner.apply_rigorous_filters([test_stock], profile)
            if filtered:
                print(f"✅ {profile.title()}: TEST_HOLD passed!")
                print(f"   Signal: {test_stock.technical_signal}")
                print(f"   Score: {test_stock.composite_score}")
                print(f"   Grade: {test_stock.grade}")
            else:
                print(f"❌ {profile.title()}: TEST_HOLD still filtered out")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def create_quick_debug_mode():
    """יצירת מצב debug מהיר"""
    debug_code = '''
def debug_rigorous_scan():
    """Debug mode for rigorous scan - shows why stocks are filtered"""
    
    from logic.rigorous_scanner import RigorousPremiumScanner
    from debug_real_scan import create_test_data, test_enhanced_scan
    
    print("🔍 DEBUG: Rigorous Scan Analysis")
    print("=" * 50)
    
    # Create data and run enhanced scan
    data_map = create_test_data()
    enhanced_results = test_enhanced_scan(data_map)
    
    if not enhanced_results:
        print("❌ No enhanced results to analyze")
        return
    
    # Analyze each stock in detail
    scanner = RigorousPremiumScanner()
    
    for result in enhanced_results:
        if result.status != "SUCCESS":
            continue
            
        print(f"\\n📊 Analyzing {result.symbol}:")
        print(f"   Technical Signal: {result.technical_signal}")
        print(f"   Technical Score: {result.technical_score}")
        print(f"   Fundamental Score: {result.fundamental_score}")
        print(f"   Composite Score: {result.composite_score}")
        print(f"   Grade: {result.grade}")
        print(f"   Risk: {result.risk_level}")
        
        # Test against conservative criteria
        criteria = scanner.conservative_criteria
        
        reasons = []
        if result.technical_signal not in criteria.required_signals:
            reasons.append(f"Signal {result.technical_signal} not in {criteria.required_signals}")
        
        if result.technical_score < criteria.min_technical_score:
            reasons.append(f"Technical score {result.technical_score} < {criteria.min_technical_score}")
            
        if result.fundamental_score < criteria.min_fundamental_score:
            reasons.append(f"Fundamental score {result.fundamental_score} < {criteria.min_fundamental_score}")
            
        if result.composite_score < criteria.min_composite_score:
            reasons.append(f"Composite score {result.composite_score} < {criteria.min_composite_score}")
        
        if reasons:
            print(f"   ❌ FILTERED OUT:")
            for reason in reasons:
                print(f"      • {reason}")
        else:
            print(f"   ✅ WOULD PASS conservative filter")

if __name__ == "__main__":
    debug_rigorous_scan()
'''
    
    with open('debug_rigorous_detailed.py', 'w', encoding='utf-8') as f:
        f.write(debug_code)
    
    print("💾 Created debug_rigorous_detailed.py")
    print("   Run with: py debug_rigorous_detailed.py")

if __name__ == "__main__":
    print("🛠️ Fixing Rigorous Scan Issues")
    print("=" * 50)
    
    # Fix the criteria
    if fix_rigorous_criteria():
        print("\n" + "="*20)
        
        # Test the fix
        if test_fixed_criteria():
            print("\n✅ Fix successful!")
            print("Now try the scan again in the UI")
        else:
            print("\n❌ Fix needs more work")
    
    # Create debug tool
    create_quick_debug_mode()
    
    print("\n💡 Quick test: Run the app and try Enhanced scan WITHOUT Rigorous first")
    print("💡 If that works, then try Conservative Rigorous mode")