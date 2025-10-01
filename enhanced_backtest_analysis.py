#!/usr/bin/env python3
"""
🚀 שיפור הבקטסטר - אלגוריתמים נוספים וביצועים טובים יותר
===========================================================

עכשיו כשהבסיס עובד, בואו נשפר את הביצועים:
1. תמיכה ב-XGB ו-LGBM
2. השוואת ביצועים
3. שיפור הפרמטרים
"""

from working_historical_backtester import WorkingHistoricalBacktester
import pandas as pd
from datetime import datetime
import json
import os
from typing import Dict

class EnhancedHistoricalBacktester(WorkingHistoricalBacktester):
    """בקטסטר משופר עם אלגוריתמים נוספים"""
    
    def run_algorithm_comparison(self, test_date: str = "2025-06-01") -> Dict:
        """השוואה בין אלגוריתמים שונים"""
        
        self.logger.info(f"🤖 השוואת אלגוריתמים לתאריך: {test_date}")
        
        algorithms = ['rf', 'xgb', 'lgbm']
        results = {
            'config': {
                'test_date': test_date,
                'algorithms': algorithms,
                'timestamp': datetime.now().isoformat()
            },
            'algorithm_results': {},
            'comparison': {}
        }
        
        try:
            # טעינת נתונים פעם אחת
            data_map = self._load_data_map_like_main_system()
            if not data_map:
                results['error'] = "לא נטענו נתונים"
                return results
                
            from ml.train_model import filter_data_until_date
            filtered_data = filter_data_until_date(data_map, test_date)
            
            if not filtered_data:
                results['error'] = "לא נשארו נתונים אחרי סינון"
                return results
            
            # בדיקה של כל אלגוריתם
            for algorithm in algorithms:
                self.logger.info(f"🔄 בודק אלגוריתם: {algorithm.upper()}")
                
                try:
                    algo_result = self._test_single_algorithm(filtered_data, algorithm, test_date)
                    results['algorithm_results'][algorithm] = algo_result
                    
                    if algo_result['success']:
                        auc = algo_result['validation_auc']
                        self.logger.info(f"✅ {algorithm.upper()}: AUC = {auc:.4f}")
                    else:
                        self.logger.warning(f"❌ {algorithm.upper()}: {algo_result.get('error', 'כשל')}")
                        
                except Exception as e:
                    self.logger.error(f"❌ שגיאה באלגוריתם {algorithm}: {e}")
                    results['algorithm_results'][algorithm] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # ניתוח השוואתי
            successful_algos = {k: v for k, v in results['algorithm_results'].items() if v.get('success')}
            
            if successful_algos:
                # מיון לפי AUC
                sorted_algos = sorted(successful_algos.items(), 
                                    key=lambda x: x[1].get('validation_auc', 0), 
                                    reverse=True)
                
                results['comparison'] = {
                    'best_algorithm': sorted_algos[0][0],
                    'best_auc': sorted_algos[0][1]['validation_auc'],
                    'ranking': [(algo, data['validation_auc']) for algo, data in sorted_algos],
                    'auc_range': {
                        'min': min(data['validation_auc'] for _, data in sorted_algos),
                        'max': max(data['validation_auc'] for _, data in sorted_algos),
                        'avg': sum(data['validation_auc'] for _, data in sorted_algos) / len(sorted_algos)
                    }
                }
                
            results['success'] = len(successful_algos) > 0
            
        except Exception as e:
            results['error'] = str(e)
            self.logger.error(f"❌ שגיאה כללית: {e}")
        
        return results
    
    def _test_single_algorithm(self, filtered_data: Dict, algorithm: str, test_date: str) -> Dict:
        """בדיקה של אלגוריתם יחיד"""
        
        from ml.train_model import train_model
        
        temp_model_path = os.path.join(self.temp_models_dir, f"temp_{algorithm}_{test_date.replace('-', '')}.pkl")
        
        try:
            training_result = train_model(
                data_map=filtered_data,
                model=algorithm,
                model_path=temp_model_path
            )
            
            if training_result.get('error'):
                return {
                    'success': False,
                    'error': training_result['error']
                }
            
            # בדיקה שהמודל נוצר
            model_exists = os.path.exists(temp_model_path)
            
            result = {
                'success': True,
                'algorithm': algorithm,
                'validation_auc': training_result.get('validation', {}).get('auc'),
                'dataset_size': training_result.get('dataset_size'),
                'features_count': len(training_result.get('features', [])),
                'model_exists': model_exists,
                'training_time': training_result.get('training_time'),
                'model_path': temp_model_path
            }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            # ניקוי מודל זמני
            try:
                if os.path.exists(temp_model_path):
                    os.remove(temp_model_path)
            except:
                pass

