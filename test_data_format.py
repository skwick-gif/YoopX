#!/usr/bin/env python3
"""
בדיקת פורמט הנתונים המעובדים - כדי להבין איך המערכת הקיימת עובדת

סקריפט זה בודק:
1. איך נראים קבצי PARQUET מעובדים
2. איך המערכת הקיימת טוענת אותם
3. מה הפורמט הסופי שמגיע ל-ML
"""

import os
import pandas as pd
from data.data_paths import get_data_paths
from data.enhanced_verification import _load_processed_data_map

def main():
    """בדיקת הפיפליין הקיים"""
    
    print("🔍 בודק פורמט נתונים במערכת הקיימת...")
    
    # 1. קבלת נתיבי המערכת
    paths = get_data_paths()
    processed_dir = paths['processed']
    
    print(f"📁 תיקיית נתונים מעובדים: {processed_dir}")
    
    # 2. בדיקת מבנה התיקיה  
    parquet_dir = os.path.join(processed_dir, '_parquet')
    catalog_dir = os.path.join(processed_dir, '_catalog')
    
    print(f"📋 תיקיית PARQUET: {parquet_dir} (קיים: {os.path.exists(parquet_dir)})")
    print(f"📋 תיקיית CATALOG: {catalog_dir} (קיים: {os.path.exists(catalog_dir)})")
    
    if os.path.exists(parquet_dir):
        files = [f for f in os.listdir(parquet_dir) if f.endswith('.parquet')]
        print(f"📊 מספר קבצי PARQUET: {len(files)}")
        
        if files:
            # בדיקת קובץ דוגמה בפורמט גולמי
            sample_file = files[0]
            sample_path = os.path.join(parquet_dir, sample_file)
            ticker = sample_file[:-8]
            
            print(f"\n🔍 בודק קובץ דוגמה: {ticker}")
            
            # טעינה ישירה של PARQUET (ללא עיבוד)
            df_raw = pd.read_parquet(sample_path)
            print(f"📊 פורמט גולמי - שורות: {len(df_raw)}, עמודות: {list(df_raw.columns)}")
            print(f"🧩 דוגמת נתונים גולמיים:")
            print(df_raw.head(2).to_string())
            
            # בדיקה אם זה JSON גולמי
            if len(df_raw.columns) == 1:
                col_name = df_raw.columns[0]
                sample_value = df_raw.iloc[0, 0]
                print(f"\n🔍 עמודה יחידה '{col_name}' מכילה: {type(sample_value)}")
                if isinstance(sample_value, (dict, str)):
                    print(f"📝 תוכן: {sample_value}")
    
    # 3. בדיקת טעינה דרך המערכת הקיימת
    print(f"\n🔄 טוען דרך המערכת הקיימת (_load_processed_data_map)...")
    
    try:
        data_map = _load_processed_data_map(processed_dir)
        
        if data_map:
            print(f"✅ נטענו {len(data_map)} טיקרים")
            
            # בדיקת דוגמה מעובדה
            sample_ticker = list(data_map.keys())[0]
            sample_df = data_map[sample_ticker]
            
            print(f"\n📊 דוגמה מעובדת ({sample_ticker}):")
            print(f"   שורות: {len(sample_df)}")
            print(f"   עמודות: {list(sample_df.columns)}")
            print(f"   אינדקס: {type(sample_df.index)} ({sample_df.index.name})")
            
            # בדיקת עמודות OHLCV
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            has_ohlcv = all(col in sample_df.columns for col in required_cols)
            print(f"   עמודות OHLCV: {'✅' if has_ohlcv else '❌'}")
            
            if has_ohlcv:
                print(f"   טווח תאריכים: {sample_df.index.min()} עד {sample_df.index.max()}")
                print(f"   דוגמת נתונים:")
                print(sample_df[required_cols].head(3).to_string())
                
                # בדיקה אם יש אינדקס תאריך
                if pd.api.types.is_datetime64_any_dtype(sample_df.index):
                    print(f"   ✅ אינדקס תאריך תקין")
                else:
                    print(f"   ⚠️ אינדקס תאריך לא תקין: {type(sample_df.index)}")
            else:
                print(f"   ⚠️ חסרות עמודות OHLCV, מציג דוגמה:")
                print(sample_df.head(2).to_string())
                
        else:
            print("❌ לא נטענו נתונים")
            
    except Exception as e:
        print(f"❌ שגיאה בטעינה: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. הסבר על הפיפליין
    print(f"\n📚 סיכום הפיפליין הקיים:")
    print(f"   1. Daily Update button -> downloads raw JSON")
    print(f"   2. processing_pipeline.py -> converts JSON to PARQUET") 
    print(f"   3. enhanced_verification.py -> loads PARQUET with data transformations")
    print(f"   4. main_content.py -> uses load_parquet_folder + maybe_adjust_with_adj")
    print(f"   5. ML training -> gets clean OHLCV DataFrame with date index")


if __name__ == "__main__":
    main()