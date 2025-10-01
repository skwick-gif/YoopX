#!/usr/bin/env python3
"""
בדיקה עמוקה של הנתונים הגולמיים
"""

import json
import os
from datetime import datetime

def deep_check_raw_data():
    """בדיקה עמוקה של הנתונים הגולמיים"""
    
    print("🔍 בדיקה עמוקה של נתונים גולמיים...")
    print("=" * 50)
    
    raw_dir = 'raw_data'
    if not os.path.exists(raw_dir):
        print("❌ תיקיית raw_data לא נמצאה")
        return
    
    files = [f for f in os.listdir(raw_dir) if f.endswith('.json')][:3]  # רק 3 ראשונים
    
    for file in files:
        ticker = file.replace('.json', '')
        file_path = os.path.join(raw_dir, file)
        
        print(f"\n🔬 {ticker}:")
        print("-" * 20)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # בדיקה של מבנה price
            if 'price' not in data:
                print("❌ אין מפתח 'price'")
                continue
                
            price = data['price']
            print(f"📈 price keys: {list(price.keys())}")
            
            # בדיקה של yahoo
            if 'yahoo' in price:
                yahoo = price['yahoo']
                print(f"📊 yahoo keys: {list(yahoo.keys()) if isinstance(yahoo, dict) else 'לא dict'}")
                
                # בדיקה של daily
                if isinstance(yahoo, dict) and 'daily' in yahoo:
                    daily = yahoo['daily']
                    print(f"📅 daily type: {type(daily)}")
                    print(f"📅 daily length: {len(daily) if hasattr(daily, '__len__') else 'אין אורך'}")
                    
                    if isinstance(daily, list) and len(daily) > 0:
                        # בדיקה של 3 רשומות ראשונות
                        for i, record in enumerate(daily[:3]):
                            print(f"   🔍 רשומה {i+1}: {type(record)}")
                            if isinstance(record, dict):
                                keys = list(record.keys())
                                print(f"      מפתחות: {keys}")
                                
                                # חיפוש תאריכים
                                date_keys = [k for k in keys if 'date' in k.lower()]
                                if date_keys:
                                    for dk in date_keys:
                                        print(f"      📅 {dk}: {record[dk]}")
                                
                                # חיפוש מחירים
                                price_keys = [k for k in keys if k.lower() in ['open', 'high', 'low', 'close', 'volume']]
                                if price_keys:
                                    for pk in price_keys:
                                        print(f"      💰 {pk}: {record[pk]}")
                        
                        # בדיקת התאריך האחרון
                        if len(daily) > 3:
                            print(f"   📆 רשומה אחרונה ({len(daily)}):")
                            last_record = daily[-1]
                            if isinstance(last_record, dict):
                                date_keys = [k for k in last_record.keys() if 'date' in k.lower()]
                                for dk in date_keys:
                                    print(f"      📅 {dk}: {last_record[dk]}")
                
            # בדיקה של updated_at ו-collected_at
            if 'updated_at' in data:
                print(f"🕐 updated_at: {data['updated_at']}")
            if 'collected_at' in data:
                print(f"🕐 collected_at: {data['collected_at']}")
            if 'date_range' in data:
                print(f"📅 date_range: {data['date_range']}")
                
        except Exception as e:
            print(f"❌ שגיאה: {e}")

def test_load_single_ticker():
    """בדיקה של טעינת טיקר יחיד דרך המערכת"""
    
    print(f"\n🧪 בדיקה של טעינת טיקר דרך המערכת...")
    print("=" * 50)
    
    try:
        # יבוא הפונקציות הנדרשות
        from ml.historical_backtester_fixed import HistoricalBacktester
        
        backtester = HistoricalBacktester()
        
        # ניסיון לטעון נתונים
        data = backtester._load_all_data()
        
        print(f"📊 טוען נתונים...")
        print(f"   🎯 נטענו {len(data)} טיקרים")
        
        if data:
            # בדיקה של הטיקר הראשון
            first_ticker = list(data.keys())[0]
            df = data[first_ticker]
            
            print(f"\n🔍 בדיקה של {first_ticker}:")
            print(f"   📊 צורת נתונים: {df.shape}")
            print(f"   📋 עמודות: {list(df.columns)}")
            print(f"   📅 אינדקס: {type(df.index)}")
            
            if hasattr(df.index, 'dtype') and 'datetime' in str(df.index.dtype).lower():
                print(f"   📆 תאריכים: {df.index.min()} עד {df.index.max()}")
                
                # דוגמה מהנתונים
                print(f"\n📈 דוגמה מהנתונים:")
                print(df.head())
                
        else:
            print("❌ לא נטענו נתונים")
        
    except Exception as e:
        print(f"❌ שגיאה בטעינה: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deep_check_raw_data()
    test_load_single_ticker()