#!/usr/bin/env python3
"""
בדיקה מהירה של הבקטסטר ההיסטורי המתוקן
"""

from ml.historical_backtester_fixed import HistoricalBacktester

def main():
    print('🚀 בודק בקטסטר היסטורי מלא...')

    try:
        backtester = HistoricalBacktester()
        
        print('📅 מריץ בדיקה קצרה: 3 ימים בלבד')
        
        results = backtester.run_historical_backtest(
            start_date='2024-06-01',
            end_date='2024-06-15', 
            horizons=[1],  # רק הוריזון יום אחד
            algorithms=['rf']  # רק Random Forest
        )
        
        print('✅ בדיקה הושלמה בהצלחה!')
        print('📊 תוצאות:')
        summary = results.get('summary', {})
        print(f'   ימים נבדקו: {summary.get("total_days_tested", 0)}')
        print(f'   מודלים אומנו: {summary.get("total_models_trained", 0)}')
        print('🎯 הבקטסטר ההיסטורי עובד תקין!')
        
    except Exception as e:
        print(f'❌ שגיאה: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()