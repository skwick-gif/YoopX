# 🎯 Multi-Horizon Historical Backtesting System - Final Specification

## 📋 סיכום הרעיון המדויק

### **התהליך המבוקש:**
1. **קלט:** משתמש מזין טווח ימים (למשל 30 ימים)
2. **חישוב תאריך התחלה:** היום - 30 ימים = תאריך התחלה של הלמידה  
3. **אימון מודלים:** לכל אלגוריתם (RF/XGB/LGBM) ולכל אופק (1D/5D/10D) = 9 מודלים
4. **לולאת סריקה ובדיקה:** מהתאריך התחלה עד היום, כל יום:
   - הרץ סריקה עם המודלים
   - המתן לפי האופק (1/5/10 ימים)
   - בדוק תוצאות אמיתיות
   - שמור דיוק לכל מודל

### **דוגמה מספרית (30 ימים):**
```
היום: 30/09/2025
טווח: 30 ימים
תאריך התחלה: 31/08/2025

איטרציות צפויות:
• Horizon 1D: 30 איטרציות (כל יום)
• Horizon 5D: 6 איטרציות (כל 5 ימים) 
• Horizon 10D: 3 איטרציות (כל 10 ימים)

סה"כ: 39 איטרציות × 3 מודלים = 117 בדיקות ביצועים
```

## 🔄 השפעה על המערכת הקיימת

### ✅ **לא ישפיע על:**
- **UI הקיים** - הטאבים והפונקציות הנוכחות יישארו זהים
- **סריקה רגילה** - הסריקה הנוכחית תמשיך לעבוד בדיוק כמו עכשיו
- **מודלים נוכחיים** - המודלים הקיימים לא יושפעו
- **נתונים** - לא נשנה או נמחק כלום מהנתונים הקיימים

### 🆕 **מה שנוסיף:**
- **טאב חדש**: "Historical Backtest" בממשק
- **מודלים היסטוריים**: נשמרים בתיקייה נפרדת `ml/models/historical/`
- **תוצאות backtest**: נשמרות ב-`ml/backtest_results/`
- **פונקציות עזר חדשות**: במודולי ML קיימים

## 🏗️ מבנה המערכת המדויק

### **Phase 1: Core Training System**

#### 1.1 Enhanced Training Function
```python
# ml/train_model.py - הוספות לקובץ הקיים

def train_multi_horizon_model(cutoff_date: str, horizon_days: int, algorithm: str = 'RF'):
    """
    אימון מודל עד תאריך מסוים עם אופק זמן ספציפי
    
    Args:
        cutoff_date: תאריך גבול לנתונים (YYYY-MM-DD)
        horizon_days: אופק החזאי (1, 5, או 10 ימים)
        algorithm: RF/XGB/LGBM
    
    Returns:
        נתיב למודל שנשמר
    """
    # 1. טעינת נתונים עד cutoff_date בלבד
    # 2. בניית labels לפי horizon_days
    # 3. אימון עם האלגוריתם המבוקש  
    # 4. שמירה: ml/models/historical/{cutoff_date}/model_{algorithm}_{horizon}d.pkl

def build_labels_for_horizon(df: pd.DataFrame, horizon_days: int) -> pd.Series:
    """
    בניית labels לאופק זמן ספציפי
    
    Logic:
    - לכל שורה, בדוק מחיר אחרי horizon_days ימי עסקים
    - אם המחיר עלה ב-1%+ → label=1, אחרת label=0
    """
```

#### 1.2 Historical Data Manager
```python
# data/data_utils.py - הוספות לקובץ הקיים

def load_data_until_date(symbol: str, cutoff_date: str) -> pd.DataFrame:
    """
    טעינת נתונים עד תאריך מסוים בלבד
    """
    # טען נתונים רגילים ואז סנן עד cutoff_date

def get_business_day_offset(start_date: str, offset_days: int) -> str:
    """
    חישוב תאריך + offset ימי עסקים
    """
```

