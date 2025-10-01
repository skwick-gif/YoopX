#!/usr/bin/env python3
"""
🔄 Iterative Historical Training System - מימוש התהליך שהמשתמש ביקש

תהליך: 
1. אמן עד תאריך X (30 ימי מסחר אחורה)
2. בדוק ביצועים על הנתונים שלא נכללו באימון (ה-30 ימים)
3. השווה תחזיות מול מציאות
4. עדכן/כייל מודל
5. חזור לשלב 1 עם נתונים מעודכנים
6. המשך עד שמגיעים לדיוק מקסימלי
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass

@dataclass
class IterativeTrainingConfig:
    """הגדרות לאימון טיטרטיבי
    label_threshold: אחוז התשואה שמגדיר הצלחה (דיפולט 2%)
    blend_alpha: כמה משקל לתת לדיוק המשוקלל (0..1)
    """
    initial_lookback_days: int = 30  # כמה ימי מסחר אחורה להתחיל
    horizons: List[int] = None
    max_iterations: int = 10  # מקסימום איטרציות
    min_accuracy_improvement: float = 0.01  # שיפור מינימלי לחזור לאיטרציה הבאה
    target_accuracy: float = 0.70  # דיוק יעד לעצירה
    label_threshold: float = 0.02  # 2% תשואה
    blend_alpha: float = 0.40  # משקל לדיוק המשוקלל (לשעבר 0.4 קבוע)
    
    def __post_init__(self):
        if self.horizons is None:
            self.horizons = [1, 5, 10]

@dataclass 
class IterativeResults:
    """תוצאות איטרציה"""
    iteration: int
    training_cutoff_date: str
    validation_start_date: str
    validation_end_date: str
    models_trained: Dict[int, str]  # horizon -> model_path
    predictions: List[Dict]  # תחזיות
    actual_results: List[Dict]  # תוצאות בפועל
    accuracy_by_horizon: Dict[int, float]  # דיוק לכל horizon
    improvement_from_previous: Optional[float] = None

class IterativeHistoricalTrainer:
    """מערכת אימון טיטרטיבית היסטורית"""
    
    def __init__(self, data_map: Dict[str, pd.DataFrame]):
        self.data_map = data_map
        self.logger = logging.getLogger(__name__)
        self.results_history: List[IterativeResults] = []
        
        # תיקיות לשמירת מודלים ותוצאות
        self.models_dir = "ml/iterative_models"
        self.results_dir = "ml/iterative_results" 
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
    def run_iterative_training(self, config: IterativeTrainingConfig) -> List[IterativeResults]:
        """
        הרצת התהליך הטיטרטיבי המלא
        
        זהו התהליך שהמשתמש ביקש:
        1. אמן על נתונים עד תאריך X
        2. בדוק על התקופה שלא נכללה באימון  
        3. השווה תחזיות מול מציאות
        4. שפר מודל והמשך
        """
        
        self.logger.info(f"🚀 מתחיל אימון טיטרטיבי עם {config.initial_lookback_days} ימי מסחר")
        
        # מציאת התאריך האחרון בנתונים
        latest_date = self._find_latest_date()
        if not latest_date:
            raise ValueError("לא נמצא תאריך אחרון בנתונים")
            
        current_lookback_days = config.initial_lookback_days
        previous_best_accuracy = 0.0
        
        for iteration in range(1, config.max_iterations + 1):
            self.logger.info(f"\n🔄 איטרציה #{iteration}")
            
            try:
                # שלב 1: חישוב תאריכי אימון ובדיקה
                training_cutoff, validation_start, validation_end = self._calculate_dates(
                    latest_date, current_lookback_days
                )
                
                self.logger.info(f"📅 אימון עד: {training_cutoff}")
                self.logger.info(f"📅 בדיקה: {validation_start} → {validation_end}")
                
                # שלב 2: אימון מודלים
                models_trained = self._train_models_for_iteration(
                    training_cutoff, config.horizons, iteration
                )
                
                if not models_trained:
                    self.logger.error("❌ כשלון באימון מודלים")
                    break
                    
                # שלב 3: יצירת תחזיות על תקופת הבדיקה
                predictions = self._generate_predictions(
                    models_trained, validation_start, validation_end
                )
                
                # שלב 4: איסוף תוצאות בפועל
                actual_results = self._collect_actual_results(
                    predictions, validation_start, validation_end, label_threshold=config.label_threshold
                )
                
                # שלב 5: השוואה וחישוב דיוק
                accuracy_by_horizon = self._calculate_accuracy(
                    predictions, actual_results, config.horizons, blend_alpha=config.blend_alpha
                )
                
                # שלב 6: בדיקת שיפור
                avg_accuracy = sum(accuracy_by_horizon.values()) / len(accuracy_by_horizon)
                improvement = avg_accuracy - previous_best_accuracy
                
                # שמירת תוצאות איטרציה
                iteration_result = IterativeResults(
                    iteration=iteration,
                    training_cutoff_date=training_cutoff,
                    validation_start_date=validation_start,
                    validation_end_date=validation_end,
                    models_trained=models_trained,
                    predictions=predictions,
                    actual_results=actual_results,
                    accuracy_by_horizon=accuracy_by_horizon,
                    improvement_from_previous=improvement if iteration > 1 else None
                )
                
                self.results_history.append(iteration_result)
                self._save_iteration_results(iteration_result)
                
                # דיווח תוצאות
                self.logger.info(f"📊 דיוק ממוצע: {avg_accuracy:.3f}")
                self.logger.info(f"📈 שיפור: {improvement:.3f}" if iteration > 1 else "📈 איטרציה ראשונה")
                
                for horizon, acc in accuracy_by_horizon.items():
                    self.logger.info(f"   {horizon}D: {acc:.3f}")
                
                # בדיקת תנאי עצירה
                if avg_accuracy >= config.target_accuracy:
                    self.logger.info(f"🎯 הגענו לדיוק יעד ({config.target_accuracy:.3f})!")
                    break
                    
                if iteration > 1 and improvement < config.min_accuracy_improvement:
                    self.logger.info(f"📉 שיפור קטן מדי ({improvement:.3f} < {config.min_accuracy_improvement:.3f})")
                    break
                
                # הכנה לאיטרציה הבאה - הוספת יותר נתונים
                previous_best_accuracy = max(previous_best_accuracy, avg_accuracy)
                current_lookback_days += 5  # הוסף 5 ימי מסחר נוספים
                
            except Exception as e:
                self.logger.error(f"❌ שגיאה באיטרציה #{iteration}: {e}")
                break
                
        self.logger.info(f"✅ אימון טיטרטיבי הושלם אחרי {len(self.results_history)} איטרציות")
        return self.results_history
    
    def _calculate_dates(self, latest_date: pd.Timestamp, lookback_days: int) -> Tuple[str, str, str]:
        """חישוב תאריכי אימון ובדיקה"""
        
        # תאריך גבול לאימון (lookback_days ימי מסחר אחורה)
        business_days = pd.bdate_range(end=latest_date, periods=lookback_days + 1, freq='B')
        training_cutoff = business_days[0].strftime('%Y-%m-%d')
        
        # תקופת בדיקה - מתאריך הגבול עד התאריך האחרון
        validation_start = business_days[1].strftime('%Y-%m-%d')  # יום אחרי הגבול
        validation_end = latest_date.strftime('%Y-%m-%d')
        
        return training_cutoff, validation_start, validation_end
    
    def _find_latest_date(self) -> Optional[pd.Timestamp]:
        """מציאת התאריך האחרון בנתונים"""
        latest = None
        
        for symbol, df in self.data_map.items():
            if df is None or df.empty:
                continue
                
            try:
                if isinstance(df.index, pd.DatetimeIndex):
                    df_latest = df.index.max()
                elif 'Date' in df.columns:
                    df_latest = pd.to_datetime(df['Date']).max()
                else:
                    continue
                    
                if latest is None or df_latest > latest:
                    latest = df_latest
                    
            except Exception as e:
                self.logger.warning(f"⚠️ בעיה בעיבוד תאריך עבור {symbol}: {e}")
                continue
                
        return latest
    
    def _train_models_for_iteration(self, cutoff_date: str, horizons: List[int], iteration: int) -> Dict[int, str]:
        """אימון מודלים לאיטרציה ספציפית"""
        
        # ייבוא הפונקציות מהמערכת הקיימת
        from ml.train_model import filter_data_until_date, train_multi_horizon_model
        
        self.logger.info(f"🧠 מאמן מודלים לאיטרציה #{iteration}")
        
        # סינון נתונים עד תאריך הגבול
        filtered_data = filter_data_until_date(self.data_map, cutoff_date)
        
        if not filtered_data:
            self.logger.error("❌ לא נמצאו נתונים מסוננים")
            return {}
            
        models_trained = {}
        
        for horizon in horizons:
            try:
                self.logger.info(f"  📚 מאמן מודל {horizon}D...")
                
                model_path = train_multi_horizon_model(
                    cutoff_date=cutoff_date,
                    horizon_days=horizon,
                    algorithm='rf',  # כרגע רק RF, אפשר להרחיב
                    data_map=filtered_data
                )
                
                if model_path and os.path.exists(model_path):
                    models_trained[horizon] = model_path
                    self.logger.info(f"    ✅ {horizon}D: {model_path}")
                else:
                    self.logger.warning(f"    ❌ {horizon}D: כשלון באימון")
                    
            except Exception as e:
                self.logger.error(f"    ❌ {horizon}D: {e}")
                
        return models_trained
    
    def _generate_predictions(self, models: Dict[int, str], start_date: str, end_date: str) -> List[Dict]:
        """יצירת תחזיות לתקופת הבדיקה"""
        
        self.logger.info(f"🔮 יוצר תחזיות {start_date} → {end_date}")
        
        # ייבוא הפונקציות הנדרשות
        from ml.train_model import load_model
        from ml.feature_engineering import compute_features
        import pandas as pd
        
        predictions = []
        
        # איטרציה על תאריכים עסקיים בתקופת הבדיקה
        date_range = pd.bdate_range(start=start_date, end=end_date, freq='B')
        
        for current_date in date_range:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # איטרציה על כל מניה
            for symbol, df in self.data_map.items():
                if df is None or df.empty:
                    continue
                    
                try:
                    # סינון נתונים עד התאריך הנוכחי
                    # וידוא שהאינדקס הוא datetime
                    if not pd.api.types.is_datetime64_any_dtype(df.index):
                        df.index = pd.to_datetime(df.index, utc=True)
                    
                    # וידוא שה-current_date הוא timezone-aware אם הנתונים timezone-aware
                    if df.index.tz is not None and current_date.tz is None:
                        current_date = current_date.tz_localize('UTC')
                    elif df.index.tz is None and current_date.tz is not None:
                        current_date = current_date.tz_localize(None)
                    
                    df_until_date = df[df.index <= current_date]
                    
                    if len(df_until_date) < 50:  # מינימום נתונים
                        continue
                        
                    # חישוב features לתאריך הנוכחי
                    features_df = compute_features(df_until_date)
                    
                    if features_df.empty:
                        continue
                        
                    # קבלת הרשומה האחרונה (התאריך הנוכחי)
                    latest_features = features_df.iloc[-1:].drop(columns=['label'], errors='ignore')
                    
                    # הרצת תחזיות לכל horizon
                    for horizon, model_path in models.items():
                        if not os.path.exists(model_path):
                            continue
                            
                        try:
                            model_obj = load_model(model_path)
                            if model_obj is None:
                                continue
                            
                            # המודל נשמר כ-dictionary עם מפתח 'model'
                            if isinstance(model_obj, dict) and 'model' in model_obj:
                                model = model_obj['model']
                            else:
                                model = model_obj
                                
                            # תחזית
                            prediction_proba = model.predict_proba(latest_features)[0]
                            prediction_class = model.predict(latest_features)[0]
                            
                            # שמירת התחזית
                            predictions.append({
                                'date': date_str,
                                'symbol': symbol,
                                'horizon': horizon,
                                'prediction_class': int(prediction_class),
                                'prediction_proba': float(prediction_proba[1]),  # הסתברות לכיוון חיובי
                                'current_price': float(df_until_date['Close'].iloc[-1]),
                                'target_date': (current_date + pd.Timedelta(days=horizon)).strftime('%Y-%m-%d')
                            })
                            
                        except Exception as e:
                            self.logger.warning(f"⚠️ תחזית נכשלה {symbol} {horizon}D {date_str}: {e}")
                            
                except Exception as e:
                    self.logger.warning(f"⚠️ עיבוד נכשל {symbol} {date_str}: {e}")
        
        self.logger.info(f"✅ נוצרו {len(predictions)} תחזיות")
        return predictions
    
    def _collect_actual_results(self, predictions: List[Dict], start_date: str, end_date: str, label_threshold: float = 0.02) -> List[Dict]:
        """איסוף תוצאות בפועל לאותן התחזיות"""
        
        self.logger.info(f"📊 אוסף תוצאות בפועל {start_date} → {end_date}")
        
        actual_results = []
        
        for prediction in predictions:
            try:
                symbol = prediction['symbol']
                target_date = prediction['target_date']
                horizon = prediction['horizon']
                current_price = prediction['current_price']
                
                # בדיקה שיש לנו נתונים למניה
                if symbol not in self.data_map or self.data_map[symbol] is None:
                    continue
                    
                df = self.data_map[symbol]
                
                # חיפוש המחיר בתאריך היעד
                import pandas as pd
                target_dt = pd.to_datetime(target_date)
                
                # וידוא שהאינדקס הוא datetime
                if not pd.api.types.is_datetime64_any_dtype(df.index):
                    df.index = pd.to_datetime(df.index, utc=True)
                
                # וידוא timezone consistency
                if df.index.tz is not None and target_dt.tz is None:
                    target_dt = target_dt.tz_localize('UTC')
                elif df.index.tz is None and target_dt.tz is not None:
                    target_dt = target_dt.tz_localize(None)
                
                # מציאת התאריך הקרוב ביותר (במקרה של סוף שבוע/חגים)
                available_dates = df.index[df.index >= target_dt]
                
                if len(available_dates) == 0:
                    # אין נתונים לתאריך היעד - אולי התחזית עדיין בעתיד
                    continue
                    
                actual_date = available_dates[0]
                actual_price = float(df.loc[actual_date, 'Close'])
                
                # חישוב התשואה בפועל
                actual_return = (actual_price - current_price) / current_price
                
                # שימוש ב-threshold דינמי מהקונפיג
                actual_direction = 1 if actual_return >= label_threshold else 0
                
                # בדיקה האם התחזית הייתה נכונה
                prediction_correct = (prediction['prediction_class'] == actual_direction)
                
                actual_results.append({
                    'date': prediction['date'],
                    'symbol': symbol,
                    'horizon': horizon,
                    'prediction_class': prediction['prediction_class'],
                    'prediction_proba': prediction['prediction_proba'],
                    'actual_class': actual_direction,
                    'actual_return': actual_return,
                    'current_price': current_price,
                    'actual_price': actual_price,
                    'target_date': target_date,
                    'actual_date': actual_date.strftime('%Y-%m-%d'),
                    'prediction_correct': prediction_correct
                })
                
            except Exception as e:
                self.logger.warning(f"⚠️ איסוף תוצאות נכשל עבור {prediction.get('symbol', 'unknown')}: {e}")
        
        self.logger.info(f"✅ נאספו {len(actual_results)} תוצאות בפועל")
        return actual_results
    
    def _calculate_accuracy(self, predictions: List[Dict], actual_results: List[Dict], horizons: List[int], blend_alpha: float = 0.40) -> Dict[int, float]:
        """חישוב דיוק לכל horizon"""
        
        accuracy_by_horizon = {}
        
        for horizon in horizons:
            # סינון תוצאות לאופק הספציפי
            horizon_results = [r for r in actual_results if r['horizon'] == horizon]
            
            if not horizon_results:
                accuracy_by_horizon[horizon] = 0.0
                continue
                
            # חישוב דיוק בסיסי
            correct_predictions = sum(1 for r in horizon_results if r['prediction_correct'])
            total_predictions = len(horizon_results)
            
            basic_accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0
            
            # חישוב דיוק משוקלל לפי רמת ביטחון
            # תחזיות עם הסתברות גבוהה יותר מקבלות משקל גבוה יותר
            weighted_correct = 0.0
            weighted_total = 0.0
            
            for result in horizon_results:
                confidence = abs(result['prediction_proba'] - 0.5) * 2  # 0 = אין ביטחון, 1 = ביטחון מלא
                weight = max(0.1, confidence)  # משקל מינימלי של 0.1
                
                weighted_total += weight
                if result['prediction_correct']:
                    weighted_correct += weight
            
            weighted_accuracy = weighted_correct / weighted_total if weighted_total > 0 else 0.0
            
            # הגבלת blend_alpha
            try:
                ba = max(0.0, min(1.0, float(blend_alpha)))
            except Exception:
                ba = 0.40
            # שילוב: basic*(1-alpha) + weighted*alpha
            final_accuracy = (basic_accuracy * (1.0 - ba)) + (weighted_accuracy * ba)
            
            accuracy_by_horizon[horizon] = final_accuracy
            
            # לוג מפורט
            self.logger.info(
                f"  {horizon}D: {correct_predictions}/{total_predictions} = {basic_accuracy:.3f} "
                f"(weighted: {weighted_accuracy:.3f}, final: {final_accuracy:.3f}, α={ba:.2f})"
            )
            
        return accuracy_by_horizon
    
    def _save_iteration_results(self, result: IterativeResults):
        """שמירת תוצאות איטרציה"""
        
        filename = f"iteration_{result.iteration:02d}_{result.training_cutoff_date.replace('-', '')}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        # המרה ל-dict לשמירה
        result_dict = {
            'iteration': result.iteration,
            'training_cutoff_date': result.training_cutoff_date,
            'validation_start_date': result.validation_start_date,
            'validation_end_date': result.validation_end_date,
            'models_trained': result.models_trained,
            'predictions_count': len(result.predictions),
            'actual_results_count': len(result.actual_results),
            'accuracy_by_horizon': result.accuracy_by_horizon,
            'improvement_from_previous': result.improvement_from_previous,
            'horizons': list(result.accuracy_by_horizon.keys()),
            'avg_accuracy': (sum(result.accuracy_by_horizon.values()) / len(result.accuracy_by_horizon)) if result.accuracy_by_horizon else 0.0
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, ensure_ascii=False, indent=2)
            # שמירת פירוט מלא של תוצאות actual (כולל הסתברות ודיוק לכל תחזית)
            if result.actual_results:
                detailed_path = filepath.replace('.json', '_actual_results.json')
                with open(detailed_path, 'w', encoding='utf-8') as df:
                    json.dump(result.actual_results, df, ensure_ascii=False, indent=2)
            # אופציונלי: שמירת תחזיות (ללא actual אם חסר)
            if result.predictions:
                preds_path = filepath.replace('.json', '_predictions.json')
                with open(preds_path, 'w', encoding='utf-8') as pf:
                    json.dump(result.predictions, pf, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 נשמרו קבצי איטרציה: {filepath}")
        except Exception as e:
            self.logger.error(f"❌ כשלון בשמירת תוצאות: {e}")

def demo_iterative_training():
    """הדמיה של הפונקציונליות החדשה"""
    
    print("🔄 Demo: Iterative Historical Training")
    print("=" * 50)
    
    # טעינת נתונים (דמה)
    print("📊 Loading demo data...")
    
    # בפועל כאן נטען data_map אמיתי
    data_map = {}  # placeholder
    
    if not data_map:
        print("⚠️ No data loaded - this is just a demo")
        return
        
    # הגדרת תצורה
    config = IterativeTrainingConfig(
        initial_lookback_days=30,
        horizons=[1, 5, 10],
        max_iterations=5,
        min_accuracy_improvement=0.01,
        target_accuracy=0.70
    )
    
    # יצירת מערכת אימון
    trainer = IterativeHistoricalTrainer(data_map)
    
    # הרצת התהליך
    results = trainer.run_iterative_training(config)
    
    # הצגת תוצאות
    print(f"\n📋 תוצאות סופיות: {len(results)} איטרציות")
    
    for i, result in enumerate(results, 1):
        print(f"\nאיטרציה #{i}:")
        print(f"  📅 אימון עד: {result.training_cutoff_date}")
        print(f"  📊 דיוק ממוצע: {sum(result.accuracy_by_horizon.values()) / len(result.accuracy_by_horizon):.3f}")
        if result.improvement_from_previous:
            print(f"  📈 שיפור: {result.improvement_from_previous:.3f}")

if __name__ == "__main__":
    demo_iterative_training()