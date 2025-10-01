#!/usr/bin/env python3
"""
🕰️ Historical Multi-Horizon Training System

מערכת אימון רב-אופקית היסטורית עם בדיקת ביצועים אוטומטית
"""

import os
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class BacktestConfig:
    start_date: str
    end_date: str
    step_days: int = 7
    horizons: List[int] = None
    min_accuracy_threshold: float = 0.55
    
    def __post_init__(self):
        if self.horizons is None:
            self.horizons = [1, 5, 10]

@dataclass
class ModelPerformance:
    horizon: int
    date: str
    total_predictions: int
    accuracy: float
    high_conf_accuracy: float
    suggested_threshold: float
    model_path: str

class HistoricalTrainingSystem:
    """מערכת אימון היסטורית עם ולידציה"""
    
    def __init__(self, base_model_dir: str = "ml/historical_models"):
        self.base_model_dir = base_model_dir
        self.results_dir = "ml/backtest_results"
        os.makedirs(self.base_model_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
    def train_multi_horizon_models(self, cutoff_date: str, horizons: List[int] = None) -> Dict[int, str]:
        """
        אימון מודלים עבור אופקי זמן שונים
        
        Args:
            cutoff_date: תאריך גבול לנתונים (YYYY-MM-DD)
            horizons: רשימת אופקי זמן (ברירת מחדל: [1, 5, 10])
        
        Returns:
            Dict מיפוי אופק → נתיב מודל
        """
        if horizons is None:
            horizons = [1, 5, 10]
            
        trained_models = {}
        
        print(f"🏋️ מתחיל אימון מודלים לתאריך {cutoff_date}")
        
        for horizon in horizons:
            print(f"  📚 מאמן מודל {horizon}D...")
            
            try:
                # יצירת שם מודל ייחודי
                model_name = f"model_{horizon}d_{cutoff_date.replace('-', '')}"
                model_path = os.path.join(self.base_model_dir, f"{model_name}.pkl")
                
                # אימון המודל (כרגע דמיוני - בפועל נקרא ל-train_model מהמודול הקיים)
                model_data = self._train_horizon_model(cutoff_date, horizon)
                
                # שמירת המודל
                with open(model_path, 'wb') as f:
                    pickle.dump(model_data, f)
                
                trained_models[horizon] = model_path
                print(f"    ✅ נשמר: {model_path}")
                
            except Exception as e:
                print(f"    ❌ שגיאה באימון מודל {horizon}D: {e}")
                continue
        
        return trained_models
    
    def _train_horizon_model(self, cutoff_date: str, horizon: int) -> Dict[str, Any]:
        """
        אימון מודל ספציפי לאופק זמן
        TODO: שילוב עם ml/train_model.py הקיים
        """
        # זהו placeholder - בפועל נקרא לפונקציות האימון הקיימות
        try:
            from ml.train_model import train_model, collect_training_data
            from ml.feature_engineering import build_training_frame
            
            # איסוף נתוני אימון עד תאריך הגבול
            print(f"      🔍 אוסף נתוני אימון עד {cutoff_date} לאופק {horizon}D")
            
            # כרגע נחזיר מודל מדומה
            # בפועל כאן יהיה הקוד האמיתי
            model_data = {
                'horizon': horizon,
                'cutoff_date': cutoff_date,
                'model_type': 'RandomForest',  # או XGB/LGBM
                'trained_at': datetime.now().isoformat(),
                'features': ['feature1', 'feature2', 'feature3'],  # רשימה אמיתית
                'performance': {'train_score': 0.72, 'val_score': 0.68},
                'model_object': 'serialized_model_here'  # מודל סקלארן מסוריאל
            }
            
            return model_data
            
        except ImportError:
            # fallback אם אין מודולי ML
            return {
                'horizon': horizon,
                'cutoff_date': cutoff_date,
                'model_type': 'MockModel',
                'trained_at': datetime.now().isoformat(),
                'mock': True
            }
    
    def run_historical_scan(self, scan_date: str, models: Dict[int, str], symbols: List[str] = None) -> List[Dict]:
        """
        הרצת סריקה היסטורית עם מודלים נתונים
        
        Args:
            scan_date: תאריך הסריקה (YYYY-MM-DD)
            models: מיפוי אופק → נתיב מודל
            symbols: רשימת סמלים לבדיקה
        
        Returns:
            רשימת תוצאות סריקה
        """
        if symbols is None:
            symbols = self._get_symbols_for_date(scan_date)
        
        print(f"🔍 מריץ סריקה היסטורית ל-{scan_date} על {len(symbols)} מניות")
        
        scan_results = []
        
        for i, symbol in enumerate(symbols):
            if i % 50 == 0:  # עדכון כל 50 מניות
                print(f"  📊 מעבד {i+1}/{len(symbols)} מניות...")
                
            try:
                # טעינת נתונים היסטוריים עד התאריך
                historical_data = self._load_historical_data(symbol, scan_date)
                
                if historical_data is None or len(historical_data) < 50:
                    continue  # לא מספיק נתונים
                
                # הרצת חזאי עם כל מודל
                predictions = {}
                for horizon, model_path in models.items():
                    try:
                        model = self._load_model(model_path)
                        pred_prob = self._predict_with_model(model, historical_data, horizon)
                        predictions[f'{horizon}d'] = pred_prob
                    except Exception as e:
                        print(f"    ⚠️ שגיאה בחזאי {horizon}D עבור {symbol}: {e}")
                        predictions[f'{horizon}d'] = None
                
                scan_results.append({
                    'symbol': symbol,
                    'scan_date': scan_date,
                    'predictions': predictions,
                    'price_at_scan': float(historical_data['Close'].iloc[-1]),
                    'volume': float(historical_data['Volume'].iloc[-1]) if 'Volume' in historical_data else 0
                })
                
            except Exception as e:
                print(f"    ❌ שגיאה בעיבוד {symbol}: {e}")
                continue
        
        print(f"  ✅ הסתיים - {len(scan_results)} תוצאות")
        return scan_results
    
    def validate_predictions(self, scan_results: List[Dict], validation_date: str) -> List[Dict]:
        """
        בדיקת תוצאות אמיתיות מול חזאי
        
        Args:
            scan_results: תוצאות הסריקה המקורית
            validation_date: תאריך הבדיקה (עד כמה זמן קיים מידע)
        
        Returns:
            תוצאות עם validation
        """
        print(f"✅ בודק תוצאות אמיתיות עד {validation_date}")
        
        validated_results = []
        
        for result in scan_results:
            symbol = result['symbol']
            scan_date = result['scan_date']
            entry_price = result['price_at_scan']
            
            # בדיקת תוצאות אמיתיות לכל אופק
            actual_outcomes = {}
            scan_dt = datetime.strptime(scan_date, '%Y-%m-%d')
            val_dt = datetime.strptime(validation_date, '%Y-%m-%d')
            
            for horizon in [1, 5, 10]:
                target_date = self._add_business_days(scan_dt, horizon)
                
                if target_date <= val_dt:
                    try:
                        actual_price = self._get_price_on_date(symbol, target_date.strftime('%Y-%m-%d'))
                        
                        if actual_price is not None:
                            return_pct = (actual_price - entry_price) / entry_price * 100
                            success = return_pct >= 1.0  # 1%+ תשואה = הצלחה
                            
                            actual_outcomes[f'{horizon}d'] = {
                                'success': success,
                                'actual_price': actual_price,
                                'return_pct': return_pct,
                                'target_date': target_date.strftime('%Y-%m-%d')
                            }
                    except Exception as e:
                        print(f"    ⚠️ לא הצליח לקבל מחיר {symbol} ל-{target_date}: {e}")
                        continue
            
            if actual_outcomes:  # רק אם יש לפחות תוצאה אחת
                result['actual_outcomes'] = actual_outcomes
                validated_results.append(result)
        
        print(f"  ✅ ולידציה הושלמה - {len(validated_results)} תוצאות מאומתות")
        return validated_results
    
    def analyze_performance(self, validated_results: List[Dict]) -> Dict[str, ModelPerformance]:
        """
        ניתוח ביצועי המודלים
        """
        print("📊 מנתח ביצועי מודלים...")
        
        performance_by_horizon = {}
        
        for horizon in [1, 5, 10]:
            horizon_key = f'{horizon}d'
            
            # איסוף תחזיות ותוצאות לאופק הזה
            predictions = []
            outcomes = []
            
            for result in validated_results:
                if (horizon_key in result.get('predictions', {}) and 
                    result['predictions'][horizon_key] is not None and
                    horizon_key in result.get('actual_outcomes', {})):
                    
                    pred = result['predictions'][horizon_key]
                    outcome = result['actual_outcomes'][horizon_key]['success']
                    
                    predictions.append(pred)
                    outcomes.append(outcome)
            
            if not predictions:
                continue
            
            # חישוב מטריקות
            total_preds = len(predictions)
            accuracy = sum(outcomes) / total_preds
            
            # דיוק ברמת ביטחון גבוהה (>= 0.7)
            high_conf_preds = [(p, o) for p, o in zip(predictions, outcomes) if p >= 0.7]
            high_conf_acc = (sum(o for p, o in high_conf_preds) / len(high_conf_preds) 
                           if high_conf_preds else 0.0)
            
            # סף אופטימלי
            optimal_threshold = self._find_optimal_threshold(predictions, outcomes)
            
            performance_by_horizon[horizon_key] = ModelPerformance(
                horizon=horizon,
                date=validated_results[0]['scan_date'] if validated_results else 'unknown',
                total_predictions=total_preds,
                accuracy=accuracy,
                high_conf_accuracy=high_conf_acc,
                suggested_threshold=optimal_threshold,
                model_path='unknown'  # נוסיף אחר כך
            )
            
            print(f"  📈 {horizon}D: {accuracy:.1%} accuracy, {total_preds} predictions")
        
        return performance_by_horizon
    
    def run_rolling_backtest(self, config: BacktestConfig) -> List[Dict]:
        """
        הרצת backtest מתגלגל
        """
        print(f"🚀 מתחיל Rolling Backtest: {config.start_date} → {config.end_date}")
        
        current_date = datetime.strptime(config.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(config.end_date, '%Y-%m-%d')
        
        results_timeline = []
        iteration = 0
        
        while current_date <= end_date:
            iteration += 1
            date_str = current_date.strftime('%Y-%m-%d')
            
            print(f"\n📅 איטרציה #{iteration}: {date_str}")
            
            try:
                # שלב 1: אימון מודלים
                models = self.train_multi_horizon_models(date_str, config.horizons)
                
                if not models:
                    print("  ❌ נכשל באימון מודלים - דילוג")
                    current_date += timedelta(days=config.step_days)
                    continue
                
                # שלב 2: סריקה היסטורית
                scan_results = self.run_historical_scan(date_str, models)
                
                if not scan_results:
                    print("  ❌ לא נמצאו תוצאות סריקה - דילוג")
                    current_date += timedelta(days=config.step_days)
                    continue
                
                # שלב 3: המתנה לתוצאות (בדיקה 14 ימים אחרי)
                validation_date = current_date + timedelta(days=14)
                
                if validation_date <= end_date:
                    # שלב 4: ולידציה
                    validated = self.validate_predictions(scan_results, validation_date.strftime('%Y-%m-%d'))
                    
                    if validated:
                        # שלב 5: ניתוח
                        performance = self.analyze_performance(validated)
                        
                        # שמירת תוצאות
                        iteration_result = {
                            'iteration': iteration,
                            'date': date_str,
                            'validation_date': validation_date.strftime('%Y-%m-%d'),
                            'scan_count': len(scan_results),
                            'validated_count': len(validated),
                            'performance': {k: {
                                'horizon': p.horizon,
                                'accuracy': p.accuracy,
                                'high_conf_accuracy': p.high_conf_accuracy,
                                'total_predictions': p.total_predictions,
                                'suggested_threshold': p.suggested_threshold
                            } for k, p in performance.items()},
                            'models_used': models
                        }
                        
                        results_timeline.append(iteration_result)
                        
                        # שמירת תוצאות ביניים
                        self._save_interim_results(iteration_result)
                        
                        print(f"  ✅ איטרציה הושלמה - {len(validated)} תוצאות מאומתות")
                    else:
                        print("  ⚠️ לא נמצאו תוצאות מאומתות")
                else:
                    print(f"  ⏳ ממתין לתאריך ולידציה ({validation_date.strftime('%Y-%m-%d')})")
                
            except Exception as e:
                print(f"  ❌ שגיאה באיטרציה: {e}")
            
            # התקדמות לאיטרציה הבאה
            current_date += timedelta(days=config.step_days)
        
        print(f"\n🎉 Backtest הושלם! {len(results_timeline)} איטרציות מוצלחות")
        
        # שמירת תוצאות סופיות
        final_results_path = os.path.join(self.results_dir, f"backtest_{config.start_date}_{config.end_date}.json")
        with open(final_results_path, 'w', encoding='utf-8') as f:
            json.dump(results_timeline, f, indent=2, ensure_ascii=False)
        
        print(f"📁 תוצאות נשמרו: {final_results_path}")
        
        return results_timeline
    
    # Helper methods (implementation stubs)
    def _get_symbols_for_date(self, date: str) -> List[str]:
        """קבלת רשימת סמלים זמינים לתאריך"""
        # כרגע רשימה קבועה - בפועל נשלוף מהדטה
        return ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA', 'META', 'AMZN']
    
    def _load_historical_data(self, symbol: str, until_date: str) -> Optional[pd.DataFrame]:
        """טעינת נתונים היסטוריים עד תאריך נתון"""
        # TODO: שילוב עם מערכת הנתונים הקיימת
        # כרגע מדומה
        try:
            dates = pd.date_range(end=until_date, periods=100)
            np.random.seed(hash(symbol) % 2**32)  # חזרתיות לפי סמל
            data = {
                'Close': 100 + np.cumsum(np.random.randn(100) * 0.02),
                'Volume': np.random.randint(1000000, 10000000, 100)
            }
            df = pd.DataFrame(data, index=dates)
            return df
        except:
            return None
    
    def _load_model(self, model_path: str) -> Dict[str, Any]:
        """טעינת מודל משמור"""
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    def _predict_with_model(self, model: Dict[str, Any], data: pd.DataFrame, horizon: int) -> float:
        """הרצת חזאי עם מודל נתון"""
        # כרגע חזאי מדומה - בפועל נשתמש במודל האמיתי
        if model.get('mock'):
            # חזאי מדומה מבוסס על תנודתיות
            recent_returns = data['Close'].pct_change().tail(10)
            volatility = recent_returns.std()
            trend = recent_returns.mean()
            
            base_prob = 0.5 + trend * 5  # נטייה בסיסית
            uncertainty = volatility * 2   # ספק
            
            prob = np.clip(base_prob + np.random.normal(0, uncertainty), 0.1, 0.9)
            return float(prob)
        else:
            # TODO: שילוב עם מודל אמיתי
            return 0.6  # placeholder
    
    def _get_price_on_date(self, symbol: str, date: str) -> Optional[float]:
        """קבלת מחיר מניה בתאריך נתון"""
        # TODO: שילוב עם מערכת הנתונים
        # כרגע מדומה
        data = self._load_historical_data(symbol, date)
        if data is not None:
            return float(data['Close'].iloc[-1])
        return None
    
    def _add_business_days(self, start_date: datetime, days: int) -> datetime:
        """הוספת ימי עסקים"""
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # לא שבת/ראשון
                added += 1
        return current
    
    def _find_optimal_threshold(self, predictions: List[float], outcomes: List[bool]) -> float:
        """מציאת סף אופטימלי"""
        try:
            from sklearn.metrics import roc_curve
            fpr, tpr, thresholds = roc_curve(outcomes, predictions)
            optimal_idx = np.argmax(tpr - fpr)
            return float(thresholds[optimal_idx])
        except:
            # fallback פשוט
            return 0.5
    
    def _save_interim_results(self, result: Dict[str, Any]):
        """שמירת תוצאות ביניים"""
        interim_path = os.path.join(self.results_dir, f"interim_{result['date']}.json")
        with open(interim_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

def demo_historical_training():
    """הדמיה של המערכת"""
    print("🕰️ Historical Multi-Horizon Training Demo")
    print("=" * 50)
    
    # הגדרת תצורה
    config = BacktestConfig(
        start_date="2024-08-01",
        end_date="2024-08-15",  # תקופה קצרה לדמו
        step_days=7,
        horizons=[1, 5, 10]
    )
    
    # יצירת מערכת
    system = HistoricalTrainingSystem()
    
    # הרצת backtest
    results = system.run_rolling_backtest(config)
    
    # הצגת תוצאות
    if results:
        print(f"\n📊 סיכום תוצאות ({len(results)} איטרציות):")
        print("-" * 40)
        
        for result in results:
            print(f"📅 {result['date']}:")
            for horizon_key, perf in result['performance'].items():
                print(f"  {horizon_key}: {perf['accuracy']:.1%} accuracy ({perf['total_predictions']} preds)")
    else:
        print("❌ לא נמצאו תוצאות")

if __name__ == "__main__":
    demo_historical_training()