#!/usr/bin/env python3
"""
🔍 בדיקה מדוקדקת - מה הבקטסטר באמת עושה?
===============================================

בואו נבדוק צעד אחר צעד מה קורה בבקטסטר
ומה הוא באמת בודק.
"""

from working_historical_backtester import WorkingHistoricalBacktester
import os

def debug_what_backtester_actually_does():
    """בואו נבין מה הבקטסטר באמת עושה"""
    
    print("🔍 בדיקה מדוקדקת של הבקטסטר")
    print("=" * 50)
    
    backtester = WorkingHistoricalBacktester()
    test_date = "2025-06-01"
    
    print(f"📅 בודק תאריך: {test_date}")
    print(f"❓ השאלה: איך אנחנו בודקים ביצועים אם אין לנו אימון לכל הוריזון?")
    
    # שלב 1: מה קורה בטעינת הנתונים
    print(f"\n🔄 שלב 1: טעינת נתונים")
    print("-" * 30)
    
    data_map = backtester._load_data_map_like_main_system()
    
    if data_map:
        for ticker, df in data_map.items():
            print(f"📊 {ticker}: {len(df)} שורות, {df.index.min()} עד {df.index.max()}")
    
    # שלב 2: מה קורה בסינון
    print(f"\n🔄 שלב 2: סינון נתונים עד {test_date}")
    print("-" * 30)
    
    from ml.train_model import filter_data_until_date
    filtered_data = filter_data_until_date(data_map, test_date)
    
    print(f"📂 אחרי סינון:")
    for ticker, df in filtered_data.items():
        print(f"   {ticker}: {len(df)} שורות, עד {df.index.max()}")
    
    # שלב 3: מה באמת קורה ב-train_model?
    print(f"\n🔄 שלב 3: מה train_model באמת עושה?")
    print("-" * 30)
    
    print("❓ שאלות חשובות:")
    print("1. איזה הוריזון זמן המודל מאומן עליו?")
    print("2. איך המודל יודע לחזות עתיד אם הוא לא אומן על הוריזונים הנכונים?")
    print("3. מה המשמעות של AUC שאנחנו מקבלים?")
    
    # בואו נבדוק את train_model בעומק
    print(f"\n🔬 בדיקה עמוקה של train_model...")
    
    from ml.train_model import train_model
    
    # בואו נראה מה המודל באמת מחזה
    temp_model_path = "temp_debug_model.pkl"
    
    print(f"🧠 מאמן מודל debug...")
    
    try:
        result = train_model(
            data_map=filtered_data,
            model='rf',
            model_path=temp_model_path
        )
        
        print(f"\n📊 תוצאות האימון:")
        print(f"   ✅ הצליח: {not result.get('error')}")
        
        if not result.get('error'):
            validation = result.get('validation', {})
            print(f"   📈 AUC: {validation.get('auc', 'N/A')}")
            print(f"   📊 גודל dataset: {result.get('dataset_size', 'N/A')}")
            print(f"   🎯 features: {len(result.get('features', []))}")
            
            # השאלה הגדולה: מה המודל באמת מחזה?
            print(f"\n❓ השאלה הגדולה:")
            print(f"   🤔 המודל מאומן לחזות מה בדיוק?")
            print(f"   🤔 איזה horizon זמן הוא מנבא?")
            print(f"   🤔 איך אנחנו מודדים ביצועים על נתונים עתידיים?")
            
            # בואו נבדוק את המודל שנוצר
            if os.path.exists(temp_model_path):
                from ml.train_model import load_model
                model_obj = load_model(temp_model_path)
                
                if model_obj:
                    print(f"\n🔍 פרטי המודל:")
                    print(f"   סוג: {model_obj.get('type', 'לא ידוע')}")
                    print(f"   features: {len(model_obj.get('features', []))}")
                    
                    features = model_obj.get('features', [])[:10]  # 10 ראשונים
                    print(f"   דוגמאות features: {features}")
                    
                    # השאלה: איך אנחנו יודעים שהמודל עובד נכון?
                    print(f"\n❓ בדיקת תוקפות:")
                    print(f"   🤔 מה המודל מנסה לחזות? (label)")
                    print(f"   🤔 איך אנחנו יודעים שהחיזוי נכון?")
                    print(f"   🤔 מה המשמעות של AUC ללא בדיקה על נתונים עתידיים?")
        
        else:
            print(f"   ❌ שגיאה: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ שגיאה באימון: {e}")
    
    finally:
        # ניקוי
        if os.path.exists(temp_model_path):
            os.remove(temp_model_path)
    
    # סיכום הבדיקה
    print(f"\n🎯 סיכום הבדיקה:")
    print("=" * 30)
    print("1. 📊 המערכת מאמנת מודל על נתונים היסטוריים עד תאריך מסוים")
    print("2. 🤔 אבל לא ברור איזה horizon זמן המודל מנבא")
    print("3. 📈 אנחנו מקבלים AUC אבל לא ברור מה המשמעות שלו")
    print("4. ❓ האם אנחנו באמת בודקים ביצועים היסטוריים או סתם מאמנים מודל?")
    
    print(f"\n❗ נדרש הבהרה:")
    print("- מה בדיוק המערכת בודקת?")
    print("- איך אנחנו מוודאים שהמודל עובד על נתונים עתידיים?")
    print("- מה ההבדל בין זה לבין אימון רגיל של מודל?")

if __name__ == "__main__":
    debug_what_backtester_actually_does()