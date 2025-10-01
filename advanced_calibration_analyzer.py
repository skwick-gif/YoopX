#!/usr/bin/env python3
"""
🔬 Advanced Calibration Analysis Tool

כלי מתקדם לניתוח וכיול דינמי של ביצועי ML
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from dataclasses import dataclass

@dataclass
class CalibrationStrategy:
    name: str
    description: str
    trigger_condition: callable
    adjustment_logic: callable
    confidence_threshold: float = 0.6

class AdvancedCalibrator:
    """מנוע כיול מתקדם עם אסטרטגיות מרובות"""
    
    def __init__(self):
        self.strategies = self._initialize_strategies()
        self.performance_history = []
        
    def _initialize_strategies(self) -> List[CalibrationStrategy]:
        """אתחול אסטרטגיות כיול שונות"""
        
        def conservative_strategy_trigger(metrics):
            return metrics.get('accuracy_5d', 0) < 0.5
            
        def conservative_adjustment(current_params, metrics):
            return {
                'ml_threshold': min(0.8, current_params.get('ml_threshold', 0.5) + 0.1),
                'weights': {'w_prob': 0.45, 'w_rr': 0.30, 'w_fresh': 0.20, 'w_pattern': 0.05}
            }
        
        def aggressive_strategy_trigger(metrics):
            return metrics.get('accuracy_5d', 0) > 0.75 and metrics.get('total_predictions', 0) > 30
            
        def aggressive_adjustment(current_params, metrics):
            return {
                'ml_threshold': max(0.3, current_params.get('ml_threshold', 0.5) - 0.05),
                'weights': {'w_prob': 0.65, 'w_rr': 0.20, 'w_fresh': 0.10, 'w_pattern': 0.05}
            }
        
        def market_adaptive_trigger(metrics):
            regime_perf = metrics.get('regime_performance', {})
            if len(regime_perf) < 2:
                return False
            # אם יש פער גדול בין רז'ימים
            accuracies = [r.get('accuracy_5d', 0) for r in regime_perf.values()]
            return max(accuracies) - min(accuracies) > 0.2
            
        def market_adaptive_adjustment(current_params, metrics):
            # התאמה דינמית לפי תנאי שוק
            regime_perf = metrics.get('regime_performance', {})
            best_regime = max(regime_perf.keys(), 
                            key=lambda k: regime_perf[k].get('accuracy_5d', 0))
            
            if best_regime == 'bull':
                return {
                    'ml_threshold': 0.45,  # אגרסיבי יותר בשוק עולה
                    'weights': {'w_prob': 0.60, 'w_rr': 0.25, 'w_fresh': 0.10, 'w_pattern': 0.05}
                }
            elif best_regime == 'bear':
                return {
                    'ml_threshold': 0.65,  # שמרני בשוק יורד
                    'weights': {'w_prob': 0.40, 'w_rr': 0.35, 'w_fresh': 0.20, 'w_pattern': 0.05}
                }
            else:  # sideways
                return {
                    'ml_threshold': 0.55,
                    'weights': {'w_prob': 0.50, 'w_rr': 0.25, 'w_fresh': 0.15, 'w_pattern': 0.10}
                }
        
        return [
            CalibrationStrategy(
                "Conservative", 
                "מעבר למצב שמרני כשהביצועים נמוכים",
                conservative_strategy_trigger, 
                conservative_adjustment
            ),
            CalibrationStrategy(
                "Aggressive", 
                "מעבר למצב אגרסיבי כשהביצועים גבוהים",
                aggressive_strategy_trigger, 
                aggressive_adjustment,
                0.8
            ),
            CalibrationStrategy(
                "Market-Adaptive", 
                "התאמה דינמית לתנאי השוק",
                market_adaptive_trigger, 
                market_adaptive_adjustment,
                0.7
            )
        ]
    
    def analyze_performance_trends(self, metrics_history: List[Dict]) -> Dict:
        """ניתוח טרנדים בביצועים לאורך זמן"""
        if len(metrics_history) < 3:
            return {"status": "insufficient_data"}
        
        df = pd.DataFrame(metrics_history)
        
        # טרנדים
        accuracy_trend = np.polyfit(range(len(df)), df['accuracy_5d'], 1)[0]
        prob_trend = np.polyfit(range(len(df)), df['avg_ml_prob'], 1)[0]
        
        # תנודתיות
        accuracy_volatility = df['accuracy_5d'].std()
        
        # מציאת תבניות
        patterns = []
        
        # זיהוי ירידה עקבית
        if accuracy_trend < -0.05:
            patterns.append("declining_performance")
        
        # זיהוי חוסר יציבות
        if accuracy_volatility > 0.15:
            patterns.append("high_volatility")
        
        # זיהוי שיפור עקבי
        if accuracy_trend > 0.03:
            patterns.append("improving_performance")
        
        return {
            "status": "valid",
            "accuracy_trend": accuracy_trend,
            "probability_trend": prob_trend,
            "volatility": accuracy_volatility,
            "patterns": patterns,
            "periods_analyzed": len(df)
        }
    
    def recommend_calibration_strategy(self, metrics: Dict, trends: Dict) -> Dict:
        """המלצה על אסטרטגיית כיול מתאימה"""
        recommendations = []
        
        for strategy in self.strategies:
            if strategy.trigger_condition(metrics):
                confidence = self._calculate_strategy_confidence(strategy, metrics, trends)
                if confidence >= strategy.confidence_threshold:
                    recommendations.append({
                        "strategy": strategy.name,
                        "description": strategy.description,
                        "confidence": confidence,
                        "adjustments": strategy.adjustment_logic({}, metrics)
                    })
        
        # מיון לפי רמת ביטחון
        recommendations.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "recommendations": recommendations,
            "top_choice": recommendations[0] if recommendations else None
        }
    
    def _calculate_strategy_confidence(self, strategy: CalibrationStrategy, 
                                     metrics: Dict, trends: Dict) -> float:
        """חישוב רמת ביטחון באסטרטגיה"""
        base_confidence = 0.5
        
        # יותר ביטחון אם יש יותר נתונים
        sample_size = metrics.get('total_predictions', 0)
        if sample_size > 50:
            base_confidence += 0.2
        elif sample_size > 20:
            base_confidence += 0.1
        
        # פחות ביטחון אם יש תנודתיות גבוהה
        volatility = trends.get('volatility', 0)
        if volatility > 0.2:
            base_confidence -= 0.15
        
        # יותר ביטחון אם הטרנד ברור
        trend_strength = abs(trends.get('accuracy_trend', 0))
        if trend_strength > 0.05:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def generate_comprehensive_report(self, metrics: Dict, trends: Dict, 
                                    recommendations: Dict) -> str:
        """יצירת דוח מקיף"""
        
        report_lines = [
            "🔬 **Advanced Calibration Analysis Report**",
            "=" * 60,
            f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 📊 Current Performance Metrics",
            f"• Total Predictions: {metrics.get('total_predictions', 'N/A')}",
            f"• 5-Day Accuracy: {metrics.get('accuracy_5d', 0):.1%}",
            f"• 10-Day Accuracy: {metrics.get('accuracy_10d', 0):.1%}",
            f"• Average ML Probability: {metrics.get('avg_ml_prob', 0):.3f}",
            f"• High Confidence Accuracy: {metrics.get('high_conf_accuracy', 0):.1%}",
            "",
        ]
        
        # ביצועים לפי רז'ים
        if 'regime_performance' in metrics:
            report_lines.extend([
                "## 🌍 Market Regime Performance",
                "```"
            ])
            for regime, perf in metrics['regime_performance'].items():
                report_lines.append(
                    f"{regime.title():>10}: {perf['accuracy_5d']:.1%} "
                    f"({perf['count']} predictions)"
                )
            report_lines.extend(["```", ""])
        
        # ניתוח טרנדים
        if trends.get("status") == "valid":
            report_lines.extend([
                "## 📈 Trend Analysis",
                f"• **Accuracy Trend:** {trends['accuracy_trend']:+.3f} per period",
                f"• **Volatility:** {trends['volatility']:.3f}",
                f"• **Patterns Detected:** {', '.join(trends.get('patterns', ['None']))}",
                ""
            ])
        
        # המלצות
        if recommendations.get('recommendations'):
            report_lines.extend([
                "## 🎯 Calibration Recommendations",
                ""
            ])
            
            for i, rec in enumerate(recommendations['recommendations'], 1):
                report_lines.extend([
                    f"### {i}. {rec['strategy']} (Confidence: {rec['confidence']:.1%})",
                    f"*{rec['description']}*",
                    ""
                ])
                
                adj = rec['adjustments']
                if 'ml_threshold' in adj:
                    report_lines.append(f"• ML Threshold → {adj['ml_threshold']:.3f}")
                if 'weights' in adj:
                    report_lines.append("• Weight Adjustments:")
                    for weight, value in adj['weights'].items():
                        report_lines.append(f"  - {weight}: {value:.2f}")
                report_lines.append("")
        
        # המלצות ליישום
        report_lines.extend([
            "## 🚀 Implementation Recommendations",
            "",
            "### Immediate Actions:",
        ])
        
        top_choice = recommendations.get('top_choice')
        if top_choice and top_choice['confidence'] > 0.7:
            report_lines.extend([
                f"✅ **Apply {top_choice['strategy']} strategy** (High confidence)",
                "✅ Monitor results for 3-5 trading days",
                "✅ Set up automated performance tracking"
            ])
        else:
            report_lines.extend([
                "⚠️  **Conservative approach recommended** (Low confidence)",
                "⚠️  Collect more data before major changes",
                "⚠️  Consider manual review of edge cases"
            ])
        
        report_lines.extend([
            "",
            "### Long-term Actions:",
            "🔄 Implement A/B testing framework",
            "📊 Enhance feature engineering pipeline", 
            "🧪 Experiment with ensemble methods",
            "⚡ Set up real-time performance alerts"
        ])
        
        return "\n".join(report_lines)

def demo_advanced_analysis():
    """הדמיה של הניתוח המתקדם"""
    print("🔬 Advanced Calibration Analysis Demo")
    print("=" * 50)
    
    # נתונים דמיוניים למטריקות נוכחיות
    current_metrics = {
        'total_predictions': 45,
        'accuracy_5d': 0.62,
        'accuracy_10d': 0.58,
        'avg_ml_prob': 0.67,
        'high_conf_accuracy': 0.74,
        'regime_performance': {
            'bull': {'accuracy_5d': 0.78, 'count': 18},
            'bear': {'accuracy_5d': 0.41, 'count': 12},
            'sideways': {'accuracy_5d': 0.65, 'count': 15}
        }
    }
    
    # היסטוריית מטריקות (דמיונית)
    metrics_history = [
        {'accuracy_5d': 0.58, 'avg_ml_prob': 0.65},
        {'accuracy_5d': 0.55, 'avg_ml_prob': 0.68},
        {'accuracy_5d': 0.62, 'avg_ml_prob': 0.67},
        {'accuracy_5d': 0.59, 'avg_ml_prob': 0.69},
        {'accuracy_5d': 0.62, 'avg_ml_prob': 0.67}
    ]
    
    calibrator = AdvancedCalibrator()
    
    # ניתוח טרנדים
    trends = calibrator.analyze_performance_trends(metrics_history)
    print("📈 Trend Analysis:")
    print(f"  Status: {trends.get('status')}")
    if trends.get('status') == 'valid':
        print(f"  Accuracy Trend: {trends['accuracy_trend']:+.3f}")
        print(f"  Volatility: {trends['volatility']:.3f}")
        print(f"  Patterns: {trends.get('patterns', [])}")
    print()
    
    # המלצות אסטרטגיות
    recommendations = calibrator.recommend_calibration_strategy(current_metrics, trends)
    print(f"🎯 Found {len(recommendations['recommendations'])} calibration strategies")
    
    if recommendations['top_choice']:
        top = recommendations['top_choice']
        print(f"🥇 Top Recommendation: {top['strategy']} (Confidence: {top['confidence']:.1%})")
    print()
    
    # דוח מקיף
    comprehensive_report = calibrator.generate_comprehensive_report(
        current_metrics, trends, recommendations
    )
    
    print("📋 Comprehensive Report:")
    print("-" * 30)
    print(comprehensive_report)

if __name__ == "__main__":
    demo_advanced_analysis()