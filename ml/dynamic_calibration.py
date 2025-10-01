"""
Live Performance Tracking & Dynamic Calibration

הרעיון: לקחת תחזיות מלפני 5-10 ימים, לבדוק איך הן התממשו,
ולהשתמש בזה לכוונון דינמי של הסריקה.

Implementation Plan:
1. Live Validation: בדיקת תחזיות בזמן אמת
2. Dynamic Thresholds: עדכון ספים באופן אוטומטי  
3. Adaptive Scoring: התאמת משקלים בציון המרוכב
4. Performance Feedback: מתן משוב למשתמש על איכות החזאי
"""

import os
import json
import datetime
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class LivePerformance:
    """Live performance metrics for recent predictions"""
    total_predictions: int
    correct_5d: int
    correct_10d: int
    accuracy_5d: float
    accuracy_10d: float
    avg_ml_prob: float
    confidence_score: float

class DynamicCalibrator:
    """
    מערכת כיול דינמית שבודקת ביצועים בזמן אמת
    ומתאימה את פרמטרי הסריקה בהתאם
    """
    
    def __init__(self, pred_log_path: str = "ml/predictions.jsonl"):
        self.pred_log_path = pred_log_path
        self.min_samples = 10  # מספר מינימלי של דגימות לכיול
        
    def check_recent_performance(self, days_back: int = 10) -> Optional[LivePerformance]:
        """
        בדיקת ביצועים של תחזיות מהימים האחרונים
        """
        if not os.path.exists(self.pred_log_path):
            return None
            
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_back)
        recent_preds = []
        
        # קריאת התחזיות הרלוונטיות
        with open(self.pred_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    pred_date = datetime.datetime.strptime(rec.get('date', ''), '%Y-%m-%d')
                    if pred_date >= cutoff_date and 'realized' in rec:
                        recent_preds.append(rec)
                except Exception:
                    continue
        
        if len(recent_preds) < self.min_samples:
            return None
            
        # חישוב מטריקות
        total = len(recent_preds)
        correct_5d = sum(1 for p in recent_preds 
                        if p.get('realized', {}).get('5d') == 1)
        correct_10d = sum(1 for p in recent_preds 
                         if p.get('realized', {}).get('10d') == 1)
        
        accuracy_5d = correct_5d / total
        accuracy_10d = correct_10d / total
        avg_ml_prob = sum(p.get('prob', 0) for p in recent_preds) / total
        
        # ציון אמינות - כמה החזאי עקבי
        confidence_score = min(accuracy_5d, accuracy_10d) * (total / 20)  # normalized
        
        return LivePerformance(
            total_predictions=total,
            correct_5d=correct_5d,
            correct_10d=correct_10d,
            accuracy_5d=accuracy_5d,
            accuracy_10d=accuracy_10d,
            avg_ml_prob=avg_ml_prob,
            confidence_score=min(confidence_score, 1.0)
        )
    
    def suggest_threshold_adjustment(self, performance: LivePerformance) -> Dict[str, Any]:
        """
        הצעת התאמות לפרמטרי הסריקה על בסיס הביצועים
        """
        adjustments = {
            'ml_threshold_adjustment': 0.0,
            'score_weight_adjustments': {},
            'confidence_level': 'medium',
            'recommendations': []
        }
        
        # התאמת סף ML
        if performance.accuracy_5d < 0.4:  # ביצועים חלשים
            adjustments['ml_threshold_adjustment'] = 0.1  # העלה סף
            adjustments['recommendations'].append("ביצועים חלשים - מעלה סף ML ל-0.6+")
            adjustments['confidence_level'] = 'low'
        elif performance.accuracy_5d > 0.7:  # ביצועים מעולים
            adjustments['ml_threshold_adjustment'] = -0.05  # הורד סף מעט
            adjustments['recommendations'].append("ביצועים מעולים - מוריד סף ML ל-0.45")
            adjustments['confidence_level'] = 'high'
        
        # התאמת משקלים בציון
        if performance.accuracy_5d > performance.accuracy_10d + 0.1:
            # 5 ימים עובד יותר טוב
            adjustments['score_weight_adjustments'] = {
                'w_prob': 0.60,  # תן יותר משקל ל-ML
                'w_rr': 0.20,
                'w_fresh': 0.15,
                'w_pattern': 0.05
            }
            adjustments['recommendations'].append("תחזית קצרת טווח יותר מדויקת - מגביר משקל ML")
        
        return adjustments
    
    def get_calibration_report(self) -> str:
        """
        דוח כיול עם המלצות לשיפור
        """
        performance = self.check_recent_performance()
        if not performance:
            return "❌ אין מספיק נתונים לכיול (נדרשות לפחות 10 תחזיות)"
        
        adjustments = self.suggest_threshold_adjustment(performance)
        
        report = f"""
📊 **דוח כיול דינמי**

**ביצועים אחרונים ({performance.total_predictions} תחזיות):**
• דיוק 5 ימים: {performance.accuracy_5d:.1%} ({performance.correct_5d}/{performance.total_predictions})
• דיוק 10 ימים: {performance.accuracy_10d:.1%} ({performance.correct_10d}/{performance.total_predictions})
• הסתברות ממוצעת: {performance.avg_ml_prob:.3f}
• ציון אמינות: {performance.confidence_score:.2f}/1.0

**רמת אמינות: {adjustments['confidence_level'].upper()}**

**המלצות:**
{chr(10).join('• ' + rec for rec in adjustments['recommendations'])}

**התאמות מוצעות:**
• סף ML: {adjustments['ml_threshold_adjustment']:+.3f}
• משקלי ציון: {adjustments.get('score_weight_adjustments', 'ללא שינוי')}
"""
        
        return report

def integrate_with_scanning(scan_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    שילוב הכיול הדינמי עם פרמטרי הסריקה
    """
    calibrator = DynamicCalibrator()
    performance = calibrator.check_recent_performance()
    
    if performance and performance.total_predictions >= 10:
        adjustments = calibrator.suggest_threshold_adjustment(performance)
        
        # עדכון פרמטרים
        current_threshold = scan_params.get('ml_min_prob', 0.5)
        new_threshold = max(0.3, min(0.8, 
            current_threshold + adjustments['ml_threshold_adjustment']))
        
        scan_params['ml_min_prob'] = new_threshold
        
        # עדכון משקלים אם יש המלצה
        if adjustments.get('score_weight_adjustments'):
            scan_params.update(adjustments['score_weight_adjustments'])
        
        # הוספת מידע על הכיול
        scan_params['_calibration_info'] = {
            'performance': performance,
            'adjustments_applied': adjustments,
            'calibration_timestamp': datetime.datetime.now().isoformat()
        }
    
    return scan_params

if __name__ == "__main__":
    # דמו של המערכת
    calibrator = DynamicCalibrator()
    print(calibrator.get_calibration_report())
    
    # דמו של שילוב עם סריקה
    sample_params = {
        'ml_min_prob': 0.5,
        'w_prob': 0.55,
        'w_rr': 0.25,
        'w_fresh': 0.15,
        'w_pattern': 0.05
    }
    
    print("\n" + "="*50)
    print("פרמטרים לפני כיול:", sample_params)
    
    updated_params = integrate_with_scanning(sample_params)
    print("פרמטרים אחרי כיול:", updated_params)