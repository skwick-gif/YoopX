#!/usr/bin/env python3
"""
🧪 Dynamic Calibration Prototype

תסריט לבדיקת הרעיון של כיול דינמי בזמן אמת.
מדמה תחזיות, בודק את התוצאות, ומציע התאמות.
"""

import json
import random
import datetime
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class Prediction:
    symbol: str
    date: str
    ml_prob: float
    price: float
    market_context: str  # "bull", "bear", "sideways"
    sector: str
    actual_5d: Optional[bool] = None
    actual_10d: Optional[bool] = None

class MarketSimulator:
    """מדמה תנאי שוק ותוצאות מניות"""
    
    def __init__(self):
        self.market_regimes = ["bull", "bear", "sideways"]
        self.sectors = ["tech", "healthcare", "finance", "energy", "consumer"]
        # דיוק לפי תנאי שוק (אמת לפי מחקרים)
        self.regime_accuracy = {
            "bull": 0.72,      # שוק עולה - ML עובד טוב
            "bear": 0.45,      # שוק יורד - ML נאבק
            "sideways": 0.58   # שוק צידי - ביצועים בינוניים
        }
        
    def generate_market_context(self, date: str) -> str:
        """יוצר תנאי שוק רנדומליים עם רצף הגיוני"""
        # פשטות: רנדום עם נטייה לרצפים
        return random.choice(self.market_regimes)
    
    def simulate_outcome(self, pred: Prediction) -> Tuple[bool, bool]:
        """מדמה תוצאות אמיתיות בהתבסס על הקשר השוק"""
        base_accuracy = self.regime_accuracy[pred.market_context]
        
        # התאמה לפי סקטור (טק יותר תנודתי)
        sector_modifier = {
            "tech": -0.05,      # יותר קשה לחזות
            "healthcare": 0.03, # יציב יותר
            "finance": -0.02,   # רגיש לריבית
            "energy": -0.08,    # מאוד תנודתי
            "consumer": 0.01    # יציב
        }
        
        adjusted_accuracy = base_accuracy + sector_modifier.get(pred.sector, 0)
        
        # ככל שהסתברות ML גבוהה יותר, כך הסיכוי להצלחה רב יותר
        prob_boost = (pred.ml_prob - 0.5) * 0.3  # boost מקסימלי של 15%
        final_accuracy = min(0.9, max(0.1, adjusted_accuracy + prob_boost))
        
        # 5 ימים - דיוק יותר גבוה
        success_5d = random.random() < final_accuracy
        # 10 ימים - דיוק מעט יותר נמוך (יותר רעש)
        success_10d = random.random() < (final_accuracy * 0.9)
        
        return success_5d, success_10d

