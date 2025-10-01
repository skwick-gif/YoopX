"""
Test Enhanced Table with Real Interface Debug
===========================================
Test with debug prints to see exactly what goes into each table column.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def debug_table_population():
    """Test table population with debug output"""
    
    print("🔍 Testing Enhanced Table Population with Debug")
    print("=" * 60)
    
    try:
        from logic.enhanced_scanner import EnhancedScanEngine, EnhancedScanResult
        import pandas as pd
        import numpy as np
        import datetime
        
        # Create test results that should work well
        results = [
            EnhancedScanResult(
                symbol="AAPL",
                timestamp=datetime.datetime.now().isoformat(),
                technical_signal="Buy",
                technical_age=3,
                price_at_signal=175.50,
                patterns=["HAMMER", "DOJI"],
                rr_ratio=2.8,
                technical_score=85.0,
                fundamental_score=90.0,
                sector_score=88,
                business_quality_score=92.0,
                composite_score=88.5,
                grade="A",
                recommendation="BUY",
                sector="Technology",
                risk_level="LOW"
            ),
            EnhancedScanResult(
                symbol="GOOGL", 
                timestamp=datetime.datetime.now().isoformat(),
                technical_signal="Hold",
                technical_age=7,
                price_at_signal=142.30,
                patterns=["ENGULFING"],
                rr_ratio=2.1,
                technical_score=75.0,
                fundamental_score=85.0,
                sector_score=80,
                business_quality_score=88.0,
                composite_score=79.5,
                grade="B+",
                recommendation="HOLD",
                sector="Communication",
                risk_level="LOW"
            ),
            EnhancedScanResult(
                symbol="TSLA",
                timestamp=datetime.datetime.now().isoformat(),
                technical_signal="Sell",
                technical_age=12,
                price_at_signal=251.20,
                patterns=[],
                rr_ratio=1.5,
                technical_score=45.0,
                fundamental_score=35.0,
                sector_score=40,
                business_quality_score=50.0,
                composite_score=42.0,
                grade="D+",
                recommendation="AVOID",
                sector="Consumer Cyclical",
                risk_level="HIGH"
            )
        ]
        
        print("📊 Enhanced Table Headers:")
        headers = ["Symbol","Signal","Age","Price","R:R","Patterns","Enhanced Score","Grade","Recommendation","Sector","Risk"]
        for i, header in enumerate(headers):
            print(f"  Column {i}: {header}")
        
        print(f"\n📋 Table Population Simulation:")
        print("=" * 80)
        
        for row, result in enumerate(results):
            print(f"\n🔍 Row {row} ({result.symbol}):")
            print("-" * 40)
            
            col = 0
            
            # Symbol
            symbol_val = result.symbol or ""
            print(f"  Col {col} (Symbol): '{symbol_val}'"); col += 1
            
            # Signal
            signal_val = result.technical_signal or ""
            print(f"  Col {col} (Signal): '{signal_val}'"); col += 1
            
            # Age  
            age_text = str(result.technical_age) if result.technical_age is not None else ""
            print(f"  Col {col} (Age): '{age_text}'"); col += 1
            
            # Price - בדיקה מדויקת
            price_text = f"${result.price_at_signal:.2f}" if result.price_at_signal and result.price_at_signal > 0 else ""
            print(f"  Col {col} (Price): '{price_text}' <-- זה צריך להיות מחיר!"); col += 1
            
            # RR
            rr_text = f"{result.rr_ratio:.2f}" if result.rr_ratio and result.rr_ratio > 0 else ""
            print(f"  Col {col} (R:R): '{rr_text}'"); col += 1
            
            # Patterns
            patterns_text = ','.join(result.patterns) if result.patterns else ""
            print(f"  Col {col} (Patterns): '{patterns_text}'"); col += 1
            
            # Enhanced Score
            score_text = f"{result.composite_score:.1f}"
            print(f"  Col {col} (Enhanced): '{score_text}'"); col += 1
            
            # Grade
            grade_text = result.grade if result.grade else "N/A"
            print(f"  Col {col} (Grade): '{grade_text}'"); col += 1
            
            # Recommendation
            rec_text = result.recommendation if result.recommendation else "N/A"
            print(f"  Col {col} (Recommendation): '{rec_text}'"); col += 1
            
            # Sector
            sector_text = result.sector if result.sector else "N/A"
            print(f"  Col {col} (Sector): '{sector_text}'"); col += 1
            
            # Risk
            risk_text = result.risk_level if result.risk_level else "MEDIUM"
            print(f"  Col {col} (Risk): '{risk_text}'"); col += 1
            
            # Check for obvious issues
            print(f"\n  ✅ Data validation:")
            if price_text:
                print(f"     Price looks good: {price_text}")
            else:
                print(f"     ❌ Price is empty! Raw value: {result.price_at_signal}")
                
            if rec_text != "N/A":
                print(f"     Recommendation looks good: {rec_text}")
            else:
                print(f"     ❌ Recommendation missing! Raw value: '{result.recommendation}'")
        
        print(f"\n🎯 Expected Table Display:")
        print("=" * 80)
        print(f"{'Symbol':<8} {'Signal':<6} {'Age':<3} {'Price':<8} {'R:R':<4} {'Patterns':<10} {'Enhanced':<8} {'Grade':<5} {'Recommendation':<12} {'Sector':<12} {'Risk':<6}")
        print("-" * 80)
        
        for result in results:
            symbol = result.symbol or ""
            signal = result.technical_signal or ""
            age = str(result.technical_age) if result.technical_age is not None else ""
            price = f"${result.price_at_signal:.2f}" if result.price_at_signal and result.price_at_signal > 0 else ""
            rr = f"{result.rr_ratio:.1f}" if result.rr_ratio and result.rr_ratio > 0 else ""
            patterns = ','.join(result.patterns[:1]) if result.patterns else ""  # First pattern only for display
            enhanced = f"{result.composite_score:.1f}"
            grade = result.grade or "N/A"
            rec = result.recommendation or "N/A"
            sector = result.sector or "N/A"
            risk = result.risk_level or "MED"
            
            print(f"{symbol:<8} {signal:<6} {age:<3} {price:<8} {rr:<4} {patterns:<10} {enhanced:<8} {grade:<5} {rec:<12} {sector:<12} {risk:<6}")
        
        print(f"\n💡 If you see signals instead of prices:")
        print("1. Check that columns are aligned correctly")
        print("2. Verify enhanced_mode_btn.isChecked() returns True")
        print("3. Make sure _setup_table() is called with right mode")
        print("4. Check if table headers match data population order")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_table_population()