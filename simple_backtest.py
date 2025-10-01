#!/usr/bin/env python3
"""
בדיקה פשוטה עם תאריך שיש בו מספיק היסטוריה
"""

from ml.historical_backtester_fixed import HistoricalBacktester
from datetime import datetime, timedelta
import os

def simple_test():
    """בדיקה פשוטה עם תאריך עם הרבה היסטוריה"""
    
    print("🚀 בדיקה פשוטה עם תאריך עם היסטוריה...")
    print("=" * 50)
    
    backtester = HistoricalBacktester()
    
    # נבחר תאריך שיש בו המון היסטוריה - יולי 2025
    # (יש נתונים עד אוגוסט אז יולי צריך לעבוד)
    results = backtester.run_historical_backtest(
        start_date="2025-07-01",
        end_date="2025-07-01",  # רק יום אחד לבדיקה
        horizons=[1],           # רק horizon אחד
        algorithms=['rf']       # רק rf
    )
    
    summary = results.get('summary', {})
    print(f"📊 תוצאות:")
    print(f"   📊 ימים נבדקו: {summary.get('total_days_tested', 0)}")
    print(f"   🧠 מודלים אומנו: {summary.get('total_models_trained', 0)}")
    print(f"   🔍 סריקות מוצלחות: {summary.get('successful_scans', 0)}")
    
    if summary.get('total_models_trained', 0) > 0:
        print("🎉 הצלחה! המערכת מאמנת מודלים!")
    else:
        print("🤔 עדיין אין מודלים. בואו נבדוק למה...")
        
        # בדיקה ידנית של תהליך האימון
        from ml.train_model import train_multi_horizon_model, filter_data_until_date
        
        print("\n🔧 בדיקה ידנית של תהליך האימון...")
        
        # טעינת נתונים
        all_data = backtester._load_all_data()
        print(f"📊 נטענו {len(all_data)} טיקרים")
        
        # סינון עד התאריך
        test_date = "2025-07-01"
        filtered_data = filter_data_until_date(all_data, test_date)
        print(f"📅 אחרי סינון עד {test_date}: {len(filtered_data)} טיקרים")
        
        for ticker, df in filtered_data.items():
            print(f"   📊 {ticker}: {len(df)} שורות, עד {df.index.max()}")
        
        # ניסיון ישיר לאמן מודל
        if len(filtered_data) >= 2:
            print(f"\n🧠 מנסה לאמן מודל ישירות...")
            try:
                model_path = train_multi_horizon_model(
                    cutoff_date=test_date,
                    horizon_days=1,
                    algorithm='rf',
                    data_map=filtered_data
                )
                
                print(f"📈 תוצאות אימון ישיר:")
                if model_path and os.path.exists(model_path):
                    print(f"   ✅ מודל נשמר: {model_path}")
                else:
                    print(f"   ❌ מודל לא נוצר: {model_path}")
                    
            except Exception as e:
                print(f"❌ שגיאה באימון: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    simple_test()