### **Phase 2: Historical Scanning Engine**

#### 2.1 Scan Controller
```python
# ml/historical_backtest.py - קובץ חדש

class HistoricalBacktestController:
    def __init__(self, range_days: int):
        self.range_days = range_days
        self.start_date = self._calculate_start_date()
        self.models_trained = {}
        
    def run_full_backtest(self):
        """הרצה מלאה של התהליך"""
        # שלב 1: אימון כל המודלים
        self.train_all_models()
        
        # שלב 2: לולאת סריקות ובדיקות
        results = {}
        for horizon in [1, 5, 10]:
            results[horizon] = self.run_horizon_loop(horizon)
            
        return results
    
    def train_all_models(self):
        """אימון 9 מודלים (3 אלגוריתמים × 3 אופקים)"""
        for algorithm in ['RF', 'XGB', 'LGBM']:
            for horizon in [1, 5, 10]:
                model_path = train_multi_horizon_model(
                    self.start_date, horizon, algorithm
                )
                self.models_trained[(algorithm, horizon)] = model_path
    
    def run_horizon_loop(self, horizon: int):
        """לולאה לאופק ספציפי"""
        results = []
        current_date = datetime.strptime(self.start_date, '%Y-%m-%d')
        
        while current_date <= datetime.now() - timedelta(days=horizon):
            # הרץ סריקה לתאריך הזה
            scan_results = self.run_historical_scan(current_date, horizon)
            
            # בדוק תוצאות אחרי horizon ימים
            validation_date = current_date + timedelta(days=horizon)
            validated = self.validate_results(scan_results, validation_date)
            
            results.append({
                'scan_date': current_date.strftime('%Y-%m-%d'),
                'validation_date': validation_date.strftime('%Y-%m-%d'),
                'results': validated
            })
            
            # התקדמות לאיטרציה הבאה
            current_date += timedelta(days=horizon)
            
        return results
```

### **Phase 3: UI Integration**

#### 3.1 New Backtest Tab
```python
# ui/tabs/historical_backtest_tab.py - קובץ חדש

class HistoricalBacktestTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """
        ממשק עם:
        - שדה טווח ימים (SpinBox: 7-90 ימים)
        - בחירת מודלים (RF/XGB/LGBM checkboxes)
        - בחירת אופקים (1D/5D/10D checkboxes)  
        - כפתור התחלה/עצירה
        - פס התקדמות
        - תצוגת תוצאות בזמן אמת
        """
        
    def start_backtest(self):
        """התחלת התהליך ברקע"""
        range_days = self.range_spinbox.value()
        controller = HistoricalBacktestController(range_days)
        
        # הרצה ב-worker thread כדי לא לחסום UI
        self.worker = BacktestWorker(controller)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.results_ready.connect(self.show_results)
        self.worker.start()
```

#### 3.2 Integration with Main App  
```python
# main_content.py - הוספה לקובץ הקיים

class MainContent(QWidget):
    def __init__(self):
        # ... קוד קיים ...
        
        # הוספת הטאב החדש
        self.historical_backtest_tab = HistoricalBacktestTab()
        self.tab_widget.addTab(self.historical_backtest_tab, "🕰️ Historical Backtest")
```

## 📊 תצוגת התוצאות המתוכננת

