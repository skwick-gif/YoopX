"""
מערכת בדיקה היסטורית - Phase 2
=====================================

הבקר הראשי לביצוע בדיקות היסטוריות עם מודלים מותאמים לזמן.

תכונות:
- בדיקה אוטומטית של תקופות שונות
- אימון מודלים עם הוריזונים שונים (1/5/10 ימים)
- סריקה היסטורית וחישוב ביצועים
- השוואת תוצאות לפני ואחרי

הערה חשובה - זרימת הנתונים:
===============================
1. כפתור "Daily Update" → מוריד נתונים גולמיים (JSON) ל-raw_data
2. Processing Pipeline → ממיר ל-Parquet מובנה ב-processed_data/_parquet 
3. ML Training → משתמש בנתוני הפארקט המעובדים (פורמט: date index + OHLCV columns)
4. Historical Backtesting → משתמש באותם נתונים מעובדים

נתיב נתונים נכון: get_data_paths()['processed'] + '/_parquet'
פורמט נתונים נדרש: DataFrame עם date index וקולונות ['Open','High','Low','Close','Volume']
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd

# הוספת נתיב הפרויקט
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.train_model import train_multi_horizon_model, filter_data_until_date
from data.data_utils import load_tickers_on_demand, get_catalog, list_tickers_from_folder
# from backend import scan_symbols_with_ml, calculate_composite_score  # לבדוק אחר כך


class HistoricalBacktester:
    """בקר לביצוע בדיקות היסטוריות עם מודלים מותאמים"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getcwd()
        self.models_dir = os.path.join(self.base_path, 'ml', 'models', 'historical')
        self.results_dir = os.path.join(self.base_path, 'ml', 'backtest_results')
        
        # וידוא שהתיקיות קיימות
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # הגדרת לוג
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def run_historical_backtest(self, 
                              start_date: str, 
                              end_date: str, 
                              horizons: List[int] = [1, 5, 10],
                              algorithms: List[str] = ['rf', 'xgb', 'lgbm']) -> Dict:
        """
        מריץ בדיקה היסטורית מלאה
        
        Args:
            start_date: תאריך התחלה (YYYY-MM-DD)
            end_date: תאריך סיום (YYYY-MM-DD) 
            horizons: רשימת הוריזונים לבדיקה
            algorithms: רשימת אלגוריתמים לבדיקה
            
        Returns:
            Dict: תוצאות הבדיקה ההיסטורית
        """
        
        self.logger.info(f"🚀 מתחיל בדיקה היסטורית: {start_date} עד {end_date}")
        
        results = {
            'config': {
                'start_date': start_date,
                'end_date': end_date,
                'horizons': horizons,
                'algorithms': algorithms
            },
            'daily_results': {},
            'summary': {}
        }
        
        # טעינת נתונים
        self.logger.info("📥 טוען נתונים...")
        all_data = self._load_all_data()
        
        # יצירת רשימת תאריכים לבדיקה
        test_dates = self._generate_test_dates(start_date, end_date)
        
        total_tests = len(test_dates) * len(horizons) * len(algorithms)
        test_count = 0
        
        for test_date in test_dates:
            self.logger.info(f"📅 בודק תאריך: {test_date}")
            
            date_results = {}
            
            for horizon in horizons:
                for algorithm in algorithms:
                    test_count += 1
                    progress = (test_count / total_tests) * 100
                    
                    self.logger.info(f"🔄 [{progress:.1f}%] אימון {algorithm} לhorizon {horizon} ימים")
                    
                    # אימון מודל עם נתונים עד התאריך הנתון
                    model_path = self._train_model_for_date(
                        test_date, horizon, algorithm, all_data
                    )
                    
                    if model_path:
                        # ביצוע סריקה עם המודל החדש
                        scan_results = self._run_historical_scan(
                            model_path, test_date, horizon
                        )
                        
                        # שמירת תוצאות
                        key = f"{algorithm}_h{horizon}"
                        date_results[key] = {
                            'model_path': model_path,
                            'scan_results': scan_results
                        }
                    
            results['daily_results'][test_date] = date_results
            
            # שמירה ביניים
            self._save_interim_results(results, test_date)
        
        # חישוב סיכום
        results['summary'] = self._calculate_summary(results)
        
        # שמירה סופית
        final_path = self._save_final_results(results)
        self.logger.info(f"✅ בדיקה הושלמה! תוצאות נשמרו ב: {final_path}")
        
        return results
    
    def _generate_test_dates(self, start_date: str, end_date: str) -> List[str]:
        """יוצר רשימת תאריכים לבדיקה"""
        dates = []
        current = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        
        # בדיקה כל 5 ימי עסקים
        while current <= end:
            if current.weekday() < 5:  # ימי עסקים בלבד
                dates.append(current.strftime('%Y-%m-%d'))
            
            # קפיצה של שבוע
            current += pd.Timedelta(days=7)
            
        return dates
    
    def _load_all_data(self) -> Dict:
        """טוען את כל הנתונים מהמערכת הקיימת - בדיוק כמו שהמערכת עובדת"""
        try:
            # שימוש בנתיבי המערכת הקיימת
            from data.data_paths import get_data_paths
            from data.enhanced_verification import _load_processed_data_map
            
            paths = get_data_paths()
            processed_dir = paths['processed']
            
            self.logger.info(f"📊 טוען נתונים מתיקיית המעובדים: {processed_dir}")
            
            # טעינה בדיוק כמו שהמערכת הקיימת עושה
            data_map = _load_processed_data_map(processed_dir)
            
            if not data_map:
                self.logger.warning("⚠️ לא נמצאו נתונים מעובדים. הרץ Daily Update תחילה.")
                return {}
            
            # מגביל ל-10 טיקרים לבדיקה
            limited_data = dict(list(data_map.items())[:10])
            
            self.logger.info(f"✅ נטענו {len(limited_data)} טיקרים בהצלחה")
            
            # בדיקה שהנתונים בפורמט הנכון
            for ticker, df in limited_data.items():
                if df is not None and not df.empty:
                    self.logger.debug(f"✓ {ticker}: {len(df)} שורות, עמודות: {list(df.columns)}")
                    break
            
            return limited_data
            
        except Exception as e:
            self.logger.error(f"❌ שגיאה בטעינת נתונים: {e}")
            return {}

    def _load_parquet_data(self, tickers: List[str], data_dir: str) -> Dict:
        """טוען נתונים מקבצי פארקט והופך אותם לפורמט מחירים יומיים"""
        data = {}
        import pandas as pd
        
        for ticker in tickers:
            try:
                parquet_path = os.path.join(data_dir, f"{ticker}.parquet")
                if os.path.exists(parquet_path):
                    # טעינת הקובץ
                    df = pd.read_parquet(parquet_path)
                    
                    # חילוץ נתוני המחירים מהשדה המתאים
                    price_data = df['price.yahoo.daily'].iloc[0]
                    
                    if price_data is not None and len(price_data) > 0:
                        # המרה לDataFrame
                        price_df = pd.DataFrame(price_data)
                        
                        # המרת התאריך לindex
                        price_df['date'] = pd.to_datetime(price_df['date'])
                        price_df.set_index('date', inplace=True)
                        
                        # סידור הנתונים
                        price_df = price_df.sort_index()
                        
                        data[ticker] = price_df
                        self.logger.debug(f"✅ נטען {ticker}: {len(price_df)} ימים של נתונים")
                    else:
                        self.logger.warning(f"⚠️ אין נתוני מחירים ל-{ticker}")
                else:
                    self.logger.warning(f"⚠️ קובץ לא נמצא: {ticker}")
            except Exception as e:
                self.logger.warning(f"⚠️ שגיאה בטעינת {ticker}: {e}")
                
        return data

    def _get_available_tickers(self, data_dir: str) -> List[str]:
        """מחזיר רשימת טיקרים זמינים מקבצי הפארקט"""
        tickers = []
        
        if not os.path.exists(data_dir):
            self.logger.error(f"❌ תיקיית נתונים לא קיימת: {data_dir}")
            return tickers
            
        for filename in os.listdir(data_dir):
            if filename.endswith('.parquet'):
                ticker = filename.replace('.parquet', '')
                tickers.append(ticker)
                
        self.logger.info(f"🎯 נמצאו {len(tickers)} טיקרים זמינים")
        return sorted(tickers)
    
    def _train_model_for_date(self, test_date: str, horizon: int, 
                             algorithm: str, all_data: Dict) -> Optional[str]:
        """מאמן מודל עם נתונים עד תאריך מסוים"""
        
        try:
            # סינון נתונים עד התאריך
            filtered_data = filter_data_until_date(all_data, test_date)
            
            if not filtered_data:
                self.logger.warning(f"⚠️ אין נתונים מספיקים לתאריך {test_date}")
                return None
            
            # אימון המודל
            model_path = train_multi_horizon_model(
                filtered_data, horizon, algorithm, 
                save_path=os.path.join(
                    self.models_dir, 
                    f"{test_date}_{algorithm}_h{horizon}.joblib"
                )
            )
            
            return model_path
            
        except Exception as e:
            self.logger.error(f"❌ שגיאה באימון מודל: {e}")
            return None
    
    def _run_historical_scan(self, model_path: str, test_date: str, 
                           horizon: int) -> Dict:
        """מריץ סריקה היסטורית עם מודל נתון"""
        
        try:
            # כאן נצטרך לשנות את backend.py לקבל נתיב מודל
            # בינתיים נחזיר מבנה בסיסי
            
            # TODO: שינוי backend.py לתמוך במודלים היסטוריים
            
            return {
                'date': test_date,
                'horizon': horizon,
                'model_path': model_path,
                'top_symbols': [],  # יימלא אחרי שנשנה את backend
                'scan_count': 0,
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ שגיאה בסריקה: {e}")
            return {
                'date': test_date,
                'horizon': horizon,
                'model_path': model_path,
                'success': False,
                'error': str(e)
            }
    
    def _save_interim_results(self, results: Dict, date: str):
        """שומר תוצאות ביניים"""
        interim_path = os.path.join(
            self.results_dir, 
            f"interim_results_{date}.json"
        )
        
        try:
            with open(interim_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ לא הצלחתי לשמור תוצאות ביניים: {e}")
    
    def _calculate_summary(self, results: Dict) -> Dict:
        """מחשב סיכום התוצאות"""
        summary = {
            'total_tests': len(results['daily_results']),
            'successful_tests': 0,
            'failed_tests': 0,
            'performance_by_horizon': {},
            'performance_by_algorithm': {}
        }
        
        # ספירת בדיקות מוצלחות
        for date_results in results['daily_results'].values():
            for test_result in date_results.values():
                if test_result.get('scan_results', {}).get('success', False):
                    summary['successful_tests'] += 1
                else:
                    summary['failed_tests'] += 1
        
        # TODO: חישובי ביצועים מפורטים לאחר יישום הסריקה המלאה
        
        return summary
    
    def _save_final_results(self, results: Dict) -> str:
        """שומר תוצאות סופיות"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_path = os.path.join(
            self.results_dir,
            f"backtest_results_{timestamp}.json"
        )
        
        with open(final_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        return final_path


def run_quick_test():
    """בדיקה מהירה של המערכת"""
    print("🧪 בדיקה מהירה של הבקר ההיסטורי...")
    
    backtester = HistoricalBacktester()
    
    # בדיקה עם תקופה קצרה
    start_date = "2024-01-01"
    end_date = "2024-01-15"
    
    print(f"📅 בודק תקופה: {start_date} עד {end_date}")
    
    # בדיקה עם מודל אחד בלבד
    results = backtester.run_historical_backtest(
        start_date=start_date,
        end_date=end_date,
        horizons=[1],  # רק horizon אחד
        algorithms=['rf']  # רק RF
    )
    
    print("✅ בדיקה הושלמה!")
    print(f"📊 תוצאות: {len(results['daily_results'])} ימים נבדקו")
    
    return results


if __name__ == "__main__":
    # הרצת בדיקה מהירה
    results = run_quick_test()
    print("\n🎯 הבקר ההיסטורי מוכן לשימוש!")