def run_comprehensive_analysis():
    """ניתוח מקיף של הבקטסטר המשופר"""
    
    print("🚀 ניתוח מקיף של הבקטסטר המשופר")
    print("=" * 60)
    
    backtester = EnhancedHistoricalBacktester()
    
    # בדיקה של תאריכים שונים
    test_dates = ["2025-04-01", "2025-06-01", "2025-08-01"]
    
    all_results = []
    
    for i, test_date in enumerate(test_dates, 1):
        print(f"\n📅 בדיקה {i}/{len(test_dates)}: {test_date}")
        print("-" * 40)
        
        results = backtester.run_algorithm_comparison(test_date)
        
        if results['success']:
            comparison = results.get('comparison', {})
            best_algo = comparison.get('best_algorithm', 'N/A')
            best_auc = comparison.get('best_auc', 0)
            
            print(f"🏆 אלגוריתם הטוב ביותר: {best_algo.upper()}")
            print(f"📊 AUC הטוב ביותר: {best_auc:.4f}")
            
            # פירוט לפי אלגוריתם
            for algo, data in results.get('algorithm_results', {}).items():
                if data.get('success'):
                    auc = data.get('validation_auc', 0)
                    print(f"   {algo.upper()}: AUC = {auc:.4f}")
                else:
                    print(f"   {algo.upper()}: ❌ {data.get('error', 'כשל')}")
        else:
            print(f"❌ כשלון: {results.get('error', 'לא ידועה')}")
        
        all_results.append(results)
    
    # ניתוח כללי
    print(f"\n📊 ניתוח כללי")
    print("=" * 40)
    
    successful_comparisons = [r for r in all_results if r.get('success')]
    
    if successful_comparisons:
        # איסוף כל התוצאות לפי אלגוריתם
        algo_performance = {}
        
        for result in successful_comparisons:
            for algo, data in result.get('algorithm_results', {}).items():
                if data.get('success'):
                    if algo not in algo_performance:
                        algo_performance[algo] = []
                    algo_performance[algo].append(data.get('validation_auc', 0))
        
        print(f"📈 ביצועים ממוצעים:")
        for algo, aucs in algo_performance.items():
            avg_auc = sum(aucs) / len(aucs)
            print(f"   {algo.upper()}: {avg_auc:.4f} (מתוך {len(aucs)} בדיקות)")
        
        # האלגוריתם הטוב ביותר
        if algo_performance:
            avg_performances = {algo: sum(aucs)/len(aucs) for algo, aucs in algo_performance.items()}
            best_overall = max(avg_performances.items(), key=lambda x: x[1])
            
            print(f"\n🏆 אלגוריתם הטוב ביותר בממוצע: {best_overall[0].upper()}")
            print(f"📊 AUC ממוצע: {best_overall[1]:.4f}")
    
    # שמירת תוצאות
    results_file = f"ml/backtest_results/algorithm_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 תוצאות נשמרו: {results_file}")
    
    # המלצות
    print(f"\n🎯 המלצות:")
    print("-" * 20)
    
    if successful_comparisons:
        print("✅ הבקטסטר עובד עם מספר אלגוריתמים")
        print("📊 המערכת מוכנה לבדיקות מתקדמות")
        print("🔄 שלב הבא: אופטימיזציה של היפר-פרמטרים")
    else:
        print("⚠️ נדרש debugging נוסף")
    
    return all_results

if __name__ == "__main__":
    results = run_comprehensive_analysis()