### **Real-time Progress Display:**
```
┌─────────────────────────────────────────┐
│  🕰️ Historical Backtest Progress        │
├─────────────────────────────────────────┤
│ Range: 30 days (01/09 - 30/09/2025)    │
│ Models Training: ████████████ 100%     │
│                                         │
│ ┌─── Horizon Progress ──────────────┐   │
│ │ 1D:  ███████████░ 25/30 (83%)    │   │
│ │ 5D:  ████████░░░░  4/6  (67%)    │   │  
│ │ 10D: ███░░░░░░░░░  1/3  (33%)    │   │
│ └───────────────────────────────────┘   │
│                                         │
│ Current: Scanning 25/09/2025           │
│ ETA: 12 minutes remaining               │
│                                         │
│ ┌─── Live Results ──────────────────┐   │
│ │ RF-1D:  68% avg accuracy (142 p)  │   │
│ │ XGB-5D: 74% avg accuracy (67 p)   │   │
│ │ LGBM-10D: 71% avg accuracy (23 p) │   │
│ └───────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### **Final Results Dashboard:**
```
┌─────────────────────────────────────────┐
│  📈 Backtest Results Summary            │
├─────────────────────────────────────────┤
│          │  1D   │  5D   │ 10D   │ Best │
│ ─────────┼───────┼───────┼───────┼──────┤
│ RF       │ 68.2% │ 71.5% │ 69.8% │ 5D   │
│ XGB      │ 71.1% │ 74.3% │ 72.6% │ 5D   │  
│ LGBM     │ 69.7% │ 73.1% │ 71.2% │ 5D   │
│ ─────────┼───────┼───────┼───────┼──────┤
│ WINNER   │ XGB   │ XGB   │ XGB   │XGB-5D│
└─────────────────────────────────────────┘

💡 Insights:
• 5-day horizon consistently outperforms
• XGB algorithm dominates all timeframes  
• Accuracy improves over time (learning effect)
• Volatility periods show accuracy drop

🎯 Recommendations:
• Use XGB-5D for production scanning
• Retrain weekly for optimal performance
• Consider ensemble of top 3 models
```

## 🎛️ תכנית המימוש המדויקת

### **Week 1: Core Training Enhancement**
- [ ] הוספת `train_multi_horizon_model()` ל-`ml/train_model.py`
- [ ] יצירת `build_labels_for_horizon()` 
- [ ] הוספת `load_data_until_date()` ל-`data/data_utils.py`
- [ ] בדיקות יחידה לפונקציות החדשות

### **Week 2: Backtest Controller**
- [ ] יצירת `ml/historical_backtest.py`
- [ ] מחלקת `HistoricalBacktestController`
- [ ] לוגיקת הלולאות לכל אופק
- [ ] מערכת שמירה ו-recovery

### **Week 3: UI Integration**
- [ ] יצירת `ui/tabs/historical_backtest_tab.py`
- [ ] Worker thread לביצוע ברקע
- [ ] Progress tracking ו-live updates
- [ ] שילוב במסך הראשי

### **Week 4: Results & Optimization**
- [ ] Dashboard לתצוגת תוצאות
- [ ] Export לקבצי Excel/JSON
- [ ] המלצות אוטומטיות
- [ ] Performance tuning

## ✅ בדיקת תקינות לפני התחלה

### **נתונים נדרשים:**
- ✅ נתונים מ-01/01/2024 (קיים)
- ✅ לפחות 120+ ימי מסחר לאימון
- ✅ נתוני Volume ו-OHLC

### **תלויות טכניות:**
- ✅ sklearn, pandas, numpy (קיים)
- ✅ PySide6 לUI (קיים)  
- ✅ מערכת הנתונים הקיימת

### **זיכרון ומהירות:**
- 🔍 **הערכה**: 9 מודלים × 30 ימים = זמן אימון ארוך
- 💡 **פתרון**: אימון מקבילי + שמירת cache
- ⚡ **אופטימיזציה**: Progressive training (לא מאמן מחדש כל פעם)

## 🚨 נקודות זהירות

### **1. זמן ביצוע**
- אימון 9 מודלים יכול לקחת 30-60 דקות
- צריך progress bar ואפשרות ביטול

### **2. שימוש במשאבים**  
- גיבוי אוטומטי של תוצאות ביניים
- ניקוי מודלים ישנים למניעת בזבוז דיסק

### **3. דיוק התוצאות**
- בדיקת תקינות נתונים לפני אימון
- validation של התאריכים והלוגיקה

---

## 📊 תצוגת תוצאות ודיווח

### **Live Results During Process:**
```
┌─────────────────────────────────────────┐
│  🔍 Scan Results - 25/09/2025           │
├─────────────────────────────────────────┤
│ Model: XGB-5D | BUY Signals Found: 23  │
│                                         │
│ ┌─── BUY Signals ───────────────────┐   │
│ │ AAPL: 0.74 prob | $150.25        │   │
│ │ MSFT: 0.68 prob | $285.10        │   │  
│ │ GOOGL: 0.81 prob | $125.45       │   │
│ │ TSLA: 0.72 prob | $210.80        │   │
│ │ ... (19 more)                    │   │
│ └───────────────────────────────────┘   │
│                                         │
│ Validation in 5 days → 30/09/2025      │
└─────────────────────────────────────────┘
```

### **Final Performance Report:**
```
┌─────────────────────────────────────────┐
│  📈 Final Results Report                │
├─────────────────────────────────────────┤
│ Period: 01/09 - 30/09/2025 (30 days)   │
│                                         │
│ ┌─── Model Performance ─────────────┐   │
│ │          │BUY Signals│Success Rate│   │
│ │ XGB-1D   │    142    │   68.3%   │   │
│ │ XGB-5D   │     67    │   74.6%   │   │  
│ │ XGB-10D  │     23    │   69.6%   │   │
│ │ RF-5D    │     71    │   71.8%   │   │
│ └───────────────────────────────────┘   │
│                                         │
│ � WINNER: XGB-5D (74.6% success)      │
│ 💰 Total BUY signals validated: 303    │
│ ✅ Successful predictions: 218 (71.9%) │
└─────────────────────────────────────────┘
```

## 🔬 Phase 5: Final Verification System

### **Post-Optimization Verification Process:**

```python
# ml/final_verification.py - קובץ חדש

