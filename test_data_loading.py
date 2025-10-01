#!/usr/bin/env python3
"""
בדיקת טעינת נתונים ובעיות אפשריות
"""

import sys
sys.path.append('.')
from data.data_utils import load_json, load_csv, get_catalog
import os
import pandas as pd

def test_data_loading():
    print('📁 Testing data loading mechanisms...')
    
    data_folder = 'data backup'
    
    # 1. בדיקה האם יש קטלוג
    try:
        catalog = get_catalog(data_folder)
        if catalog is not None and not catalog.empty:
            print(f'✅ Catalog found: {len(catalog)} entries')
            print(f'   Sample columns: {list(catalog.columns)[:5]}')
        else:
            print('❌ No catalog found or empty')
    except Exception as e:
        print(f'❌ Catalog loading failed: {e}')
    
    # 2. בדיקת טעינת קבצים רגילים
    sample_files = [f for f in os.listdir(data_folder) if f.endswith('.json')][:3]
    
    for fname in sample_files:
        fpath = os.path.join(data_folder, fname)
        symbol = fname.replace('.json', '')
        
        try:
            df = load_json(fpath)
            if df is not None and not df.empty:
                print(f'✅ {symbol}: {len(df)} rows, columns: {list(df.columns)[:5]}')
                # בדיקת עמודות נדרשות
                required = ['Open', 'High', 'Low', 'Close', 'Volume']
                missing = [col for col in required if col not in df.columns]
                if missing:
                    print(f'   ⚠️ Missing columns: {missing}')
                
                # בדיקת אינדקס תאריכים
                if isinstance(df.index, pd.DatetimeIndex):
                    print(f'   ✅ DateTime index: {df.index.min()} to {df.index.max()}')
                else:
                    print(f'   ⚠️ Non-datetime index: {type(df.index)}')
            else:
                print(f'❌ {symbol}: Empty or None DataFrame')
        except Exception as e:
            print(f'❌ {symbol}: Loading failed - {e}')
    
    # 3. בדיקת תיקיות אחרות
    other_dirs = ['processed_data', 'raw_data', 'cache/data']
    for dir_name in other_dirs:
        if os.path.exists(dir_name):
            file_count = len([f for f in os.listdir(dir_name) if os.path.isfile(os.path.join(dir_name, f))])
            print(f'📂 {dir_name}: {file_count} files')

if __name__ == "__main__":
    test_data_loading()