#!/usr/bin/env python3
"""
בדיקה של טווח הנתונים הזמינים למעבר לבדיקות אמיתיות
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import json

def check_data_range():
    """בודק את הטווח האמיתי של הנתונים"""
    
    print("🔍 בודק טווח נתונים זמינים...")
    print("=" * 50)
    
    processed_data_dir = os.path.join('processed_data', '_parquet')
    if not os.path.exists(processed_data_dir):
        print("❌ תיקיית processed_data/_parquet לא נמצאה")
        return
    
    # עובר על כל הקבצים
    all_dates = []
    ticker_info = {}
    
    for file in os.listdir(processed_data_dir):
        if not file.endswith('.parquet'):
            continue
            
        ticker = file.replace('.parquet', '')
        file_path = os.path.join(processed_data_dir, file)
        
        try:
            df = pd.read_parquet(file_path)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                min_date = df['Date'].min()
                max_date = df['Date'].max()
                record_count = len(df)
                
                all_dates.extend(df['Date'].tolist())
                ticker_info[ticker] = {
                    'min_date': min_date,
                    'max_date': max_date,
                    'records': record_count,
                    'file_size': os.path.getsize(file_path)
                }
                
                print(f"📊 {ticker}:")
                print(f"   📅 מ-{min_date.strftime('%Y-%m-%d')} עד {max_date.strftime('%Y-%m-%d')}")
                print(f"   📈 {record_count:,} רשומות")
                
        except Exception as e:
            print(f"⚠️ שגיאה בקריאת {ticker}: {e}")
    
    if all_dates:
        global_min = min(all_dates)
        global_max = max(all_dates)
        
        print(f"\n📈 סיכום כללי:")
        print(f"   📅 טווח כללי: {global_min.strftime('%Y-%m-%d')} - {global_max.strftime('%Y-%m-%d')}")
        print(f"   🗂️ סה\"כ טיקרים: {len(ticker_info)}")
        print(f"   📊 סה\"כ רשומות: {len(all_dates):,}")
        
        # המלצות לתקופות בדיקה
        print(f"\n🎯 תקופות מומלצות לבדיקה:")
        print(f"   🚀 בדיקה מהירה (שבוע): {(global_max - timedelta(days=7)).strftime('%Y-%m-%d')} - {global_max.strftime('%Y-%m-%d')}")
        print(f"   📊 בדיקה בינונית (חודש): {(global_max - timedelta(days=30)).strftime('%Y-%m-%d')} - {global_max.strftime('%Y-%m-%d')}")
        print(f"   🔬 בדיקה מעמיקה (3 חודשים): {(global_max - timedelta(days=90)).strftime('%Y-%m-%d')} - {global_max.strftime('%Y-%m-%d')}")
        
        return global_min, global_max, ticker_info
    
    else:
        print("❌ לא נמצאו נתונים תקינים")
        return None, None, {}


def run_proper_backtest():
    """הרצת בדיקה עם התאריכים הנכונים"""
    
    print("\n🎯 מריץ בדיקה עם תאריכים אמיתיים...")
    print("=" * 50)
    
    # בדיקת טווח נתונים
    min_date, max_date, ticker_info = check_data_range()
    
    if not max_date:
        print("❌ לא ניתן לקבוע טווח נתונים")
        return
    
    # יבוא הבקטסטר
    try:
        from ml.historical_backtester_fixed import HistoricalBacktester
        backtester = HistoricalBacktester()
        
    except Exception as e:
        print(f"❌ שגיאה ביבוא הבקטסטר: {e}")
        return
    
    # 🎯 תסריט 1: בדיקה אחרונה (שבוע אחרון)
    print(f"\n🚀 תסריט 1: שבוע אחרון")
    print("-" * 30)
    
    end_date_str = max_date.strftime('%Y-%m-%d')
    start_date_str = (max_date - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"📅 תקופה: {start_date_str} עד {end_date_str}")
    
    try:
        results = backtester.run_historical_backtest(
            start_date=start_date_str,
            end_date=end_date_str,
            horizons=[1, 5],
            algorithms=['rf']
        )
        
        summary = results.get('summary', {})
        print(f"✅ הושלם בהצלחה!")
        print(f"   📊 ימים: {summary.get('total_days_tested', 0)}")
        print(f"   🧠 מודלים: {summary.get('total_models_trained', 0)}")
        print(f"   🔍 סריקות: {summary.get('successful_scans', 0)}")
        
        if summary.get('total_models_trained', 0) > 0:
            print(f"🎉 המערכת פועלת! הבקטסטר מאמן מודלים בהצלחה")
            
            # בדיקה מעמיקה יותר
            print(f"\n🔬 תסריט 2: חודש אחרון")
            print("-" * 30)
            
            start_month = (max_date - timedelta(days=30)).strftime('%Y-%m-%d')
            
            results_month = backtester.run_historical_backtest(
                start_date=start_month,
                end_date=end_date_str,
                horizons=[1, 5, 10],
                algorithms=['rf', 'xgb']
            )
            
            summary_month = results_month.get('summary', {})
            print(f"📊 תוצאות חודשיות:")
            print(f"   📅 ימים: {summary_month.get('total_days_tested', 0)}")
            print(f"   🧠 מודלים: {summary_month.get('total_models_trained', 0)}")
            print(f"   🔍 סריקות: {summary_month.get('successful_scans', 0)}")
            
        else:
            print(f"⚠️ עדיין אין מודלים מאומנים. יכול להיות שצריך יותר נתונים היסטוריים.")
            
    except Exception as e:
        print(f"❌ שגיאה בהרצת הבקטסט: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_proper_backtest()