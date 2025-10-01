# 🎯 תכנית מפורטת - Historical Multi-Horizon Training System

## 📋 סקירת המצב הנוכחי

### מה יש לנו כבר במערכת:
- ✅ `ml/train_model.py` - מערכת אימון מלאה עם RF/XGB/LGBM
- ✅ `ml/feature_engineering.py` - בניית פיצ'רים 
- ✅ `data/` - מערכת נתונים מלאה
- ✅ `ui/worker_thread.py` - מנגנון סריקה
- ✅ `backend.py` - לוגיקת סריקה

### מה חסר לנו:
- ❌ Multi-horizon training (1D, 5D, 10D במקביל)
- ❌ Historical data filtering (נתונים עד תאריך מסוים)
- ❌ Historical scanning simulation
- ❌ Prediction validation & outcome tracking
- ❌ Performance analysis & improvement loop
- ❌ UI controls למערכת החדשה

## 🛠️ תכנית המימוש - שלב אחר שלב

### **Phase 1: Core Infrastructure (שבוע 1)**

#### 1.1 Multi-Horizon Model Training
```python
# קבצים לעריכה/יצירה:
- ml/train_model.py → הוספת תמיכה בהוריזונים מרובים
- ml/multi_horizon_trainer.py → מנהל אימון רב-אופקי חדש

# פונקציונליות:
def train_for_date_and_horizons(cutoff_date: str, horizons: List[int]):
    """אימון 3 מודלים נפרדים לאותו תאריך"""
    # 1. סינון נתונים עד cutoff_date
    # 2. בניית labels שונים לכל horizon (1D/5D/10D)
    # 3. אימון מודל נפרד לכל אופק
    # 4. שמירה עם שמות ייחודיים: model_1d_20240801.pkl
```

#### 1.2 Historical Data Management
```python
# קבצים לעריכה:
- data/data_utils.py → הוספת פונקציות סינון זמן

# פונקציונליות:
def load_data_until_date(symbol: str, cutoff_date: str) -> pd.DataFrame:
    """טעינת נתונים עד תאריך מסוים בלבד"""
    
def get_available_symbols_for_date(date: str) -> List[str]:
    """רשימת מניות שיש עליהן נתונים באותו תאריך"""
```

#### 1.3 Historical Scanning Engine
```python
# קבצים לעריכה:
- ui/worker_thread.py → התאמה לסריקה היסטורית
- ml/historical_scanner.py → מנוע סריקה היסטורית חדש

# פונקציונליות:
def run_scan_for_historical_date(scan_date: str, models_paths: Dict[int, str]):
    """סריקה כאילו אנחנו באותו יום בעבר"""
    # 1. טעינת נתונים עד התאריך בלבד
    # 2. טעינת המודלים המתאימים
    # 3. הרצת סריקה רגילה
    # 4. שמירת תוצאות עם תאריך
```

### **Phase 2: Validation & Analysis (שבוע 2)**

#### 2.1 Prediction Outcome Tracking
```python
# קבצים חדשים:
- ml/outcome_validator.py → מערכת מעקב תוצאות

# פונקציונליות:
def validate_scan_results(scan_results: List[Dict], validation_date: str):
    """בדיקת מה קרה באמת אחרי הסריקה"""
    # 1. לכל תוצאה מהסריקה
    # 2. בדוק מחיר אחרי 1/5/10 ימים
    # 3. קבע האם זה "הצלחה" (1%+ רווח)
    # 4. שמור התוצאות
```

#### 2.2 Performance Analysis Engine
```python
# קבצים חדשים:
- ml/performance_analyzer.py → ניתוח ביצועים

# פונקציונליות:
def analyze_model_performance(validated_results: List[Dict]):
    """ניתוח מפורט של ביצועי המודלים"""
    # 1. דיוק לכל אופק זמן
    # 2. ביצועים לפי רמת הסתברות
    # 3. השוואה בין מודלים
    # 4. הצעות שיפור
```

### **Phase 3: Automation & UI (שבוע 3)**

#### 3.1 Rolling Backtest Controller
```python
# קבצים חדשים:
- ml/backtest_controller.py → בקר הרצה אוטומטית

# פונקציונליות:
def run_rolling_backtest(start_date: str, end_date: str, step_days: int):
    """הרצה אוטומטית על תקופה שלמה"""
    # לולאה: אימון → סריקה → המתנה → ולידציה → ניתוח
```

#### 3.2 UI Integration
```python
# קבצים לעריכה:
- ui/tabs/ → טאב חדש לHistorical Backtest
- main_content.py → הוספת הטאב החדש

# ממשק:
┌─────────────────────────────────────┐
│  🕰️ Historical Backtest Manager     │
├─────────────────────────────────────┤
│ Start Date: [2024-08-01] 📅         │
│ End Date:   [2024-09-01] 📅         │  
│ Step Size:  [7 days] ⏭️             │
│ Models: ☑️ RF ☑️ XGB ☑️ LGBM        │
│ Horizons: ☑️ 1D ☑️ 5D ☑️ 10D        │
│                                     │
│ [🚀 START BACKTEST] [⏹️ STOP]       │
│                                     │
│ Progress: ████████░░ 80%            │
│ Current: 2024-08-25                 │
│ Status: Validating predictions...   │
└─────────────────────────────────────┘
```

