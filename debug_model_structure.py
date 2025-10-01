#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
בדיקת מבנה המודל
"""

import os
import joblib

def check_model_structure():
    model_path = "ml/models/historical/20250509/model_rf_5d.pkl"
    
    if not os.path.exists(model_path):
        print(f"❌ קובץ מודל לא קיים: {model_path}")
        return
        
    try:
        obj = joblib.load(model_path)
        print(f"📦 טוען מודל מ: {model_path}")
        print(f"🔍 סוג האובייקט: {type(obj)}")
        
        if isinstance(obj, dict):
            print("📋 מפתחות במילון:")
            for key, value in obj.items():
                print(f"  - {key}: {type(value)}")
                if hasattr(value, 'predict'):
                    print(f"    ✅ יש predict method")
                if hasattr(value, 'predict_proba'):
                    print(f"    ✅ יש predict_proba method")
        else:
            print(f"📊 האובייקט אינו מילון")
            if hasattr(obj, 'predict'):
                print(f"  ✅ יש predict method")
            if hasattr(obj, 'predict_proba'):
                print(f"  ✅ יש predict_proba method")
                
    except Exception as e:
        print(f"❌ שגיאה בטעינת המודל: {e}")

if __name__ == "__main__":
    check_model_structure()