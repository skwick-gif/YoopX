#!/usr/bin/env python3
"""
הרצה מלאה של הבקטסטר ההיסטורי
=====================================

בודק ביצועי המערכת על תקופות היסטוריות שונות עם מודלים מותאמי זמן.
השלב הבא אחרי הבנת הפיפליין - בדיקה מעמיקה ומציאותית.
"""

from ml.historical_backtester_fixed import HistoricalBacktester
from datetime import datetime, timedelta
import json
import os

def run_comprehensive_historical_test():
    """הרצה מקיפה של בדיקות היסטוריות"""
    
    print("🚀 מתחיל בדיקה מקיפה של הבקטסטר ההיסטורי")
    print("=" * 60)
    
    backtester = HistoricalBacktester()
    
    # 🎯 תסריט 1: בדיקה מהירה - שבועיים
    print("\n📅 תסריט 1: בדיקה מהירה (שבועיים)")
    print("-" * 40)
    
    try:
        results_quick = backtester.run_historical_backtest(
            start_date="2024-08-01",
            end_date="2024-08-15",
            horizons=[1, 5],  # 1 יום ו-5 ימים
            algorithms=['rf', 'xgb']  # Random Forest + XGBoost
        )
        
        print(f"✅ בדיקה מהירה הושלמה:")
        summary = results_quick.get('summary', {})
        print(f"   📊 ימים נבדקו: {summary.get('total_days_tested', 0)}")
        print(f"   🧠 מודלים אומנו: {summary.get('total_models_trained', 0)}")
        print(f"   🔍 סריקות מוצלחות: {summary.get('successful_scans', 0)}")
        
    except Exception as e:
        print(f"❌ שגיאה בבדיקה מהירה: {e}")
        return False
    
    # 🎯 תסריט 2: בדיקה בינונית - חודש  
    print(f"\n📅 תסריט 2: בדיקה בינונית (חודש)")
    print("-" * 40)
    
    try:
        results_medium = backtester.run_historical_backtest(
            start_date="2024-07-01", 
            end_date="2024-07-31",
            horizons=[1, 5, 10],  # כל ההוריזונים
            algorithms=['rf']  # רק RF למהירות
        )
        
        print(f"✅ בדיקה בינונית הושלמה:")
        summary = results_medium.get('summary', {})
        print(f"   📊 ימים נבדקו: {summary.get('total_days_tested', 0)}")
        print(f"   🧠 מודלים אומנו: {summary.get('total_models_trained', 0)}")
        
    except Exception as e:
        print(f"⚠️ בעיה בבדיקה בינונית: {e}")
    
    # 🎯 תסריט 3: בדיקה מעמיקה - 3 חודשים
    print(f"\n📅 תסריט 3: בדיקה מעמיקה (3 חודשים)")
    print("-" * 40)
    
    try:
        results_deep = backtester.run_historical_backtest(
            start_date="2024-04-01",
            end_date="2024-06-30", 
            horizons=[1, 5, 10],
            algorithms=['rf', 'xgb', 'lgbm']  # כל האלגוריתמים
        )
        
        print(f"✅ בדיקה מעמיקה הושלמה:")
        summary = results_deep.get('summary', {})
        print(f"   📊 ימים נבדקו: {summary.get('total_days_tested', 0)}")
        print(f"   🧠 מודלים אומנו: {summary.get('total_models_trained', 0)}")
        
    except Exception as e:
        print(f"⚠️ בעיה בבדיקה מעמיקה: {e}")
    
    # 📊 ניתוח תוצאות
    print(f"\n📊 ניתוח תוצאות כללי")
    print("=" * 60)
    
    results_dir = os.path.join('ml', 'backtest_results')
    if os.path.exists(results_dir):
        result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
        print(f"📁 נוצרו {len(result_files)} קבצי תוצאות")
        
        # ניתוח התוצאות האחרונות
        if result_files:
            latest_file = max(result_files)
            latest_path = os.path.join(results_dir, latest_file)
            
            try:
                with open(latest_path, 'r', encoding='utf-8') as f:
                    latest_results = json.load(f)
                
                print(f"📄 קובץ תוצאות אחרון: {latest_file}")
                
                config = latest_results.get('config', {})
                summary = latest_results.get('summary', {})
                
                print(f"⚙️ תצורה:")
                print(f"   📅 תקופה: {config.get('start_date')} - {config.get('end_date')}")
                print(f"   🔭 הוריזונים: {config.get('horizons', [])}")
                print(f"   🧠 אלגוריתמים: {config.get('algorithms', [])}")
                
                print(f"📈 תוצאות:")
                print(f"   📊 ימים כולל: {summary.get('total_days_tested', 0)}")
                print(f"   🧠 מודלים: {summary.get('total_models_trained', 0)}")
                print(f"   🔍 סריקות: {summary.get('successful_scans', 0)}")
                
            except Exception as e:
                print(f"⚠️ לא הצלחתי לנתח את הקובץ: {e}")
    
    # 🎯 המלצות לשלבים הבאים
    print(f"\n🎯 שלבים הבאים מומלצים:")
    print("-" * 40)
    print("1. 📊 ניתוח תוצאות מפורט - השוואת ביצועים בין אלגוריתמים")
    print("2. 📈 חישוב מדדי ביצועים - Sharpe Ratio, Max Drawdown, וכו'")
    print("3. 🔄 אופטימיזציה של היפר-פרמטרים על בסיס התוצאות")
    print("4. 🌐 הרחבה לכלל המניות במסד הנתונים")
    print("5. 🤖 אוטומציה של תהליך הבדיקה הנמשך")
    
    return True


