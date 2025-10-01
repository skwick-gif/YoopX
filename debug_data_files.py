#!/usr/bin/env python3
"""
בדיקה מפורטת של קבצי הפארקה
"""

import os
import pandas as pd
import numpy as np

def debug_parquet_files():
    """בדיקה מפורטת של קבצי הפארקה"""
    
    print("🔍 בדיקה מפורטת של קבצי PARQUET...")
    print("=" * 50)
    
    processed_dir = os.path.join('processed_data', '_parquet')
    
    if not os.path.exists(processed_dir):
        print(f"❌ התיקייה לא נמצאה: {processed_dir}")
        return
    
    files = [f for f in os.listdir(processed_dir) if f.endswith('.parquet')]
    print(f"📂 נמצאו {len(files)} קבצי parquet:")
    for f in files:
        print(f"  📄 {f}")
    
    # בדיקה מפורטת של הקובץ הראשון
    if files:
        first_file = files[0]
        file_path = os.path.join(processed_dir, first_file)
        ticker = first_file.replace('.parquet', '')
        
        print(f"\n🔬 בדיקה מפורטת של {ticker}:")
        print("-" * 30)
        
        try:
            df = pd.read_parquet(file_path)
            print(f"📊 צורת הנתונים: {df.shape}")
            print(f"📋 עמודות: {list(df.columns)}")
            print(f"📈 דוגמה מהנתונים:")
            print(df.head())
            
            # בדיקה אם יש עמודת Date
            if 'Date' in df.columns:
                print(f"\n📅 עמודת Date נמצאה:")
                df['Date'] = pd.to_datetime(df['Date'])
                print(f"   מינימום: {df['Date'].min()}")
                print(f"   מקסימום: {df['Date'].max()}")
                print(f"   סוג: {df['Date'].dtype}")
            else:
                print(f"\n❌ אין עמודת Date. בדיקת האינדקס:")
                print(f"   סוג אינדקס: {type(df.index)}")
                print(f"   אינדקס: {df.index}")
                
                # אולי התאריכים באינדקס?
                if hasattr(df.index, 'dtype') and 'datetime' in str(df.index.dtype).lower():
                    print(f"   📅 האינדקס הוא תאריכים!")
                    print(f"   מינימום: {df.index.min()}")
                    print(f"   מקסימום: {df.index.max()}")
            
            # בדיקה של עמודות חשובות
            important_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in important_cols:
                if col in df.columns:
                    print(f"✅ {col}: {df[col].dtype}")
                else:
                    print(f"❌ {col}: לא נמצא")
            
        except Exception as e:
            print(f"❌ שגיאה בקריאת הקובץ: {e}")
            import traceback
            traceback.print_exc()

def check_raw_data_too():
    """בדיקה גם של הנתונים הגולמיים"""
    
    print(f"\n🔍 בדיקה של נתונים גולמיים...")
    print("=" * 50)
    
    raw_dir = 'raw_data'
    if not os.path.exists(raw_dir):
        print("❌ תיקיית raw_data לא נמצאה")
        return
    
    files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    print(f"📂 נמצאו {len(files)} קבצי JSON:")
    
    if files:
        first_file = files[0]
        file_path = os.path.join(raw_dir, first_file)
        ticker = first_file.replace('.json', '')
        
        print(f"\n🔬 בדיקה של {ticker} (גולמי):")
        print("-" * 30)
        
        try:
            import json
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            print(f"📊 מבנה הנתונים:")
            print(f"   סוג: {type(data)}")
            if isinstance(data, dict):
                print(f"   מפתחות: {list(data.keys())}")
                
                # בדיקה אם יש נתוני מחירים
                if 'price' in data:
                    price_data = data['price']
                    print(f"   📈 נתוני מחיר: {type(price_data)}")
                    if isinstance(price_data, dict):
                        print(f"      מפתחי מחיר: {list(price_data.keys())}")
                        
                        # בדיקה של yahoo.daily
                        if 'yahoo' in price_data and 'daily' in price_data['yahoo']:
                            daily = price_data['yahoo']['daily']
                            print(f"      📅 daily: {type(daily)}, אורך: {len(daily) if hasattr(daily, '__len__') else 'N/A'}")
                            
                            if isinstance(daily, list) and daily:
                                print(f"      🔍 דוגמה ראשונה: {daily[0]}")
                                print(f"      🔍 דוגמה אחרונה: {daily[-1]}")
                
        except Exception as e:
            print(f"❌ שגיאה בקריאת הקובץ הגולמי: {e}")

if __name__ == "__main__":
    debug_parquet_files()
    check_raw_data_too()