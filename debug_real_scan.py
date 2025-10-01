"""
🔍 Test Real Scan with Debug Output
==================================
בדיקת סריקה מציאותית עם פלט debug מפורט
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from ui.enhanced_worker_thread import EnhancedWorkerThread
from logic.enhanced_scanner import EnhancedScanEngine
from logic.rigorous_scanner import RigorousPremiumScanner
import time

def create_test_data():
    """יצירת נתוני בדיקה בסיסיים"""
    print("📊 Creating test data...")
    
    # Create simple price data for a few symbols
    import numpy as np
    
    dates = pd.date_range('2023-01-01', '2024-12-01', freq='D')
    
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    data_map = {}
    
    for symbol in test_symbols:
        # Create realistic price data with some trends
        np.random.seed(hash(symbol) % 1000)  # Different seed per symbol
        
        base_price = 100 + (hash(symbol) % 500)  # Different base price
        returns = np.random.normal(0.001, 0.02, len(dates))  # Daily returns
        
        prices = [base_price]
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1.0))  # Minimum price of $1
        
        # Create DataFrame with required columns
        df = pd.DataFrame({
            'Date': dates,
            'Open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
            'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices], 
            'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'Close': prices,
            'Volume': [int(1000000 + np.random.exponential(500000)) for _ in prices]
        })
        
        df.set_index('Date', inplace=True)
        data_map[symbol] = df
        
        print(f"  ✅ Created data for {symbol}: {len(df)} rows, price range ${df['Close'].min():.2f}-${df['Close'].max():.2f}")
    
    return data_map

def test_enhanced_scan(data_map):
    """בדיקת הסריקה המשופרת"""
    print("\n🔍 Testing Enhanced Scan")
    print("-" * 40)
    
    # Create enhanced scan engine
    engine = EnhancedScanEngine(data_map)
    
    # Basic scan parameters
    params = {
        'scan_strategy': 'Donchian Breakout',
        'upper': 20,
        'lower': 10,
        'patterns': 'HAMMER,DOJI',
        'lookback': 30,
        'rr_target': '2xATR'
    }
    
    symbols = list(data_map.keys())
    print(f"Scanning {len(symbols)} symbols: {symbols}")
    
    try:
        results = engine.bulk_scan_enhanced(symbols, params)
        print(f"✅ Enhanced scan completed: {len(results)} results")
        
        for result in results:
            if result.status == "SUCCESS":
                print(f"  📈 {result.symbol}: Score={result.composite_score:.1f}, Grade={result.grade}, Rec={result.recommendation}")
            else:
                print(f"  ❌ {result.symbol}: Error - {result.error_message}")
                
        return results
        
    except Exception as e:
        print(f"❌ Enhanced scan failed: {e}")
        return []

def test_rigorous_filtering(enhanced_results):
    """בדיקת הסינון הנוקשה"""
    print("\n🎯 Testing Rigorous Filtering")
    print("-" * 40)
    
    if not enhanced_results:
        print("❌ No enhanced results to filter")
        return
    
    scanner = RigorousPremiumScanner()
    
    for profile in ['conservative', 'growth', 'elite']:
        try:
            filtered = scanner.apply_rigorous_filters(enhanced_results, profile)
            print(f"📊 {profile.title()}: {len(filtered)}/{len(enhanced_results)} passed")
            
            for result in filtered:
                print(f"  ✅ {result.symbol}: {result.composite_score:.1f} ({result.grade}) - {result.recommendation}")
                
        except Exception as e:
            print(f"❌ {profile.title()} filtering failed: {e}")

def test_worker_thread(data_map):
    """בדיקת ה-worker thread"""
    print("\n🔗 Testing Worker Thread")
    print("-" * 40)
    
    params = {
        'scan_strategies': ['Donchian Breakout'],
        'patterns': 'HAMMER,DOJI',
        'lookback': 30,
        'use_enhanced_scan': True,
        'use_rigorous_scan': True,
        'rigorous_profile': 'conservative',
        'upper': 20,
        'lower': 10
    }
    
    print(f"Creating worker with params: {params}")
    
    try:
        worker = EnhancedWorkerThread('scan', params, data_map)
        print(f"✅ Worker created: {type(worker)}")
        
        # Test the enhanced scan method directly
        if hasattr(worker, 'run_enhanced_scan'):
            print("✅ Enhanced scan method found")
            # Note: Can't run worker in main thread, but we can test the method exists
        else:
            print("❌ Enhanced scan method not found")
            
        return worker
        
    except Exception as e:
        print(f"❌ Worker creation failed: {e}")
        return None

def simulate_ui_workflow():
    """סימולציה של תהליך הסריקה מה-UI"""
    print("\n🖥️ Simulating UI Workflow")
    print("-" * 40)
    
    # Step 1: Create data (like loading from files)
    data_map = create_test_data()
    
    # Step 2: Run enhanced scan
    enhanced_results = test_enhanced_scan(data_map)
    
    # Step 3: Apply rigorous filtering
    if enhanced_results:
        test_rigorous_filtering(enhanced_results)
    
    # Step 4: Test worker thread
    worker = test_worker_thread(data_map)
    
    print(f"\n🎯 Simulation Summary:")
    print(f"  • Data loaded: {len(data_map)} symbols")
    print(f"  • Enhanced results: {len(enhanced_results)} stocks")
    
    successful_results = [r for r in enhanced_results if r.status == "SUCCESS"]
    print(f"  • Successful scans: {len(successful_results)}")
    
    if successful_results:
        avg_score = sum(r.composite_score for r in successful_results) / len(successful_results)
        print(f"  • Average score: {avg_score:.1f}")
        
        top_result = max(successful_results, key=lambda r: r.composite_score)
        print(f"  • Top result: {top_result.symbol} ({top_result.composite_score:.1f})")

def debug_empty_results():
    """ניתוח מדוע עלולות להיות תוצאות ריקות"""
    print("\n🔍 Debugging Empty Results")
    print("-" * 40)
    
    common_issues = [
        ("No data loaded", "וודא שנטענו נתונים בתיקיית data backup"),
        ("All stocks filtered out", "הקריטריונים הנוקשים מדי - נסה Conservative"),
        ("Enhanced mode disabled", "ודא שכפתור Enhanced ON מופעל"),
        ("Rigorous mode causes empty results", "נסה לכבות Rigorous תחילה"),
        ("Technical indicators failed", "בדוק שיש מספיק נתוני מחיר (30+ ימים)"),
        ("Non-technical data missing", "ודא שקיימים קבצי JSON בתיקיית data backup")
    ]
    
    print("🔍 Common issues that can cause empty results:")
    for i, (issue, solution) in enumerate(common_issues, 1):
        print(f"  {i}. {issue}")
        print(f"     💡 {solution}")

if __name__ == "__main__":
    print("🔍 Real Scan Debug Test")
    print("=" * 50)
    
    simulate_ui_workflow()
    debug_empty_results()
    
    print("\n" + "=" * 50)
    print("🎯 Debug Test Complete!")
    print("\n💡 Quick fixes to try:")
    print("1. Make sure Enhanced ON is checked")
    print("2. Try without Rigorous mode first") 
    print("3. Check that data backup folder has JSON files")
    print("4. Try Conservative profile if using Rigorous")
    print("5. Look at console output during scan for error messages")