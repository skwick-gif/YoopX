# תיעוד מפורט: פיפליין נתונים - Daily Update Pipeline

## סקירה כללית

מערכת Daily Update היא הליבה של זרימת הנתונים במערכת. היא אחראית להורדה, עיבוד ווידוא איכות של נתוני מניות בזמן אמת.

## 🔄 זרימת הפיפליין המלאה

```
[לחיצה על Daily Update] 
          ↓
[תכנון עדכונים - Planning Phase]
          ↓  
[הורדת נתונים גולמיים - Raw Data Fetching]
          ↓
[עיבוד ל-Parquet - Processing Pipeline]
          ↓
[אימות נתונים - Data Verification]
          ↓
[עדכון מטא-דאטה - Metadata Update]
```

---

## 📊 Phase 1: תכנון העדכונים (Planning)

**קובץ:** `data/daily_update_new.py` → `plan_daily_update_new()`

### מה קורה:
1. **סריקת נתונים קיימים** - בודק מה כבר קיים ב-`raw_data/`
2. **זיהוי פערים** - מוצא אילו תאריכים חסרים לכל טיקר
3. **תכנון אופטימלי** - מחשב כמה ימים להוריד לכל טיקר
4. **אסטרטגית API** - בוחר מקורות נתונים (Yahoo, AlphaVantage)

### פלט:
```python
plan_dict = {
    "summary": {
        "total_tickers": 850,
        "needs_update": 245,
        "new_tickers": 12,
        "total_days_to_fetch": 1850
    },
    "tickers": {
        "AAPL": {"missing_days": 5, "strategy": "yahoo"},
        "GOOGL": {"missing_days": 3, "strategy": "alphavantage"}
    }
}
```

---

## 📥 Phase 2: הורדת נתונים גולמיים (Raw Data Fetching)

**קובץ:** `data/daily_update_new.py` → `execute_daily_update_plan()`

### מה קורה:
1. **הורדה מ-APIs** - Yahoo Finance, AlphaVantage, וכו'
2. **ניהול Rate Limiting** - עיכובים אוטומטיים בין בקשות
3. **טיפול בשגיאות** - חידוש נסיונות, מעבר בין APIs
4. **שמירה גולמית** - JSON files ב-`raw_data/`

### מבנה קובץ גולמי:
```
raw_data/
├── AAPL.json    # נתונים גולמיים מ-API
├── GOOGL.json   # כולל מטא-דאטה, מחירים, דיבידנדים
└── MSFT.json    # פורמט JSON מקורי
```

### תוכן קובץ JSON גולמי:
```json
{
    "ticker": "AAPL",
    "collected_at": "2025-09-30T12:00:00Z",
    "price": {
        "source": "yahoo",
        "yahoo": {
            "daily": [
                {
                    "date": "2025-09-30",
                    "open": 150.25,
                    "high": 152.10,
                    "low": 149.80,
                    "close": 151.45,
                    "adj_close": 151.45,
                    "volume": 45123400
                }
            ]
        }
    },
    "corporate_actions": {...},
    "fundamentals": {...}
}
```

---

## 🔧 Phase 3: עיבוד ל-Parquet (Processing Pipeline)

**קובץ:** `data/processing_pipeline.py` → `process_raw_to_parquet()`

### מה קורה:
1. **טעינת JSON גולמי** - קריאה מ-`raw_data/`
2. **חילוץ נתונים** - מפריד בין מחירים, פונדמנטלים, אירועים
3. **נרמול פורמט** - מאחד פורמטים שונים מ-APIs שונים
4. **שמירה מובנית** - PARQUET files ב-`processed_data/`

### מבנה תיקיית עיבוד:
```
processed_data/
├── _parquet/
│   ├── AAPL.parquet     # נתונים מעובדים
│   ├── GOOGL.parquet    # פורמט מאוחד
│   └── MSFT.parquet     # מטא-דאטה + מחירים
├── _catalog/
│   ├── catalog.parquet  # אינדקס של כל הקבצים
│   └── catalog.json     # גיבוי באינדקס JSON
└── verification_reports/
    └── report_20250930.json
```

