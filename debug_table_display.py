"""
Debug Enhanced Table Display Issues
==================================
Test to identify why signals appear instead of prices and missing recommendations.
"""

import sys
import os
import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def debug_enhanced_scan_result():
    """Debug the enhanced scan result structure"""
    
    print("🔍 Debugging Enhanced Scan Result Display Issues")
    print("=" * 60)
    
    try:
        from logic.enhanced_scanner import EnhancedScanEngine
        import pandas as pd
        import numpy as np
        
        # Create simple test data
        symbol = "TEST"
        dates = pd.date_range(start='2024-06-01', periods=50, freq='D')
        prices = [100 + i * 0.5 + np.random.normal(0, 1) for i in range(50)]
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.99 for p in prices], 
            'Close': prices,
            'Volume': [1000000] * 50
        }, index=dates)
        
        data_map = {symbol: df}
        
        # Create engine and scan
        engine = EnhancedScanEngine(data_map)
        
        params = {
            'scan_strategy': 'Donchian Breakout',
            'upper': 20, 'lower': 10,
            'patterns': 'HAMMER',
            'use_enhanced_scan': True
        }
        
        print(f"📊 Testing scan for {symbol}")
        print(f"Last price in data: ${df['Close'].iloc[-1]:.2f}")
        
        result = engine.scan_symbol_enhanced(symbol, params)
        
        print(f"\n🔍 Enhanced Scan Result Debug:")
        print("-" * 40)
        print(f"Symbol: '{result.symbol}'")
        print(f"Technical Signal: '{result.technical_signal}'")
        print(f"Technical Age: {result.technical_age}")
        print(f"Price at Signal: {result.price_at_signal}")
        print(f"RR Ratio: {result.rr_ratio}")
        print(f"Patterns: {result.patterns}")
        print(f"Composite Score: {result.composite_score}")
        print(f"Grade: '{result.grade}'")
        print(f"Recommendation: '{result.recommendation}'")
        print(f"Sector: '{result.sector}'")
        print(f"Risk Level: '{result.risk_level}'")
        print(f"Status: '{result.status}'")
        
        print(f"\n🎯 Table Display Simulation:")
        print("-" * 40)
        
        # Simulate exact table population logic
        def simulate_table_display(result):
            """Simulate what goes into each column"""
            print(f"Column 1 (Symbol): '{result.symbol or ''}'")
            print(f"Column 2 (Signal): '{result.technical_signal or ''}'") 
            print(f"Column 3 (Age): '{result.technical_age if result.technical_age is not None else ''}'")
            
            # Price column - this is where the bug might be!
            price_text = f"${result.price_at_signal:.2f}" if result.price_at_signal and result.price_at_signal > 0 else ""
            print(f"Column 4 (Price): '{price_text}'")
            
            # RR Ratio
            rr_text = f"{result.rr_ratio:.2f}" if result.rr_ratio and result.rr_ratio > 0 else ""
            print(f"Column 5 (R:R): '{rr_text}'")
            
            # Patterns 
            patterns_text = ','.join(result.patterns) if result.patterns else ""
            print(f"Column 6 (Patterns): '{patterns_text}'")
            
            # Enhanced Score
            print(f"Column 7 (Enhanced): '{result.composite_score:.1f}'")
            
            # Grade
            grade_text = result.grade if result.grade else "N/A"
            print(f"Column 8 (Grade): '{grade_text}'")
            
            # Recommendation  
            rec_text = result.recommendation if result.recommendation else "N/A"
            print(f"Column 9 (Recommendation): '{rec_text}'")
            
            # Sector
            sector_text = result.sector if result.sector else "N/A"
            print(f"Column 10 (Sector): '{sector_text}'")
            
            # Risk
            risk_text = result.risk_level if result.risk_level else "MEDIUM"
            print(f"Column 11 (Risk): '{risk_text}'")
        
        simulate_table_display(result)
        
        print(f"\n❌ Potential Issues Identified:")
        
        if not result.price_at_signal or result.price_at_signal <= 0:
            print("🔴 ISSUE: price_at_signal is missing or invalid!")
            print(f"   Current value: {result.price_at_signal}")
            print("   This might cause signals to appear instead of prices")
        
        if not result.recommendation:
            print("🔴 ISSUE: recommendation is missing!")
            print("   This causes empty recommendation columns")
        
        if not result.grade:
            print("🔴 ISSUE: grade is missing!")
            
        if not result.sector:
            print("🔴 ISSUE: sector is missing!")
            
        if result.composite_score == 0:
            print("🔴 ISSUE: composite_score is 0!")
        
        print(f"\n💡 Expected vs Actual:")
        print("Expected Price Column: '$124.50'")
        print(f"Actual Price Column: '${result.price_at_signal:.2f}' if result.price_at_signal and result.price_at_signal > 0 else ''")
        print("This might explain why you see signals instead of prices!")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🚀 Starting Debug Session at {datetime.datetime.now()}")
    print()
    
    success = debug_enhanced_scan_result()
    
    print(f"\n{'🎉 Debug completed!' if success else '❌ Debug failed!'}")
    
    if success:
        print(f"\nNext steps to fix the issues:")
        print("1. Check backend.scan_signal() to ensure it returns valid price")
        print("2. Verify recommendation generation logic")
        print("3. Ensure all required fields are populated")