#!/usr/bin/env python3
"""
בדיקת אימון מודל ML בסיסי
"""

import sys
sys.path.append('.')
from ml.train_model import train_model, collect_training_data
from data.data_utils import load_json
import os

def test_ml_training():
    print('🧠 Testing ML model training...')
    
    # טען 10 קבצים לדוגמה
    data_map = {}
    data_folder = 'data backup'
    sample_files = [f for f in os.listdir(data_folder) if f.endswith('.json')][:10]
    
    for f in sample_files:
        try:
            df = load_json(os.path.join(data_folder, f))
            symbol = f.replace('.json', '')
            data_map[symbol] = df
        except Exception as e:
            print(f'❌ {f}: {e}')
    
    print(f'✅ Loaded {len(data_map)} symbols')
    
    # נסיון אימון מודל
    try:
        result = train_model(data_map, model='rf', model_path='test_model.pkl')
        print(f'🎯 Training result: {type(result)}')
        if isinstance(result, dict):
            print(f'   - Error: {result.get("error")}')
            print(f'   - Samples: {result.get("samples")}')
            print(f'   - Symbols: {result.get("symbols")}')
            validation = result.get("validation", {})
            if validation:
                print(f'   - Validation AUC: {validation.get("auc")}')
        return result
    except Exception as e:
        print(f'❌ Training failed: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_ml_training()