### תוכן קובץ PARQUET מעובד:
הקובץ מכיל **44 עמודות** עם כל המידע:
- `ticker` - סמל המניה
- `collected_at` - זמן איסוף הנתונים
- `price.yahoo.daily` - **רשימת נתוני OHLCV** (numpy array)
- `fundamentals.yahoo.overview.*` - נתוני יסוד
- `corporate_actions.*` - דיבידנדים ופיצולים
- `additional_data.*` - נתונים נוספים

**העמודה הקריטית:** `price.yahoo.daily` מכילה numpy array של dictionaries:
```python
[
    {"date": "2025-09-30", "open": 150.25, "high": 152.10, ...},
    {"date": "2025-09-29", "open": 149.80, "high": 151.00, ...},
    ...
]
```

---

## ✅ Phase 4: אימות נתונים (Data Verification)

**קובץ:** `data/enhanced_verification.py` → `verify_processed_data_structure()`

### מה קורה:
1. **בדיקת תקינות** - מוודא שכל קובץ PARQUET תקין
2. **תאימות מודולים** - בודק שהנתונים מתאימים ל-ML/Backtest/Scanner
3. **זיהוי בעיות** - מוצא נתונים חסרים או פגומים
4. **דו"ח איכות** - יוצר סיכום מפורט

### פלט אימות:
```python
verification_report = {
    "summary": {
        "total_tickers": 850,
        "verified_tickers": 845,
        "failed_tickers": 3,
        "warning_tickers": 2
    },
    "data_compatibility": {
        "ml_training": "✅ Compatible",
        "backtesting": "✅ Compatible", 
        "scanning": "✅ Compatible",
        "optimization": "✅ Compatible"
    }
}
```

---

## 🎯 Phase 5: עדכון מטא-דאטה (Metadata Update)

### קטלוג מרכזי:
הקובץ `_catalog/catalog.parquet` מכיל אינדקס של כל הנתונים:

```python
catalog_df = pd.DataFrame([
    {
        "ticker": "AAPL",
        "parquet_path": "/path/to/processed_data/_parquet/AAPL.parquet",
        "src_path": "/path/to/raw_data/AAPL.json", 
        "min_date": "2020-01-01",
        "max_date": "2025-09-30",
        "total_records": 1450,
        "last_updated": "2025-09-30T12:00:00Z"
    }
])
```

---

## 🔌 ממשק המשתמש (UI Integration)

**קובץ:** `main_content.py` → `_on_daily_update_clicked()`

### רכיבי UI:
1. **כפתור Daily Update** - מפעיל את הפיפליין
2. **Progress Bar** - מציג התקדמות 0-100%
3. **Status Label** - הודעות בזמן אמת
4. **Stop Button** - עצירה במהלך ההרצה

### Worker Thread Architecture:
```python
# תהליך רקע בטוח
QThread → DailyUpdateWorkerNew → Signals:
├── progress(int) → Progress Bar
├── status(str) → Status Label  
├── ticker_done(str, bool, meta) → Per-ticker updates
├── finished(dict) → Final summary
└── error(str) → Error handling
```

---

## 📊 איך המערכת הקיימת משתמשת בנתונים

### טעינה למערכת ML:
**קובץ:** `ml/historical_backtester_fixed.py`

```python
# 1. טעינת נתונים גולמיים
raw_data = _load_processed_data_map(processed_dir)

# 2. בדיקה אם צריך עיבוד
if _is_clean_ohlcv_data(df):
    # כבר נקי - רק התאמות
    final_df = maybe_adjust_with_adj(df)
else:
    # נתונים גולמיים - עיבוד מלא
    final_df = _process_raw_to_ohlcv(df)

# 3. חילוץ מעמודת המחירים
price_data = df['price.yahoo.daily'].iloc[0].tolist()
clean_df = pd.DataFrame(price_data)
clean_df = _standardize_columns(clean_df)
clean_df = _ensure_datetime_index(clean_df)
```

### התוצאה הסופית:
```python
# DataFrame נקי עם:
clean_df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
clean_df.index = DatetimeIndex(['2024-01-01', '2024-01-02', ...])
```

---

## ⚠️ נקודות קריטיות לתחזוקה

