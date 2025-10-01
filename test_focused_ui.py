"""
Test Enhanced UI - Focused Scoring Demo
======================================
Test the improved enhanced UI with focused scoring approach.
"""

import os
import sys
import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_enhanced_ui_focused():
    """Test the focused enhanced UI approach"""
    
    print("🎯 Enhanced UI - Focused Scoring Test")
    print("=" * 45)
    print("Testing the new simplified approach:")
    print("  📊 Enhanced Score (single composite metric)")  
    print("  🎯 Grade (A+ to F)")
    print("  💡 Smart Recommendation")
    print("  🏢 Key Business Context (Sector + Risk)")
    print("  ❌ NO information overload!")
    print()
    
    try:
        from logic.enhanced_scanner import EnhancedScanEngine
        from data.non_technical_loader import NonTechnicalDataLoader
        import pandas as pd
        import numpy as np
        
        # Create focused test
        symbols = ['MSFT', 'GOOGL', 'TSLA']
        data_map = {}
        
        print("📈 Creating test data...")
        for i, symbol in enumerate(symbols):
            # Generate 100 days of data
            dates = pd.date_range(start='2024-06-01', periods=100, freq='D')
            base_price = [300, 150, 200][i]
            
            np.random.seed(42 + i)
            prices = [base_price]
            for _ in range(99):
                change = np.random.normal(0, 0.02)
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1))
            
            df = pd.DataFrame({
                'Open': prices,
                'High': [p * 1.02 for p in prices],
                'Low': [p * 0.98 for p in prices], 
                'Close': prices,
                'Volume': [1000000] * 100
            }, index=dates)
            
            data_map[symbol] = df
            print(f"  📊 {symbol}: Current Price ${df['Close'].iloc[-1]:.2f}")
        
        # Run enhanced scan
        engine = EnhancedScanEngine(data_map)
        
        params = {
            'scan_strategy': 'Donchian Breakout',
            'upper': 20, 'lower': 10,
            'patterns': 'ENGULFING,DOJI',
            'use_enhanced_scan': True
        }
        
        print(f"\n🔄 Running Focused Enhanced Scan...")
        results = engine.bulk_scan_enhanced(symbols, params)
        
        print(f"\n📋 FOCUSED RESULTS TABLE")
        print("-" * 50)
        print(f"{'Symbol':<8} {'Signal':<6} {'Age':<4} {'Price':<8} {'Enhanced':<9} {'Grade':<5} {'Recommendation':<12} {'Sector':<15} {'Risk':<6}")
        print("-" * 50)
        
        for result in results:
            if result.status == "SUCCESS":
                print(f"{result.symbol:<8} {result.technical_signal:<6} {result.technical_age:<4} ${result.price_at_signal:<7.2f} "
                      f"{result.composite_score:<8.1f} {result.grade:<5} {result.recommendation:<12} "
                      f"{result.sector[:14]:<15} {result.risk_level:<6}")
        
        print(f"\n💡 KEY INSIGHTS:")
        print("-" * 15)
        
        for result in results:
            if result.status == "SUCCESS":
                print(f"\n🔍 {result.symbol}:")
                print(f"   Enhanced Score: {result.composite_score:.1f}/100")
                print(f"   Breakdown: Technical={result.technical_score:.1f} + Fundamental={result.fundamental_score:.1f} + Sector={result.sector_score} + Quality={result.business_quality_score:.1f}")
                print(f"   Bottom Line: {result.grade} grade → {result.recommendation}")
                
                # Show why this score
                if result.composite_score >= 85:
                    print(f"   💚 Excellent overall - strong across all dimensions")
                elif result.composite_score >= 70:
                    print(f"   💛 Good candidate with some strengths")
                else:
                    print(f"   🔴 Needs attention - mixed signals")
        
        print(f"\n🎯 UI FOCUS BENEFITS:")
        print("✅ Single Enhanced Score - easy to understand")
        print("✅ Clear Grade system - like school grades") 
        print("✅ Action-oriented Recommendations")
        print("✅ Key context only (Sector + Risk)")
        print("❌ No information overload")
        print("❌ No meaningless detailed numbers")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🚀 Starting Focused Enhanced UI Test at {datetime.datetime.now()}")
    print()
    
    success = test_enhanced_ui_focused()
    
    print(f"\n{'🎉 Test completed successfully!' if success else '❌ Test failed!'}")
    print(f"Time: {datetime.datetime.now()}")