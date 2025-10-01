"""
Enhanced Scanning System Demo
=============================
Comprehensive demonstration of the new enhanced scanning capabilities
integrating technical analysis with fundamental analysis and business intelligence.
"""

import os
import sys
import datetime
import json

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def run_enhanced_scan_demo():
    """Run a complete enhanced scanning demonstration"""
    
    print("🎯 Enhanced Scanning System Demo")
    print("=" * 60)
    print("Demonstrating integration of:")
    print("  📈 Technical Analysis (signals, patterns, age)")  
    print("  💰 Fundamental Analysis (PE, ROE, debt ratios)")
    print("  🏢 Business Intelligence (sector, employees, quality)")
    print("  🔮 Composite Scoring & Recommendations")
    print()
    
    # Import components
    try:
        from data.non_technical_loader import NonTechnicalDataLoader
        from logic.enhanced_scanner import EnhancedScanEngine
        import pandas as pd
        import numpy as np
        
        # Initialize components
        print("🔧 Initializing Enhanced Scanning Engine...")
        non_tech_loader = NonTechnicalDataLoader()
        
        # Get real symbols that have data
        print("🔍 Discovering available symbols...")
        available_symbols = []
        test_symbols = ['MSFT', 'GOOGL', 'AAPL', 'TSLA', 'NVDA', 'META', 'AMZN', 'JPM', 'JNJ', 'PG']
        
        for symbol in test_symbols:
            scores = non_tech_loader.get_company_scores(symbol)
            if scores and scores.fundamental_score > 0:
                available_symbols.append(symbol)
                if len(available_symbols) >= 6:  # Limit for demo
                    break
        
        print(f"  📊 Found {len(available_symbols)} symbols with complete data: {available_symbols}")
        
        # Create enhanced price data (more realistic than pure random)
        print("📈 Generating realistic market data...")
        data_map = {}
        
        for i, symbol in enumerate(available_symbols):
            # Create realistic price movements
            days = 252  # One trading year
            dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
            
            # Base price varies by symbol
            base_prices = {'MSFT': 300, 'GOOGL': 150, 'AAPL': 180, 'TSLA': 200, 
                          'NVDA': 500, 'META': 350, 'AMZN': 140, 'JPM': 150, 'JNJ': 160, 'PG': 140}
            base_price = base_prices.get(symbol, 100)
            
            # Generate price series with trend and volatility
            np.random.seed(42 + i)  # Different seed per symbol
            
            # Trend factor (some stocks trend up, others sideways)
            trend = 0.0002 if i % 2 == 0 else -0.0001
            volatility = 0.015 + (i * 0.002)  # Varying volatility
            
            prices = [base_price]
            for day in range(1, days):
                daily_return = np.random.normal(trend, volatility)
                new_price = prices[-1] * (1 + daily_return)
                prices.append(max(new_price, 1))
            
            # Create OHLCV data
            df_data = []
            for j, close_price in enumerate(prices):
                # Intraday range
                daily_range = close_price * np.random.uniform(0.005, 0.025)
                high = close_price + np.random.uniform(0, daily_range * 0.7)
                low = close_price - np.random.uniform(0, daily_range * 0.7) 
                open_price = low + np.random.uniform(0, high - low)
                volume = np.random.randint(1000000, 50000000)
                
                df_data.append({
                    'Open': open_price,
                    'High': high,
                    'Low': low,
                    'Close': close_price,
                    'Volume': volume
                })
            
            df = pd.DataFrame(df_data, index=dates)
            data_map[symbol] = df
            
            print(f"  📊 {symbol}: {len(df)} days, Price Range: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}")
        
        # Initialize enhanced scanner
        engine = EnhancedScanEngine(data_map)
        
        print(f"\n🎛️ Configuring Scan Parameters...")
        scan_params = {
            'scan_strategy': 'Donchian Breakout',
            'upper': 20,
            'lower': 10,
            'patterns': 'ENGULFING,DOJI,HAMMER',
            'lookback': 30,
            'rr_target': '2xATR',
            'min_rr': 1.5,
            'use_enhanced_scan': True,
            'include_fundamentals': True,
            'include_sector_analysis': True,
            'include_business_quality': True,
            'max_results': 10
        }
        
        print("  📋 Scan Configuration:")
        print(f"    Strategy: {scan_params['scan_strategy']}")
        print(f"    Breakout Periods: Upper={scan_params['upper']}, Lower={scan_params['lower']}")
        print(f"    Pattern Recognition: {scan_params['patterns']}")
        print(f"    Risk Management: Min R:R = {scan_params['min_rr']}")
        print(f"    Enhanced Features: Fundamentals + Sector + Business Quality")
        
        print(f"\n🔄 Running Enhanced Scan...")
        start_time = datetime.datetime.now()
        
        results = engine.bulk_scan_enhanced(available_symbols, scan_params)
        
        end_time = datetime.datetime.now()
        scan_duration = (end_time - start_time).total_seconds()
        
        print(f"  ⏱️ Scan completed in {scan_duration:.2f} seconds")
        print(f"  📊 Processed {len(results)} symbols")
        
        # Display results
        print(f"\n📈 ENHANCED SCAN RESULTS")
        print("=" * 60)
        
        successful_results = [r for r in results if r.status == "SUCCESS"]
        failed_results = [r for r in results if r.status == "ERROR"]
        
        if successful_results:
            # Sort by composite score
            successful_results.sort(key=lambda x: x.composite_score, reverse=True)
            
            print(f"🎯 Top Results (sorted by Composite Score):")
            print()
            
            for i, result in enumerate(successful_results):
                print(f"#{i+1}: {result.symbol} - {result.long_name[:40]}{'...' if len(result.long_name) > 40 else ''}")
                print(f"     🎯 Composite Score: {result.composite_score:.1f}/100 | Grade: {result.grade} | Recommendation: {result.recommendation}")
                print(f"     📊 Technical: {result.technical_signal} ({result.technical_age} days old) | Price: ${result.price_at_signal:.2f}")
                pe_text = f"{result.pe_ratio:.1f}" if result.pe_ratio else 'N/A'
                roe_text = f"{result.roe*100:.1f}%" if result.roe else 'N/A'
                print(f"     💰 Fundamental: Score={result.fundamental_score:.1f} | PE={pe_text} | ROE={roe_text}")
                employee_text = f" | {result.employee_count:,} employees" if result.employee_count else ""
                print(f"     🏢 Business: {result.sector} | {result.financial_strength}{employee_text}")
                print(f"     ⚠️ Risk Level: {result.risk_level} | Size: {result.size_category}")
                
                if result.patterns:
                    print(f"     📊 Patterns: {', '.join(result.patterns)}")
                    
                print()
        
        if failed_results:
            print(f"❌ Failed to analyze {len(failed_results)} symbols:")
            for result in failed_results:
                print(f"  {result.symbol}: {result.error_message}")
            print()
        
        # Generate summary statistics
        if successful_results:
            print(f"📊 SCAN SUMMARY")
            print("-" * 30)
            
            # Score statistics
            scores = [r.composite_score for r in successful_results]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            print(f"Composite Scores: Avg={avg_score:.1f}, Max={max_score:.1f}, Min={min_score:.1f}")
            
            # Signal distribution
            signals = {}
            for result in successful_results:
                signal = result.technical_signal
                signals[signal] = signals.get(signal, 0) + 1
            print(f"Technical Signals: {dict(signals)}")
            
            # Sector distribution
            sectors = {}
            for result in successful_results:
                if result.sector:
                    sectors[result.sector] = sectors.get(result.sector, 0) + 1
            print(f"Sector Distribution: {dict(sectors)}")
            
            # Recommendation distribution
            recommendations = {}
            for result in successful_results:
                rec = result.recommendation
                recommendations[rec] = recommendations.get(rec, 0) + 1
            print(f"Recommendations: {dict(recommendations)}")
            
            # Risk distribution
            risks = {}
            for result in successful_results:
                risk = result.risk_level
                risks[risk] = risks.get(risk, 0) + 1
            print(f"Risk Levels: {dict(risks)}")
        
        # Demonstrate filtering
        print(f"\n🔍 ENHANCED FILTERING DEMO")
        print("-" * 30)
        
        filters = {
            'min_composite_score': 75,
            'technical_signals': ['Buy'],
            'max_risk': 'MEDIUM',
            'grades': ['A+', 'A', 'A-', 'B+']
        }
        
        print("Applying filters:")
        for key, value in filters.items():
            print(f"  {key}: {value}")
        
        filtered_results = engine.filter_results(successful_results, filters)
        print(f"\nFiltered Results: {len(filtered_results)} symbols match criteria")
        
        for result in filtered_results:
            print(f"  ✅ {result.symbol}: Score={result.composite_score:.1f}, Signal={result.technical_signal}, Risk={result.risk_level}")
        
        # Demonstrate top picks
        print(f"\n🏆 TOP PICKS")
        print("-" * 15)
        
        top_picks = engine.get_top_picks(successful_results, 3)
        print("Top 3 recommendations based on composite scoring:")
        
        for i, result in enumerate(top_picks):
            print(f"\n🥇 #{i+1}: {result.symbol}")
            print(f"   Composite Score: {result.composite_score:.1f}/100")
            print(f"   Grade: {result.grade}")  
            print(f"   Recommendation: {result.recommendation}")
            print(f"   Reasoning: Strong {result.technical_signal} signal with {result.financial_strength.lower()} fundamentals")
            if result.sector:
                print(f"   Sector: {result.sector} ({result.risk_level.lower()} risk)")
        
        print(f"\n🎉 Enhanced Scanning Demo Completed Successfully!")
        print(f"   Total Processing Time: {scan_duration:.2f} seconds")
        print(f"   Symbols Analyzed: {len(successful_results)}/{len(results)}")
        print(f"   Data Sources: Technical + Fundamental + Business Intelligence")
        print(f"   Advanced Features: ✅ Composite Scoring ✅ Smart Filtering ✅ Risk Assessment")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(f"🚀 Starting Enhanced Scanning Demo at {datetime.datetime.now()}")
    print()
    
    success = run_enhanced_scan_demo()
    
    print(f"\n{'🎉 Demo completed successfully!' if success else '❌ Demo failed!'}")
    print(f"Time: {datetime.datetime.now()}")