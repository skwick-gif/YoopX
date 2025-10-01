#!/usr/bin/env python3
"""
🧪 בדיקת המערכת הטיטרטיבית החדשה
"""

import sys
sys.path.append('.')

def test_iterative_system():
    print("🔄 Testing Iterative Training System")
    print("=" * 50)
    
    # ייבוא המערכת החדשה
    from ml.iterative_training_system import IterativeHistoricalTrainer, IterativeTrainingConfig
    from data.data_utils import load_json
    import os
    
    # טעינת נתונים
    print("📊 Loading sample data...")
    data_map = {}
    data_folder = 'data backup'
    sample_files = [f for f in os.listdir(data_folder) if f.endswith('.json')][:5]
    
    for f in sample_files:
        try:
            df = load_json(os.path.join(data_folder, f))
            symbol = f.replace('.json', '')
            data_map[symbol] = df
            print(f"  ✅ {symbol}: {len(df)} rows")
        except Exception as e:
            print(f"  ❌ {f}: {e}")
    
    if not data_map:
        print("❌ No data loaded")
        return False
    
    # יצירת תצורה לבדיקה
    config = IterativeTrainingConfig(
        initial_lookback_days=60,  # התחל עם 60 ימי מסחר
        horizons=[5, 10],  # רק 2 horizons לבדיקה
        max_iterations=3,  # מקסימום 3 איטרציות
        min_accuracy_improvement=0.01,
        target_accuracy=0.65  # יעד נמוך יותר לבדיקה
    )
    
    print(f"📋 Configuration:")
    print(f"  Initial lookback: {config.initial_lookback_days} days")
    print(f"  Horizons: {config.horizons}")
    print(f"  Max iterations: {config.max_iterations}")
    print(f"  Target accuracy: {config.target_accuracy}")
    
    # יצירת המערכת
    trainer = IterativeHistoricalTrainer(data_map)
    
    # בדיקת חישוב תאריכים
    print("\n📅 Testing date calculations...")
    latest_date = trainer._find_latest_date()
    print(f"Latest date: {latest_date}")
    
    if latest_date:
        training_cutoff, validation_start, validation_end = trainer._calculate_dates(
            latest_date, config.initial_lookback_days
        )
        print(f"Training cutoff: {training_cutoff}")
        print(f"Validation period: {validation_start} → {validation_end}")
    
    # בדיקת אימון מודלים (רק שלב אחד)
    print("\n🧠 Testing model training...")
    try:
        models = trainer._train_models_for_iteration(training_cutoff, [5], 1)  # רק horizon 5
        if models:
            print(f"✅ Models trained: {list(models.keys())}")
            for horizon, path in models.items():
                exists = os.path.exists(path) if path else False
                print(f"  {horizon}D: {path} (exists: {exists})")
        else:
            print("❌ No models trained")
    except Exception as e:
        print(f"❌ Model training failed: {e}")
        import traceback
        traceback.print_exc()
    
    return True

if __name__ == "__main__":
    test_iterative_system()