class CalibrationEngine:
    """מנוע הכיול הדינמי"""
    
    def __init__(self, min_samples: int = 15):
        self.min_samples = min_samples
        self.history: List[Prediction] = []
        
    def add_prediction(self, pred: Prediction):
        """הוספת תחזית חדשה"""
        self.history.append(pred)
        
    def validate_recent_predictions(self, simulator: MarketSimulator):
        """מדמה בדיקת תוצאות תחזיות שהגיע זמנן"""
        today = datetime.datetime.now()
        
        for pred in self.history:
            if pred.actual_5d is None:  # עדיין לא נבדק
                pred_date = datetime.datetime.strptime(pred.date, '%Y-%m-%d')
                days_passed = (today - pred_date).days
                
                if days_passed >= 5:
                    pred.actual_5d, pred.actual_10d = simulator.simulate_outcome(pred)
                    print(f"✓ {pred.symbol}: ML={pred.ml_prob:.2f} → 5d={pred.actual_5d}, 10d={pred.actual_10d}")
    
    def calculate_performance_metrics(self, days_back: int = 14) -> Dict:
        """חישוב מטריקות ביצועים"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        
        recent_preds = [p for p in self.history 
                       if datetime.datetime.strptime(p.date, '%Y-%m-%d') >= cutoff_date
                       and p.actual_5d is not None]
        
        if len(recent_preds) < self.min_samples:
            return {"status": "insufficient_data", "count": len(recent_preds)}
        
        # חישוב מטריקות בסיסיות
        accuracy_5d = sum(p.actual_5d for p in recent_preds) / len(recent_preds)
        accuracy_10d = sum(p.actual_10d for p in recent_preds) / len(recent_preds)
        avg_ml_prob = sum(p.ml_prob for p in recent_preds) / len(recent_preds)
        
        # מטריקות מתקדמות
        high_conf_preds = [p for p in recent_preds if p.ml_prob >= 0.7]
        high_conf_accuracy = (sum(p.actual_5d for p in high_conf_preds) / len(high_conf_preds) 
                            if high_conf_preds else 0)
        
        # ביצועים לפי תנאי שוק
        regime_performance = {}
        for regime in ["bull", "bear", "sideways"]:
            regime_preds = [p for p in recent_preds if p.market_context == regime]
            if regime_preds:
                regime_performance[regime] = {
                    "count": len(regime_preds),
                    "accuracy_5d": sum(p.actual_5d for p in regime_preds) / len(regime_preds)
                }
        
        return {
            "status": "valid",
            "total_predictions": len(recent_preds),
            "accuracy_5d": accuracy_5d,
            "accuracy_10d": accuracy_10d,
            "avg_ml_prob": avg_ml_prob,
            "high_conf_accuracy": high_conf_accuracy,
            "regime_performance": regime_performance
        }
    
    def suggest_calibration_adjustments(self, metrics: Dict) -> Dict:
        """הצעת התאמות לפרמטרי המערכת"""
        if metrics["status"] != "valid":
            return {"action": "wait", "reason": "Not enough data"}
        
        adjustments = {
            "ml_threshold_change": 0.0,
            "weight_adjustments": {},
            "confidence_level": "medium",
            "reasoning": []
        }
        
        acc_5d = metrics["accuracy_5d"]
        
        # התאמת סף ML
        if acc_5d < 0.45:
            adjustments["ml_threshold_change"] = +0.08
            adjustments["confidence_level"] = "low"
            adjustments["reasoning"].append(f"דיוק נמוך ({acc_5d:.1%}) - מעלה סף ML")
            
        elif acc_5d < 0.55:
            adjustments["ml_threshold_change"] = +0.03
            adjustments["reasoning"].append(f"דיוק בינוני ({acc_5d:.1%}) - מעלה מעט את הסף")
            
        elif acc_5d > 0.75:
            adjustments["ml_threshold_change"] = -0.03
            adjustments["confidence_level"] = "high"
            adjustments["reasoning"].append(f"דיוק גבוה ({acc_5d:.1%}) - מוריד סף לתוצאות יותר")
        
        # התאמת משקלים
        if acc_5d > metrics["accuracy_10d"] + 0.1:
            adjustments["weight_adjustments"] = {
                "w_prob": 0.60,  # יותר משקל ל-ML
                "w_rr": 0.22,
                "w_fresh": 0.15,
                "w_pattern": 0.03
            }
            adjustments["reasoning"].append("5 ימים עובד יותר טוב - מגביר משקל ML")
        
        # ביצועים גרועים בכל הרמות
        if acc_5d < 0.4 and metrics["high_conf_accuracy"] < 0.5:
            adjustments["weight_adjustments"] = {
                "w_prob": 0.35,  # פחות משקל ל-ML
                "w_rr": 0.35,    # יותר למדדים טכניים
                "w_fresh": 0.20,
                "w_pattern": 0.10
            }
            adjustments["reasoning"].append("ML נאבק - עובר לדגש טכני")
        
        return adjustments

def run_simulation_demo():
    """הדמיה מלאה של המערכת"""
    print("🧪 Dynamic Calibration Simulation")
    print("=" * 50)
    
    simulator = MarketSimulator()
    engine = CalibrationEngine()
    
    # יצירת תחזיות היסטוריות (מדמה 3 שבועות של פעילות)
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "META", "AMZN", "NFLX"]
    
    for day_offset in range(21, 0, -1):  # 21 ימים אחורה עד היום
        pred_date = (datetime.datetime.now() - datetime.timedelta(days=day_offset)).strftime('%Y-%m-%d')
        
        # 2-4 תחזיות ליום
        daily_predictions = random.randint(2, 4)
        for _ in range(daily_predictions):
            pred = Prediction(
                symbol=random.choice(symbols),
                date=pred_date,
                ml_prob=random.uniform(0.3, 0.9),  # מגוון הסתברויות
                price=random.uniform(50, 300),
                market_context=simulator.generate_market_context(pred_date),
                sector=random.choice(simulator.sectors)
            )
            engine.add_prediction(pred)
    
    print(f"Generated {len(engine.history)} historical predictions")
    print()
    
    # "בדיקת" תוצאות (מדמה מה שקורה כל יום באמת)
    print("📊 Validating recent predictions...")
    engine.validate_recent_predictions(simulator)
    print()
    
    # חישוב מטריקות ביצועים
    print("📈 Performance Analysis")
    print("-" * 30)
    metrics = engine.calculate_performance_metrics()
    
    if metrics["status"] == "valid":
        print(f"Total Predictions: {metrics['total_predictions']}")
        print(f"5-Day Accuracy: {metrics['accuracy_5d']:.1%}")
        print(f"10-Day Accuracy: {metrics['accuracy_10d']:.1%}")
        print(f"Avg ML Probability: {metrics['avg_ml_prob']:.3f}")
        print(f"High Confidence Accuracy: {metrics['high_conf_accuracy']:.1%}")
        print()
        
        # ביצועים לפי תנאי שוק
        print("Market Regime Performance:")
        for regime, perf in metrics["regime_performance"].items():
            print(f"  {regime.title()}: {perf['accuracy_5d']:.1%} ({perf['count']} predictions)")
        print()
        
        # הצעות כיול
        print("🎯 Calibration Suggestions")
        print("-" * 30)
        adjustments = engine.suggest_calibration_adjustments(metrics)
        
        if adjustments["ml_threshold_change"] != 0:
            print(f"ML Threshold Adjustment: {adjustments['ml_threshold_change']:+.3f}")
        
        if adjustments["weight_adjustments"]:
            print("Suggested Weight Changes:")
            for weight, value in adjustments["weight_adjustments"].items():
                print(f"  {weight}: {value:.2f}")
        
        print(f"Confidence Level: {adjustments['confidence_level'].upper()}")
        print("\nReasoning:")
        for reason in adjustments["reasoning"]:
            print(f"• {reason}")
    else:
        print(f"❌ {metrics['status']}: Only {metrics['count']} predictions available")
    
    print()
    print("🔄 Next Steps:")
    print("1. Apply suggested adjustments to live scanning")
    print("2. Monitor performance for next 5-7 days") 
    print("3. Re-calibrate based on new results")
    print("4. Implement automated alerts for performance drops")

if __name__ == "__main__":
    run_simulation_demo()