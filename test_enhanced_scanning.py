"""
Test Enhanced Scanning System
=============================
Quick test to verify the enhanced scanning components work together
"""

import os
import sys
import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def test_non_technical_loader():
    """Test the non-technical data loader"""
    print("🧪 Testing Non-Technical Data Loader...")
    
    try:
        from data.non_technical_loader import NonTechnicalDataLoader
        
        loader = NonTechnicalDataLoader()
        
        # Test with available symbols
        test_symbols = ['MSFT', 'GOOGL', 'TSLA']
        results = {}
        
        for symbol in test_symbols:
            print(f"  Loading {symbol}...")
            
            fundamentals = loader.get_company_fundamentals(symbol)
            profile = loader.get_company_profile(symbol)
            scores = loader.get_company_scores(symbol)
            
            if scores:
                results[symbol] = {
                    'fundamental_score': scores.fundamental_score,
                    'sector_score': scores.sector_score,
                    'business_quality_score': scores.business_quality_score,
                    'size_category': scores.size_category,
                    'financial_strength': scores.financial_strength
                }
                
                print(f"    ✅ {symbol}: Score={scores.fundamental_score:.1f}, Sector={profile.sector if profile else 'Unknown'}")
            else:
                print(f"    ❌ {symbol}: No data available")
        
        print(f"  📊 Loaded data for {len(results)} symbols")
        return len(results) > 0
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_enhanced_scanner():
    """Test the enhanced scanner engine"""
    print("\n🧪 Testing Enhanced Scanner Engine...")
    
    try:
        from logic.enhanced_scanner import EnhancedScanEngine
        import pandas as pd
        import numpy as np
        
        # Create mock data for testing
        data_map = {}
        
        for symbol in ['MSFT', 'GOOGL']:
            # Generate sample OHLCV data
            dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
            np.random.seed(42)  # For reproducible results
            
            # Generate realistic price data
            base_price = 100
            price_changes = np.random.normal(0, 0.02, len(dates))
            prices = [base_price]
            
            for change in price_changes[1:]:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1))  # Ensure positive prices
            
            df = pd.DataFrame({
                'Open': prices,
                'High': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'Low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'Close': prices,
                'Volume': np.random.randint(1000000, 10000000, len(dates))
            }, index=dates)
            
            data_map[symbol] = df
            print(f"  📈 Created mock data for {symbol}: {len(df)} days")
        
        # Test enhanced scanning
        engine = EnhancedScanEngine(data_map)
        
        params = {
            'scan_strategy': 'Donchian Breakout',
            'upper': 20,
            'lower': 10,
            'patterns': 'ENGULFING,DOJI',
            'lookback': 30,
            'use_enhanced_scan': True
        }
        
        symbols = list(data_map.keys())
        print(f"  🔍 Starting enhanced scan for {symbols}...")
        
        results = engine.bulk_scan_enhanced(symbols, params)
        
        print(f"  📋 Scan Results:")
        for result in results:
            if result.status == "SUCCESS":
                print(f"    ✅ {result.symbol}: Composite={result.composite_score:.1f}, Grade={result.grade}, Rec={result.recommendation}")
            else:
                print(f"    ❌ {result.symbol}: {result.error_message}")
        
        return len([r for r in results if r.status == "SUCCESS"]) > 0
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_worker():
    """Test the enhanced worker thread creation"""
    print("\n🧪 Testing Enhanced Worker Thread...")
    
    try:
        from ui.enhanced_worker_thread import create_worker_thread
        
        params = {
            'use_enhanced_scan': True,
            'symbols': 'MSFT,GOOGL',
            'scan_strategy': 'Donchian Breakout'
        }
        
        worker = create_worker_thread('scan', params, {}, use_enhanced=True)
        
        if worker:
            print(f"  ✅ Enhanced worker thread created: {type(worker).__name__}")
            return True
        else:
            print(f"  ❌ Failed to create worker thread")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Enhanced Scanning System Test Suite")
    print("=" * 50)
    
    start_time = datetime.datetime.now()
    
    tests = [
        ("Non-Technical Data Loader", test_non_technical_loader),
        ("Enhanced Scanner Engine", test_enhanced_scanner),
        ("Enhanced Worker Thread", test_enhanced_worker),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n📊 Test Results Summary (Duration: {duration:.2f}s)")
    print("-" * 50)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced scanning system is ready.")
    elif passed > total // 2:
        print("⚠️ Most tests passed. System should work with some limitations.")  
    else:
        print("🔥 Many tests failed. System needs attention before use.")

if __name__ == "__main__":
    main()