class FinalVerificationEngine:
    """
    מערכת בדיקה סופית - האם השיפורים עובדים באמת?
    """
    
    def run_before_after_comparison(self, optimized_params: Dict):
        """
        השוואה לפני ואחרי אופטימיזציה
        
        Process:
        1. קח את הפרמטרים המאופטימזים מהbacktest
        2. הרץ סריקה עם פרמטרים ישנים על 30 ימים אחרונים
        3. הרץ סריקה עם פרמטרים חדשים על אותה תקופה
        4. השווה תוצאות
        """
        
        # תקופת הבדיקה - 30 ימים אחרונים (מחוץ לתקופת האימון)
        verification_start = datetime.now() - timedelta(days=30)
        verification_end = datetime.now()
        
        # סריקה עם פרמטרים ישנים (baseline)
        old_results = self.run_verification_scan(
            verification_start, verification_end, 
            use_optimized=False
        )
        
        # סריקה עם פרמטרים מאופטימזים
        new_results = self.run_verification_scan(
            verification_start, verification_end, 
            use_optimized=True, 
            optimized_params=optimized_params
        )
        
        # השוואה וייצור דוח
        improvement_report = self.compare_results(old_results, new_results)
        return improvement_report
    
    def compare_results(self, baseline: Dict, optimized: Dict) -> Dict:
        """
        השוואה מפורטת בין תוצאות
        
        Returns:
        {
            'improvement_found': bool,
            'accuracy_change': float,  # +5.2% או -2.1%
            'signal_count_change': int,
            'false_positive_reduction': float,
            'statistical_significance': float,
            'recommendation': str
        }
        """
