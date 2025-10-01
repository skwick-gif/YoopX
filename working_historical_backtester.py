#!/usr/bin/env python3
"""
🎯 הבקטסטר ההיסטורי הנכון - בדיוק כמו המערכת הקיימת!
==============================================================

השלב הבא: יצירת בקטסטר שעובד בדיוק כמו הסריקה הרגילה,
אבל על נתונים היסטוריים.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# יבוא הפונקציות המרכזיות מהמערכת הקיימת
from ml.train_model import train_model, filter_data_until_date
from data.enhanced_verification import _load_processed_data_map
from data.data_paths import get_data_paths
from data.data_utils import maybe_adjust_with_adj

class WorkingHistoricalBacktester:
    """
    בקטסטר היסטורי שעובד בדיוק כמו המערכת הקיימת
    """
    
    def __init__(self):
        """אתחול הבקטסטר"""
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        # תיקיות תוצאות
        self.results_dir = "ml/backtest_results"
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.temp_models_dir = "ml/temp_historical_models"
        os.makedirs(self.temp_models_dir, exist_ok=True)
        
    def run_simple_backtest(self, test_date: str = "2025-06-01") -> Dict:
        """
        הרצה פשוטה של בדיקה היסטורית יחידה
        """
        
        self.logger.info(f"🚀 בדיקה היסטורית פשוטה לתאריך: {test_date}")
        
        results = {
            'config': {
                'test_date': test_date,
                'timestamp': datetime.now().isoformat()
            },
            'steps': {},
            'success': False
        }
        
        try:
            # שלב 1: טעינת נתונים - בדיוק כמו המערכת הקיימת
            self.logger.info("📊 שלב 1: טוען data_map...")
            data_map = self._load_data_map_like_main_system()
            
            if not data_map:
                results['error'] = "לא נטענו נתונים"
                return results
                
            results['steps']['data_loaded'] = {
                'tickers_count': len(data_map),
                'tickers': list(data_map.keys())
            }
            self.logger.info(f"✅ נטענו {len(data_map)} טיקרים: {list(data_map.keys())}")
            
            # שלב 2: סינון נתונים עד התאריך - בדיוק כמו filter_data_until_date
            self.logger.info(f"🔄 שלב 2: סינון נתונים עד {test_date}...")
            filtered_data = filter_data_until_date(data_map, test_date)
            
            if not filtered_data:
                results['error'] = "לא נשארו נתונים אחרי סינון"
                return results
                
            results['steps']['data_filtered'] = {
                'tickers_count': len(filtered_data),
                'sample_ranges': {}
            }
            
            # בדיקה של טווחי נתונים
            for ticker, df in filtered_data.items():
                if df is not None and not df.empty:
                    results['steps']['data_filtered']['sample_ranges'][ticker] = {
                        'rows': len(df),
                        'date_range': f"{df.index.min()} - {df.index.max()}"
                    }
            
            self.logger.info(f"✅ אחרי סינון: {len(filtered_data)} טיקרים")
            
            # שלב 3: אימון מודל - בדיוק כמו train_model במערכת הקיימת
            self.logger.info("🧠 שלב 3: אימון מודל...")
            
            temp_model_path = os.path.join(self.temp_models_dir, f"temp_model_{test_date.replace('-', '')}.pkl")
            
            training_result = train_model(
                data_map=filtered_data,
                model='rf',  # התחל עם RF
                model_path=temp_model_path
            )
            
            if training_result.get('error'):
                results['error'] = f"שגיאה באימון: {training_result['error']}"
                return results
            
            results['steps']['model_trained'] = {
                'model_path': temp_model_path,
                'model_exists': os.path.exists(temp_model_path),
                'training_meta': {
                    'validation_auc': training_result.get('validation', {}).get('auc'),
                    'dataset_size': training_result.get('dataset_size'),
                    'features_count': len(training_result.get('features', []))
                }
            }
            
            self.logger.info(f"✅ מודל אומן: AUC = {training_result.get('validation', {}).get('auc', 'N/A')}")
            
            # שלב 4: בדיקה שהמודל עובד
            if os.path.exists(temp_model_path):
                from ml.train_model import load_model
                
                model = load_model(temp_model_path)
                if model:
                    self.logger.info("✅ מודל נטען בהצלחה ומוכן לשימוש")
                    results['steps']['model_verified'] = True
                else:
                    results['error'] = "מודל לא נטען כראוי"
                    return results
            
            # הצלחה!
            results['success'] = True
            self.logger.info("🎉 בדיקה היסטורית הושלמה בהצלחה!")
            
        except Exception as e:
            results['error'] = str(e)
            self.logger.error(f"❌ שגיאה: {e}")
            import traceback
            results['traceback'] = traceback.format_exc()
        
        finally:
            # ניקוי מודלים זמניים
            try:
                if 'temp_model_path' in locals() and os.path.exists(temp_model_path):
                    os.remove(temp_model_path)
            except:
                pass
        
        return results
    
    def _load_data_map_like_main_system(self) -> Dict[str, pd.DataFrame]:
        """
        טוען data_map בדיוק כמו שהמערכת הקיימת עושה זאת
        """
        try:
            # השתמש בדיוק באותן פונקציות שהמערכת הקיימת משתמשת
            paths = get_data_paths()
            processed_dir = paths['processed']
            
            self.logger.info(f"📁 טוען מתיקיית המעובדים: {processed_dir}")
            
            # טעינה כמו במערכת הקיימת
            raw_data_map = _load_processed_data_map(processed_dir)
            
            if not raw_data_map:
                self.logger.warning("⚠️ לא נמצאו נתונים מעובדים")
                return {}
            
            # עיבוד כמו במערכת הקיימת
            processed_data_map = {}
            
            for ticker, df in raw_data_map.items():
                try:
                    # בדיקה אם הנתונים כבר מעובדים (יש עמודות OHLCV)
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    has_ohlcv = all(col in df.columns for col in required_cols)
                    
                    if has_ohlcv:
                        # נתונים כבר נקיים - רק maybe_adjust_with_adj
                        final_df = maybe_adjust_with_adj(df.copy(), use_adj=True)
                        processed_data_map[ticker] = final_df
                        self.logger.debug(f"✓ {ticker}: נתונים נקיים, {len(final_df)} שורות")
                    else:
                        # נתונים גולמיים - עיבוד כמו בבקטסטר הקודם
                        processed_df = self._process_raw_parquet_to_ohlcv(df, ticker)
                        if processed_df is not None and len(processed_df) > 0:
                            processed_data_map[ticker] = processed_df
                            self.logger.debug(f"🔄 {ticker}: עיבד מגולמי, {len(processed_df)} שורות")
                        else:
                            self.logger.debug(f"⚠️ {ticker}: כשלון בעיבוד נתונים גולמיים")
                        
                except Exception as e:
                    self.logger.warning(f"❌ {ticker}: שגיאה בעיבוד - {e}")
                    continue
            
            self.logger.info(f"✅ עיבד {len(processed_data_map)} טיקרים בהצלחה")
            return processed_data_map
            
        except Exception as e:
            self.logger.error(f"❌ שגיאה בטעינת data_map: {e}")
            return {}
    
    def _process_raw_parquet_to_ohlcv(self, raw_df: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
        """
        מעבד נתונים גולמיים מ-PARQUET לפורמט OHLCV
        מבוסס על הקוד מהבקטסטר הקודם
        """
        try:
            from data.data_utils import _standardize_columns, _ensure_datetime_index
            
            # חיפוש עמודת נתוני מחיר
            price_col = None
            if 'price.yahoo.daily' in raw_df.columns:
                price_col = 'price.yahoo.daily'
            else:
                # חיפוש עמודות אחרות
                for col in raw_df.columns:
                    if 'price' in str(col).lower() and 'daily' in str(col).lower():
                        price_col = col
                        break
            
            if price_col is None:
                self.logger.debug(f"⚠️ {ticker}: לא נמצאה עמודת נתוני מחיר")
                return None
            
            # חילוץ נתוני המחיר
            price_data = raw_df[price_col].iloc[0]
            
            # המרה לרשימה אם מגיע כ-numpy array
            if hasattr(price_data, 'tolist'):
                price_data = price_data.tolist()
            
            if not isinstance(price_data, (list, tuple)) or len(price_data) == 0:
                self.logger.debug(f"⚠️ {ticker}: נתוני מחיר לא ברשימה או ריקים")
                return None
            
            # וידוא שהרשומה הראשונה היא dictionary
            if not isinstance(price_data[0], dict):
                self.logger.debug(f"⚠️ {ticker}: פורמט נתוני מחיר לא תקין")
                return None
            
            # יצירת DataFrame מנתוני המחיר
            df = pd.DataFrame(price_data)
            
            # נרמול שמות עמודות
            df = _standardize_columns(df)
            
            # טיפול באינדקס תאריכים
            df = _ensure_datetime_index(df, path=f"ticker_{ticker}")
            
            # וידוא שיש עמודות OHLCV נדרשות
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                self.logger.debug(f"⚠️ {ticker}: חסרות עמודות: {missing_cols}")
                # נוסיף עמודות חסרות כNaN
                for col in missing_cols:
                    df[col] = pd.NA
            
            # המרה למספרים
            for col in required_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # ווידוא שהאינדקס תאריכים תקין
            if not pd.api.types.is_datetime64_any_dtype(df.index):
                self.logger.warning(f"⚠️ {ticker}: אינדקס תאריך לא תקין")
                return None
            
            # מיון לפי תאריך
            df = df.sort_index()
            
            # החלת adjustment
            df = maybe_adjust_with_adj(df, use_adj=True)
            
            self.logger.debug(f"✅ {ticker}: המרה מוצלחת - {len(df)} שורות, {df.index.min()} עד {df.index.max()}")
            return df
                
        except Exception as e:
            self.logger.warning(f"❌ {ticker}: שגיאה בעיבוד נתוני מחיר - {e}")
            return None

def main():
    """פונקציה ראשית"""
    
    print("🎯 בקטסטר היסטורי חדש - כמו המערכת הקיימת")
    print("=" * 60)
    
    backtester = WorkingHistoricalBacktester()
    
    # בדיקה פשוטה
    results = backtester.run_simple_backtest("2025-06-01")
    
    print(f"\n📊 תוצאות:")
    print(f"   ✅ הצלחה: {results['success']}")
    
    if results['success']:
        steps = results.get('steps', {})
        
        if 'data_loaded' in steps:
            data_info = steps['data_loaded']
            print(f"   📂 נתונים נטענו: {data_info['tickers_count']} טיקרים")
        
        if 'model_trained' in steps:
            model_info = steps['model_trained']
            training_meta = model_info.get('training_meta', {})
            print(f"   🧠 מודל אומן: AUC = {training_meta.get('validation_auc', 'N/A')}")
            print(f"   📊 גודל dataset: {training_meta.get('dataset_size', 'N/A')}")
            
        print(f"\n🎉 הבקטסטר עובד! המערכת מוכנה לבדיקות מורחבות")
        
    else:
        print(f"   ❌ שגיאה: {results.get('error', 'לא ידועה')}")
        
    print(f"\n🔄 שלבים הבאים:")
    print("1. 📅 הרצה על תאריכים שונים")  
    print("2. 🔄 השוואת מודלים (RF vs XGB vs LGBM)")
    print("3. 📊 ניתוח ביצועים")
    print("4. 🎯 הרצת סריקות על הנתונים ההיסטוריים")

if __name__ == "__main__":
    main()