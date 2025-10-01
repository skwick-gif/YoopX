#!/usr/bin/env python3
"""
בדיקה מה קורה עם הנתונים בבקטסטר
"""

from ml.historical_backtester_fixed import HistoricalBacktester

def debug_data_issue():
    """בדיקה מה בעצם קורה עם הנתונים"""
    
    print("🔍 בדיקה של בעיית הנתונים...")
    print("=" * 50)
    
    backtester = HistoricalBacktester()
    
    # טעינת הנתונים
    print("📊 טוען נתונים...")
    all_data = backtester._load_all_data()
    
    print(f"📈 נטענו {len(all_data)} טיקרים:")
    for ticker, df in all_data.items():
        print(f"  📊 {ticker}: צורה {df.shape}, אינדקס: {type(df.index)}")
        print(f"      עמודות: {list(df.columns)}")
        
        # בדיקת האינדקס
        if hasattr(df.index, 'dtype'):
            print(f"      סוג אינדקס: {df.index.dtype}")
        
        # בדיקת טווח תאריכים
        if hasattr(df.index, 'min'):
            print(f"      תאריכים: {df.index.min()} עד {df.index.max()}")
        
        # דוגמה מהנתונים
        print(f"      דוגמה ראשונה:")
        print(f"      {df.head(1)}")
        
        break  # רק הראשון לבדיקה
    
    # בדיקה של filter_data_until_date
    print(f"\n🔍 בדיקה של filter_data_until_date...")
    
    from ml.train_model import filter_data_until_date
    
    test_date = "2025-09-01"
    print(f"📅 מנסה לסנן עד {test_date}")
    
    filtered_data = filter_data_until_date(all_data, test_date)
    
    print(f"📊 תוצאות סינון:")
    print(f"   🎯 נשארו {len(filtered_data)} טיקרים")
    
    for ticker, df in filtered_data.items():
        print(f"   📊 {ticker}: {df.shape[0]} שורות אחרי סינון")
        if hasattr(df.index, 'max'):
            print(f"      תאריך מקסימלי: {df.index.max()}")

if __name__ == "__main__":
    debug_data_issue()