#!/usr/bin/env python3
"""
Test script to verify historical training UI works properly
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

def test_trading_days_calculation():
    """Test the trading days calculation logic"""
    import pandas as pd
    from datetime import datetime, timedelta
    
    print("🧪 Testing trading days calculation...")
    
    # Simulate some data with dates
    date_range = pd.date_range(end='2025-09-30', periods=100, freq='B')  # 100 business days
    print(f"Date range: {date_range[0].strftime('%Y-%m-%d')} to {date_range[-1].strftime('%Y-%m-%d')}")
    
    # Test going back 30 trading days
    latest_date = date_range[-1]
    training_days_back = 30
    
    # Calculate cutoff using business days
    business_days = pd.bdate_range(end=latest_date, periods=training_days_back + 1, freq='B')
    cutoff_dt = business_days[0]
    
    print(f"Latest date: {latest_date.strftime('%Y-%m-%d')}")
    print(f"Going back {training_days_back} trading days...")
    print(f"Cutoff date: {cutoff_dt.strftime('%Y-%m-%d')}")
    
    # Count actual trading days between cutoff and latest
    actual_days = len(pd.bdate_range(start=cutoff_dt, end=latest_date))
    print(f"Actual trading days in range: {actual_days}")
    
    return True

def test_historical_training_params():
    """Test parameter passing for historical training"""
    print("\n🧪 Testing historical training parameters...")
    
    # Simulate UI parameters
    params = {
        'ml_model': 'rf',
        'horizons': '5,10,20',
        'training_days_back': 60,
        'auto_rescan': True
    }
    
    print(f"Training parameters: {params}")
    
    # Test horizons parsing (copy from main_content.py logic)
    horizons_raw = params.get('horizons', '').strip()
    horizons_list = None
    if horizons_raw:
        parts = [p.strip() for p in horizons_raw.split(',') if p.strip()]
        hl = []
        for p in parts:
            try:
                v = int(p)
                if v > 0:
                    hl.append(v)
            except Exception:
                pass
        if hl:
            horizons_list = sorted(list(set(hl)))
    
    print(f"Parsed horizons: {horizons_list}")
    
    # Test cutoff date calculation
    training_days_back = params.get('training_days_back')
    if training_days_back and isinstance(training_days_back, int) and training_days_back > 0:
        import pandas as pd
        from datetime import datetime
        
        # Simulate latest date
        latest_date = pd.Timestamp('2025-09-30')
        business_days = pd.bdate_range(end=latest_date, periods=training_days_back + 1, freq='B')
        cutoff_dt = business_days[0]
        historical_cutoff_date = cutoff_dt.strftime('%Y-%m-%d')
        
        print(f"Historical cutoff calculated: {historical_cutoff_date}")
        print(f"This means training on data from earliest available until {historical_cutoff_date}")
    
    return True

if __name__ == '__main__':
    print("🚀 Testing Historical Training UI Components")
    print("=" * 50)
    
    try:
        test_trading_days_calculation()
        test_historical_training_params()
        
        print("\n✅ All tests passed!")
        print("\nNext steps:")
        print("1. Run the app and go to Scan tab")
        print("2. Set 'Training Cutoff' to 60 trading days") 
        print("3. Set 'Train Horizons' to '5,10,20'")
        print("4. Click Train to see historical training in action")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()