### **Phase 4: Advanced Features (שבוע 4)**

#### 4.1 Auto-Improvement Engine
```python
# קבצים חדשים:
- ml/auto_tuner.py → כיוונון אוטומטי

# פונקציונליות:
def auto_tune_based_on_results(performance_history: List[Dict]):
    """שיפור פרמטרים בהתבסס על ביצועים"""
    # 1. זיהוי דפוסים בביצועים
    # 2. הצעת התאמות פרמטרים
    # 3. A/B testing אוטומטי
```

#### 4.2 Results Visualization
```python
# קבצים חדשים:
- ui/backtest_dashboard.py → דשבורד תוצאות

# תצוגות:
- גרפים של שיפור לאורך זמן
- השוואת מודלים
- מטריקות מפורטות
- המלצות פעולה
```

## 📁 מבנה קבצים מוצע

```
ml/
├── historical_training/
│   ├── __init__.py
│   ├── multi_horizon_trainer.py      # אימון רב-אופקי
│   ├── historical_scanner.py         # סריקה היסטורית  
│   ├── outcome_validator.py          # מעקב תוצאות
│   ├── performance_analyzer.py       # ניתוח ביצועים
│   ├── backtest_controller.py        # בקרה אוטומטית
│   └── auto_tuner.py                 # כיוונון אוטומטי
│
├── models/
│   ├── historical/                   # מודלים היסטוריים
│   │   ├── 20240801/
│   │   │   ├── model_1d_rf.pkl
│   │   │   ├── model_5d_rf.pkl
│   │   │   └── model_10d_rf.pkl
│   │   └── 20240808/
│   │       └── ...
│   └── current/                      # מודלים נוכחיים
│
└── backtest_results/
    ├── 20240801_20240901.json       # תוצאות backtest
    ├── performance_timeline.json    # ביצועים לאורך זמן
    └── auto_improvements.json       # שיפורים אוטומטיים

ui/tabs/
├── historical_backtest_tab.py       # טאב בקרה
└── backtest_dashboard_tab.py        # טאב תוצאות

config/
└── backtest_settings.json          # הגדרות מערכת
```

## 🔄 תהליך העבודה המדויק

### שלב 1: הגדרה
```python
# משתמש בוחר:
start_date = "2024-08-01"  
end_date = "2024-09-01"
step_days = 7
horizons = [1, 5, 10]
models = ["RF", "XGB", "LGBM"]
```

### שלב 2: לולאה אוטומטית
```python
for current_date in date_range(start_date, end_date, step_days):
    # 1. אמן 9 מודלים (3 אלגוריתמים × 3 אופקים) לתאריך current_date
    # 2. הרץ סריקה היסטורית באותו תאריך
    # 3. שמור תוצאות סריקה
    # 4. המתן 10-14 ימים (בדמיון - קפץ קדימה בזמן)
    # 5. בדוק מה קרה באמת עם המניות
    # 6. חשב דיוק לכל מודל
    # 7. שמור תוצאות ניתוח
    # 8. התאם פרמטרים לאיטרציה הבאה
```

### שלב 3: ניתוח סופי
```python
# אחרי שכל הלולאה הסתיימה:
# 1. צור דוח מקיף של שיפור לאורך זמן
# 2. זהה איזה מודל/אופק עובד הכי טוב
# 3. המלץ על פרמטרים אופטימליים לייצור
# 4. צור תצוגות גרפיות
```

## 🎯 נקודות קריטיות למימוש

### 1. **שילוב עם מערכת הקיימת**
- ✅ שימוש ב-`ml/train_model.py` הקיים (לא להמציא מחדש)
- ✅ שימוש ב-`data/data_utils.py` לטעינת נתונים
- ✅ שימוש ב-`ui/worker_thread.py` לסריקה (עם התאמות)

### 2. **ניהול זיכרון ומהירות**
- 🚀 טעינת נתונים חכמה (cache)  
- 🚀 אימון מקבילי של מודלים
- 🚀 שמירה מתמשכת של תוצאות ביניים

### 3. **Error Handling & Resume**
- 🛡️ יכולת המשכה אחרי תקלה
- 🛡️ validation של נתונים
- 🛡️ בדיקות תקינות לפני התחלה

### 4. **תאימות לסביבה הקיימת**
- 🔧 אותה מבנה נתונים
- 🔧 אותם פורמטים של מודלים  
- 🔧 אותה סביבת Python והפקגים

## ❓ שאלות לאישור

1. **האם התכנית הזו מתאימה לחזון שלך?**
2. **איזה שלב תרצה להתחיל בו? (אני ממליץ על Phase 1.1)**
3. **האם יש נתונים היסטוריים מספיקים לתקופה שתרצה לבדוק?**
4. **האם אתה מעוניין בממשק UI מלא או להתחיל עם command line?**
5. **איזו תקופה בדיוק תרצה לבדוק? (חודש? שלושה חודשים?)**

**רק אחרי שתאשר הכל - נתחיל לכתוב קוד אמיתי! 🚀**