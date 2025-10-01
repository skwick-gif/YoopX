#!/usr/bin/env python3
"""
🚀 הרצה מורחבת של הבקטסטר ההיסטורי
=====================================

עכשיו שהבקטסטר עובד, בואו נריץ אותו על תקופות שונות
ונשווה ביצועים.
"""

from working_historical_backtester import WorkingHistoricalBacktester
import pandas as pd
from datetime import datetime, timedelta
import json
import os

def run_extended_backtest():
    """הרצה מורחבת על תאריכים שונים"""
    
    print("🚀 הרצה מורחבת של הבקטסטר ההיסטורי")
    print("=" * 60)
    
    backtester = WorkingHistoricalBacktester()
    
    # תאריכים לבדיקה
    test_dates = [
        "2025-03-01",  # מרץ 2025
        "2025-04-01",  # אפריל 2025  
        "2025-05-01",  # מאי 2025
        "2025-06-01",  # יוני 2025
        "2025-07-01",  # יולי 2025
        "2025-08-01"   # אוגוסט 2025
    ]
    
    results = []
    
    for i, test_date in enumerate(test_dates, 1):
        print(f"\n📅 בדיקה {i}/{len(test_dates)}: {test_date}")
        print("-" * 40)
        
        try:
            result = backtester.run_simple_backtest(test_date)
            
            if result['success']:
                steps = result.get('steps', {})
                model_info = steps.get('model_trained', {}).get('training_meta', {})
                
                summary = {
                    'test_date': test_date,
                    'success': True,
                    'tickers_count': steps.get('data_loaded', {}).get('tickers_count', 0),
                    'validation_auc': model_info.get('validation_auc'),
                    'dataset_size': model_info.get('dataset_size'),
                    'features_count': model_info.get('features_count')
                }
                
                print(f"   ✅ הצלחה!")
                print(f"   📊 AUC: {summary['validation_auc']:.4f}")
                print(f"   🎯 גודל dataset: {summary['dataset_size']}")
                print(f"   📈 מספר features: {summary['features_count']}")
                
            else:
                summary = {
                    'test_date': test_date,
                    'success': False,
                    'error': result.get('error', 'לא ידועה')
                }
                print(f"   ❌ כשלון: {summary['error']}")
            
            results.append(summary)
            
        except Exception as e:
            print(f"   ❌ שגיאה: {e}")
            results.append({
                'test_date': test_date,
                'success': False,
                'error': str(e)
            })
    
    # ניתוח תוצאות
    print(f"\n📊 ניתוח תוצאות כללי")
    print("=" * 60)
    
    successful_runs = [r for r in results if r['success']]
    failed_runs = [r for r in results if not r['success']]
    
    print(f"✅ הרצות מוצלחות: {len(successful_runs)}/{len(results)}")
    print(f"❌ הרצות כושלות: {len(failed_runs)}")
    
    if successful_runs:
        aucs = [r['validation_auc'] for r in successful_runs if r['validation_auc'] is not None]
        dataset_sizes = [r['dataset_size'] for r in successful_runs if r['dataset_size'] is not None]
        
        if aucs:
            print(f"\n📈 סטטיסטיקות AUC:")
            print(f"   ממוצע: {sum(aucs)/len(aucs):.4f}")
            print(f"   מינימום: {min(aucs):.4f}")
            print(f"   מקסימום: {max(aucs):.4f}")
        
        if dataset_sizes:
            print(f"\n📊 גדלי Dataset:")
            print(f"   ממוצע: {sum(dataset_sizes)/len(dataset_sizes):.0f}")
            print(f"   מינימום: {min(dataset_sizes)}")
            print(f"   מקסימום: {max(dataset_sizes)}")
    
    # שמירת תוצאות
    results_file = f"ml/backtest_results/extended_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 תוצאות נשמרו: {results_file}")
    
    # המלצות
    print(f"\n🎯 המלצות לשלבים הבאים:")
    print("-" * 40)
    
    if successful_runs:
        avg_auc = sum(r['validation_auc'] for r in successful_runs if r['validation_auc']) / len([r for r in successful_runs if r['validation_auc']])
        
        if avg_auc < 0.55:
            print("📈 שיפור נדרש באיכות המודל:")
            print("   • הוספת features נוספים")
            print("   • כוונון היפר-פרמטרים")
            print("   • ניסוי אלגוריתמים שונים (XGB, LGBM)")
        
        if len(successful_runs) == len(results):
            print("✅ כל ההרצות הצליחו - המערכת יציבה!")
            print("📊 מוכן לבדיקות סריקה היסטוריות")
        else:
            print("⚠️ חלק מההרצות כשלו - בדוק טווחי נתונים")
    
    print("🚀 הבקטסטר ההיסטורי מוכן לשימוש מתקדם!")
    
    return results

def compare_algorithms():
    """השוואה בין אלגוריתמים שונים"""
    
    print(f"\n🤖 השוואת אלגוריתמים")
    print("=" * 40)
    
    # TODO: להוסיף תמיכה באלגוריתמים שונים בבקטסטר
    print("⚠️ השוואת אלגוריתמים תתווסף בגרסה הבאה")
    print("   • RF (Random Forest) - כרגע זמין")
    print("   • XGB (XGBoost) - לפיתוח")
    print("   • LGBM (LightGBM) - לפיתוח")

if __name__ == "__main__":
    results = run_extended_backtest()
    compare_algorithms()