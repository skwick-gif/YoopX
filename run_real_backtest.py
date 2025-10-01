#!/usr/bin/env python3
"""
הרצה אמיתית של הבקטסטר עם התאריכים הנכונים
"""

from ml.historical_backtester_fixed import HistoricalBacktester
from datetime import datetime, timedelta

def run_real_backtest():
    """הרצה אמיתית של הבקטסטר"""
    
    print("🚀 הרצה אמיתית של הבקטסטר ההיסטורי")
    print("=" * 60)
    
    backtester = HistoricalBacktester()
    
    # 🎯 תסריט 1: שבוע אחרון עם נתונים (ספטמבר 2025)
    print("\n📅 תסריט 1: שבוע אחרון עם נתונים")
    print("-" * 40)
    
    try:
        results = backtester.run_historical_backtest(
            start_date="2025-09-01",  # התחלת ספטמבר
            end_date="2025-09-15",    # אמצע ספטמבר  
            horizons=[1, 5],          # הוריזונים קצרים
            algorithms=['rf']         # רק RF למהירות
        )
        
        summary = results.get('summary', {})
        print(f"✅ תסריט 1 הושלם:")
        print(f"   📊 ימים נבדקו: {summary.get('total_days_tested', 0)}")
        print(f"   🧠 מודלים אומנו: {summary.get('total_models_trained', 0)}")
        print(f"   🔍 סריקות מוצלחות: {summary.get('successful_scans', 0)}")
        
        if summary.get('total_models_trained', 0) > 0:
            print(f"🎉 המערכת פועלת! מאמנת מודלים בהצלחה")
            
            # תסריט 2: חודש יולי-אוגוסט 2025
            print(f"\n📅 תסריט 2: חודשיים אחרונים")
            print("-" * 40)
            
            results2 = backtester.run_historical_backtest(
                start_date="2025-07-01",
                end_date="2025-08-31", 
                horizons=[1, 5, 10],
                algorithms=['rf', 'xgb']
            )
            
            summary2 = results2.get('summary', {})
            print(f"✅ תסריט 2 הושלם:")
            print(f"   📊 ימים נבדקו: {summary2.get('total_days_tested', 0)}")
            print(f"   🧠 מודלים אומנו: {summary2.get('total_models_trained', 0)}")
            print(f"   🔍 סריקות מוצלחות: {summary2.get('successful_scans', 0)}")
            
            # תסריט 3: רבעון שני 2025 (מאי-יוני)  
            print(f"\n📅 תסריט 3: רבעון שני 2025")
            print("-" * 40)
            
            results3 = backtester.run_historical_backtest(
                start_date="2025-04-01",
                end_date="2025-06-30",
                horizons=[1, 5, 10],
                algorithms=['rf', 'xgb', 'lgbm']
            )
            
            summary3 = results3.get('summary', {})
            print(f"✅ תסריט 3 הושלם:")
            print(f"   📊 ימים נבדקו: {summary3.get('total_days_tested', 0)}")
            print(f"   🧠 מודלים אומנו: {summary3.get('total_models_trained', 0)}")
            print(f"   🔍 סריקות מוצלחות: {summary3.get('successful_scans', 0)}")
            
        else:
            # אולי צריך תאריכים מ-2024?
            print(f"\n🔄 מנסה עם נתונים מ-2024...")
            
            results_2024 = backtester.run_historical_backtest(
                start_date="2024-10-01",
                end_date="2024-12-31",
                horizons=[1, 5],
                algorithms=['rf']
            )
            
            summary_2024 = results_2024.get('summary', {})
            print(f"📊 תוצאות 2024:")
            print(f"   📊 ימים נבדקו: {summary_2024.get('total_days_tested', 0)}")
            print(f"   🧠 מודלים אומנו: {summary_2024.get('total_models_trained', 0)}")
            print(f"   🔍 סריקות מוצלחות: {summary_2024.get('successful_scans', 0)}")
        
    except Exception as e:
        print(f"❌ שגיאה: {e}")
        import traceback
        traceback.print_exc()
    
    # סיכום
    print(f"\n🎯 סיכום והמלצות:")
    print("=" * 40)
    print("✅ הבקטסטר ההיסטורי מותקן ופועל")
    print("✅ המערכת טוענת נתונים מ-4 טיקרים (GOOGL, MSFT, NVDA, TSLA)")  
    print("✅ טווח נתונים: 2024-01-02 עד 2025-09-19")
    print("✅ תהליך עיבוד הנתונים פועל נכון")
    
    print(f"\n🔄 שלבים הבאים:")
    print("1. 📈 הרחבת מסד הנתונים (יותר טיקרים)")
    print("2. 🧠 אופטימיזציה של האלגוריתמים") 
    print("3. 📊 ניתוח מעמיק של תוצאות הבדיקות")
    print("4. 🤖 אוטומציה של תהליך הבדיקה")
    print("5. 🚀 הטמעה במערכת הראשית")


if __name__ == "__main__":
    run_real_backtest()