def analyze_backtest_performance():
    """ניתוח ביצועים של תוצאות הבקטסט"""
    
    print("\n🔬 מנתח ביצועי בקטסט...")
    
    results_dir = os.path.join('ml', 'backtest_results')
    if not os.path.exists(results_dir):
        print("❌ תיקיית תוצאות לא נמצאה")
        return
    
    result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
    if not result_files:
        print("❌ לא נמצאו קבצי תוצאות")
        return
    
    print(f"📁 נמצאו {len(result_files)} קבצי תוצאות")
    
    # ניתוח כל הקבצים
    all_results = []
    for file in result_files:
        file_path = os.path.join(results_dir, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
                result['filename'] = file
                all_results.append(result)
        except Exception as e:
            print(f"⚠️ שגיאה בקריאת {file}: {e}")
    
    if not all_results:
        return
    
    # סטטיסטיקות כלליות
    total_days = sum(r.get('summary', {}).get('total_days_tested', 0) for r in all_results)
    total_models = sum(r.get('summary', {}).get('total_models_trained', 0) for r in all_results)
    total_scans = sum(r.get('summary', {}).get('successful_scans', 0) for r in all_results)
    
    print(f"\n📊 סטטיסטיקות כוללות:")
    print(f"   📅 סה\"כ ימי בדיקה: {total_days}")
    print(f"   🧠 סה\"כ מודלים שאומנו: {total_models}")
    print(f"   🔍 סה\"כ סריקות מוצלחות: {total_scans}")
    
    if total_models > 0:
        success_rate = (total_scans / total_models) * 100
        print(f"   ✅ שיעור הצלחת סריקות: {success_rate:.1f}%")
    
    # הצגת תוצאות לפי תאריכים
    print(f"\n📅 תוצאות לפי הרצות:")
    for i, result in enumerate(sorted(all_results, key=lambda x: x['filename']), 1):
        config = result.get('config', {})
        summary = result.get('summary', {})
        
        print(f"   {i}. {config.get('start_date', 'N/A')} - {config.get('end_date', 'N/A')}")
        print(f"      🧠 {summary.get('total_models_trained', 0)} מודלים, 🔍 {summary.get('successful_scans', 0)} סריקות")


def main():
    """הפונקציה הראשית"""
    
    print("🎯 הרצה מקיפה של בדיקות בקטסטר היסטורי")
    print("=" * 80)
    
    # בדיקה שהמערכת פועלת
    print("🔧 בודק שהמערכת מוכנה...")
    try:
        backtester = HistoricalBacktester()
        data = backtester._load_all_data()
        
        if not data:
            print("❌ אין נתונים זמינים. הרץ Daily Update תחילה.")
            return
        
        print(f"✅ המערכת מוכנה עם {len(data)} טיקרים")
        
    except Exception as e:
        print(f"❌ שגיאה בהכנת המערכת: {e}")
        return
    
    # הרצה מקיפה
    success = run_comprehensive_historical_test()
    
    if success:
        print(f"\n🎉 הבדיקה המקיפה הושלמה בהצלחה!")
        
        # ניתוח תוצאות
        analyze_backtest_performance()
        
        print(f"\n✨ הבקטסטר ההיסטורי מוכן לשימוש מלא!")
    else:
        print(f"\n⚠️ הבדיקה הושלמה עם בעיות. בדוק את הלוגים.")


if __name__ == "__main__":
    main()