### 1. **פורמט הנתונים המעובדים**
- קבצי PARQUET **אינם** מכילים DataFrame נקי
- הם מכילים **JSON גולמי** עם 44 עמודות מטא-דאטה
- העמודה `price.yahoo.daily` מכילה את נתוני OHLCV בפורמט numpy array

### 2. **תהליך ההמרה**
- כל מודול שצורך נתונים **חייב** לעבד את `price.yahoo.daily`
- השימוש ב-`_standardize_columns()` ו-`_ensure_datetime_index()` הכרחי
- `maybe_adjust_with_adj()` מתאים Close ל-Adj Close

### 3. **תאימות לאחור**
- המערכת תומכת בקבצים ישנים (JSON/CSV) וחדשים (PARQUET)
- פונקציית `load_json()` ב-`data_utils.py` מטפלת בפורמטים שונים
- Catalog מספק אינדקס מאוחד לכל סוגי הקבצים

---

## 🔧 בדיקת תקינות כפתור Daily Update

### סטטוס נוכחי: ✅ **תקין לגמרי**

**לא שיניתי שום דבר בלוגיקה של כפתור Daily Update!**

### הכפתור פועל כך:
1. **הפעלה** - `_on_daily_update_clicked()` ב-`main_content.py`
2. **Worker Thread** - יוצר `DailyUpdateWorkerNew` ברקע
3. **תהליך מלא** - מתכנן → מוריד → מעבד → מאמת
4. **עדכוני UI** - Progress bar, Status messages, Stop button
5. **ניקוי** - משחרר Thread וכפתור Stop בסיום

### מה ש**כן** שיניתי:
- **הבנתי את הפיפליין** וכיתבתי `historical_backtester_fixed.py` שעובד איתו
- **יצרתי פונקציות עיבוד** שיודעות לחלץ נכון מ-`price.yahoo.daily`
- **הבנתי שקבצי PARQUET** מכילים JSON גולמי ולא DataFrame נקי

### הכפתור עובד בדיוק כמו שתוכנן:
✅ מוריד נתונים גולמיים ל-`raw_data/`  
✅ מעבד אותם ל-PARQUET ב-`processed_data/`  
✅ יוצר קטלוג מאוחד  
✅ מאמת תאימות למודולים  
✅ מעדכן UI עם התקדמות  

---

## 🎯 המלצות לפיתוח עתידי

### 1. **תיעוד קוד**
```python
# הוסף תיעוד לפונקציות קריטיות
def _process_raw_to_ohlcv(self, raw_df: pd.DataFrame, ticker: str):
    """
    מעבד נתונים גולמיים מפורמט PARQUET לDataFrame OHLCV נקי.
    
    הפונקציה מחלצת נתוני מחיר מהעמודה 'price.yahoo.daily' 
    וממירה לפורמט תקני עם אינדקס תאריכים.
    """
```

### 2. **בדיקות אוטומטיות**
```python
# יצור בדיקות לוודא שהפיפליין עובד
def test_daily_update_pipeline():
    """בודק שהפיפליין המלא עובד נכון"""
    assert raw_data_exists()
    assert parquet_processed_correctly() 
    assert catalog_updated()
    assert verification_passed()
```

### 3. **מעקב ביצועים**
- זמני הורדה ועיבוד
- שיעור הצלחה של APIs
- גודל קבצים ותפוסת דיסק

### 4. **גיבויים אוטומטיים**
- גיבוי יומי של `processed_data/`
- ארכיון נתונים גולמיים
- שחזור במקרה של כשל

---

## 📞 פתרון בעיות נפוצות

### בעיה: "No date info found" 
**פתרון:** הנתונים ב-PARQUET צריכים עיבוד דרך `_process_raw_to_ohlcv()`

### בעיה: "Empty DataFrame"
**פתרון:** בדוק שהעמודה `price.yahoo.daily` קיימת וחוקית

### בעיה: "API Rate Limit"  
**פתרון:** המערכת מטפלת אוטומטית - חכה או הפעל שוב מאוחר יותר

### בעיה: "Verification Failed"
**פתרון:** בדוק דו"ח האימות ב-`processed_data/verification_reports/`

---

**תאריך עדכון:** 30 בספטמבר 2025  
**גרסה:** 2.0 - Pipeline Documentation  
**מחבר:** AI Assistant (בהתבסס על ניתוח מעמיק של הקוד)