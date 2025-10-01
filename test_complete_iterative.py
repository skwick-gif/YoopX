#!/usr/bin/env python3
"""
🎯 בדיקה מלאה של המערכת הטיטרטיבית המושלמת
"""

import sys
sys.path.append('.')
import logging

def test_complete_iterative_system():
    print("🎯 Testing COMPLETE Iterative Training System")
    print("=" * 60)
    
    # הגדרת logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    # ייבוא המערכת
    from ml.iterative_training_system import IterativeHistoricalTrainer, IterativeTrainingConfig
    from data.data_utils import load_json
    import os
    
    # טעינת נתונים
    print("📊 Loading sample data...")
    data_map = {}
    data_folder = 'data backup'
    # נקח רק 3 מניות לבדיקה מהירה
    sample_files = [f for f in os.listdir(data_folder) if f.endswith('.json')][:3]
    
    for f in sample_files:
        try:
            df = load_json(os.path.join(data_folder, f))
            symbol = f.replace('.json', '')
            data_map[symbol] = df
            print(f"  ✅ {symbol}: {len(df)} rows ({df.index.min()} → {df.index.max()})")
        except Exception as e:
            print(f"  ❌ {f}: {e}")
    
    if not data_map:
        print("❌ No data loaded")
        return False
    
    # תצורה לבדיקה מהירה
    config = IterativeTrainingConfig(
        initial_lookback_days=90,  # התחל עם 90 ימי מסחר (כ-4 חודשים)
        horizons=[5],  # רק horizon אחד לבדיקה מהירה
        max_iterations=2,  # רק 2 איטרציות לבדיקה
        min_accuracy_improvement=0.005,  # 0.5% שיפור מינימלי
        target_accuracy=0.60  # יעד נמוך לבדיקה
    )
    
    print(f"\n📋 Configuration:")
    print(f"  Initial lookback: {config.initial_lookback_days} trading days")
    print(f"  Horizons: {config.horizons}")
    print(f"  Max iterations: {config.max_iterations}")
    print(f"  Target accuracy: {config.target_accuracy}")
    print(f"  Min improvement: {config.min_accuracy_improvement}")
    
    # יצירת המערכת
    trainer = IterativeHistoricalTrainer(data_map)
    
    print(f"\n🚀 Starting iterative training process...")
    print("=" * 60)
    
    try:
        # הרצת התהליך הטיטרטיבי המלא!
        results = trainer.run_iterative_training(config)
        
        print("\n" + "=" * 60)
        print("🎉 ITERATIVE TRAINING COMPLETED!")
        print("=" * 60)
        
        if results:
            print(f"📊 Summary: {len(results)} iterations completed")
            
            for i, result in enumerate(results, 1):
                print(f"\n📈 Iteration #{i}:")
                print(f"  📅 Training cutoff: {result.training_cutoff_date}")
                print(f"  📅 Validation: {result.validation_start_date} → {result.validation_end_date}")
                print(f"  🧠 Models trained: {list(result.models_trained.keys())}")
                print(f"  🔮 Predictions made: {len(result.predictions)}")
                print(f"  📊 Results collected: {len(result.actual_results)}")
                
                # הצגת דיוק לכל horizon
                for horizon, accuracy in result.accuracy_by_horizon.items():
                    print(f"  📊 {horizon}D Accuracy: {accuracy:.3f} ({accuracy*100:.1f}%)")
                
                if result.improvement_from_previous is not None:
                    direction = "📈" if result.improvement_from_previous > 0 else "📉"
                    print(f"  {direction} Improvement: {result.improvement_from_previous:.3f}")
            
            # הצגת המגמה
            accuracies = []
            for result in results:
                avg_acc = sum(result.accuracy_by_horizon.values()) / len(result.accuracy_by_horizon)
                accuracies.append(avg_acc)
            
            print(f"\n📈 Accuracy Trend:")
            for i, acc in enumerate(accuracies, 1):
                print(f"  Iteration {i}: {acc:.3f} ({acc*100:.1f}%)")
            
            if len(accuracies) > 1:
                total_improvement = accuracies[-1] - accuracies[0]
                print(f"  Total improvement: {total_improvement:.3f} ({total_improvement*100:.1f}%)")
        
        else:
            print("❌ No results returned")
            
        return True
        
    except Exception as e:
        print(f"❌ Iterative training failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_iterative_system()
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'}")