```

### **Verification Results Display:**
```
┌─────────────────────────────────────────┐
│  🔬 Final Verification Report           │
├─────────────────────────────────────────┤
│ Comparison Period: Last 30 Days         │
│                                         │
│ ┌─── Before vs After ───────────────┐   │
│ │                │Before │ After  │Δ │   │
│ │ Accuracy       │ 68.2% │ 74.6% │+6.4│   │
│ │ BUY Signals    │  156  │  142  │-14│   │
│ │ Success Count  │  106  │  106  │ 0 │   │
│ │ False Positives│   50  │   36  │-14│   │
│ └───────────────────────────────────┘   │
│                                         │
│ 📊 Key Improvements:                    │
│ ✅ +6.4% accuracy improvement           │
│ ✅ -28% false positive reduction        │
│ ✅ Same profit, less risk               │
│                                         │
│ 🎯 Statistical Significance: 94.2%     │
│ 💡 Recommendation: DEPLOY OPTIMIZED    │
└─────────────────────────────────────────┘
```

## 🛠️ תכנית המימוש המעודכנת

### **Phase 1: Enhanced Training (Week 1)**
- [ ] `train_multi_horizon_model()` ב-`ml/train_model.py`
- [ ] `build_labels_for_horizon()`
- [ ] `load_data_until_date()` ב-`data/data_utils.py`
- [ ] **בדיקת תקינות:** אימון מודל בודד ובדיקה שהוא עובד

### **Phase 2: Backtest Controller (Week 2)** 
- [ ] `ml/historical_backtest.py`
- [ ] `HistoricalBacktestController` class
- [ ] **בדיקת תקינות:** הרצת backtest קטן (5 ימים) וולידציה

### **Phase 3: UI Integration (Week 3)**
- [ ] `ui/tabs/historical_backtest_tab.py`
- [ ] Worker thread עם progress tracking
- [ ] **בדיקת תקינות:** ממשק פועל ומציג תוצאות

### **Phase 4: Results & Analysis (Week 4)**
- [ ] Dashboard מפורט לתוצאות
- [ ] Export ושמירת דוחות
- [ ] **בדיקת תקינות:** דוחות נוצרים ומוצגים נכון

### **Phase 5: Final Verification (Week 5)**
- [ ] `ml/final_verification.py`
- [ ] השוואה לפני/אחרי על נתונים חדשים
- [ ] דוח סופי עם המלצות
- [ ] **בדיקת תקינות:** ווריפיקציה מוכיחה שיפור אמיתי

## 🚦 סדר הביצוע המומלץ

### **שלב הכנה (לפני תחילת הקוד):**
1. **בדיקת נתונים** - ודא שיש נתונים מספיקים ל-60+ ימים
2. **בדיקת מודל קיים** - הרץ אימון רגיל כדי לוודא שהמערכת עובדת
3. **הגדרת תיקיות** - צור את המבנה: `ml/models/historical/`, `ml/backtest_results/`

### **שלב 1: Multi-Horizon Training**
- התחל עם פונקציה אחת: `train_multi_horizon_model()`
- בדוק על מודל אחד (RF, 5D horizon)
- רק אחרי שזה עובד - הוסף את השאר

### **שלב 2: Mini Backtest**
- צור גרסה פשוטה של הבקר
- הרץ על 3 ימים בלבד
- ודא שהלוגיקה עובדת

### **שלב 3: הדרגתיות**
- הוסף UI בסיסי
- הוסף תיעוד תוצאות
- הוסף ווריפיקציה

## ✅ קריטריונים להצלחה

### **תוצאות מינימליות לאישור:**
- ✅ המערכת מסיימת ללא שגיאות
- ✅ לפחות 50+ BUY signals בכל horizon
- ✅ דיוק מעל 60% לפחות במודל אחד
- ✅ הווריפיקציה מוכיחה שיפור של 2%+ דיוק

### **אזהרות לבדיקה:**
- ⚠️ זמני ביצוע ארוכים (30-60 דקות)
- ⚠️ צריכת זיכרון גבוהה
- ⚠️ תלות ברשת לנתוני שוק

---

## 🎯 האישור הסופי המעודכן

התכנית כוללת עכשיו:
1. **Multi-horizon training** ✅
2. **Historical backtesting** ✅  
3. **Live progress tracking** ✅
4. **Detailed results reporting** ✅
5. **Final verification system** ✅
6. **Before/after comparison** ✅

**מוכן להתחיל עם Phase 1.1 - Enhanced Training? 🚀**