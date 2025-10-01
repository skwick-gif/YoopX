#!/usr/bin/env python3
"""
בדיקת מערכת האימון ההיסטורית
"""

import sys
sys.path.append('.')
from ml.train_model import train_model, filter_data_until_date, train_multi_horizon_model
from data.data_utils import load_json
import os
from datetime import datetime, timedelta

def test_historical_training():
    print('🕰️ Testing historical training system...')
    
    # טען נתונים לדוגמה
    data_map = {}
    data_folder = 'data backup'
    sample_files = [f for f in os.listdir(data_folder) if f.endswith('.json')][:5]
    
    for f in sample_files:
        try:
            df = load_json(os.path.join(data_folder, f))
            symbol = f.replace('.json', '')
            data_map[symbol] = df
        except Exception as e:
            print(f'❌ {f}: {e}')
            
    print(f'✅ Loaded {len(data_map)} symbols for historical testing')
    
    # 1. בדיקת סינון נתונים לפי תאריך
    cutoff_date = '2025-06-01'
    print(f'📅 Testing data filtering until {cutoff_date}')
    
    try:
        filtered_data = filter_data_until_date(data_map, cutoff_date)
        print(f'✅ Filtered data: {len(filtered_data)} symbols')
        
        # בדיקה שהסינון עבד
        for symbol, df in filtered_data.items():
            if not df.empty:
                latest_date = df.index.max()
                print(f'   {symbol}: latest date = {latest_date.strftime("%Y-%m-%d")}')
                break
                
    except Exception as e:
        print(f'❌ Data filtering failed: {e}')
        return
    
    # 2. בדיקת אימון היסטורי עם horizon יחיד
    print(f'🧠 Testing single horizon historical training')
    
    try:
        model_path = train_multi_horizon_model(
            cutoff_date=cutoff_date,
            horizon_days=5,
            algorithm='rf',
            data_map=filtered_data
        )
        
        if model_path and os.path.exists(model_path):
            print(f'✅ Historical model trained successfully: {model_path}')
        else:
            print(f'❌ Historical model training failed or file not found')
            
    except Exception as e:
        print(f'❌ Historical training failed: {e}')
        import traceback
        traceback.print_exc()
    
    # 3. בדיקת אימון רב-אופקי
    print(f'🎯 Testing multi-horizon training')
    
    try:
        result = train_model(
            data_map=filtered_data,
            model='rf',
            multi_horizons=[5, 10],
            model_path='test_multi_horizon.pkl'
        )
        
        if result and not result.get('error'):
            print(f'✅ Multi-horizon training successful')
            print(f'   Horizons: {result.get("horizons")}')
            print(f'   Models: {len(result.get("horizon_models", []))}')
        else:
            print(f'❌ Multi-horizon training failed: {result.get("error")}')
            
    except Exception as e:
        print(f'❌ Multi-horizon training failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_historical_training()