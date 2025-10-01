<div dir="rtl" align="right">

## לשונית Model Dashboard – מדריך מעודכן

### 1. מטרה עיקרית
לשונית ה-Model Dashboard מרכזת את מחזור החיים של המודלים (Training / Snapshots / הפעלה פעילה / Drift / Feature Store / אוטומציה) ומאפשרת:
1. צפייה ב-Snapshots היסטוריים (תיקיית `ml/registry/...`).
2. קביעת המודל הפעיל (משפיע על סריקות בלשונית SCAN ועל חישובי הסתברויות).
3. אימון מחדש (Single / Multi horizon) + הפקת מטא-דאטה (AUC, CV AUC, Horizons, Thresholds, Feature Stats, Class Balance).
4. ניטור Drift אוטומטי + התראות (לפי ספים ניתנים להגדרה בקובץ `config/automation.json`).
5. צפייה מהירה ב-Horizons ובמדדי ביצועים היסטוריים + לוח Metrics פעיל (Active Model Metrics) ללא פופאפים.
6. התאמה דינמית (Adaptive) של Threshold לפי Precision חי.
7. טריגר Auto-Rescan לאחר אימון (אם סומן) כדי שהמודל החדש ישתקף מיד ב-SCAN.

### 2. שילוב עם לשוניות אחרות
| לשונית | אינטראקציה עם Model Dashboard |
|--------|-------------------------------|
| Scan | משתמשת ב-ACTIVE snapshot כדי לטעון מודל + thresholds. אם multi-horizon – בחירת horizon מתבצעת שם. |
| Optimize | משקלול פרמטרי אסטרטגיה – לא מאמן מודל ML, אך תוצאות אופציונליות נשמרות ל-Run Repo; לאחר שיפור פרמטרים אפשר לחזור ולבצע Train כאן כדי לרענן הסתברויות. |
| Backtest | יכול לרוץ עם מדדי אסטרטגיה ללא ML או בשילוב (אם downstream logic משתמש ב-ML score). בחירת מודל פעיל משפיעה על חישובי Score בחלקים משותפים. |
| Walkforward | הערכת יציבות אסטרטגית על פני חלונות זמן; מאפשר לקבל החלטה האם לאמן מודל חדש. |
| IBKR | בחירת Symbolים מסריקה אחרונה (שהושפעה מהמודל הפעיל), ולכן עדכון Snapshot משפיע גם על רשימות ההזמנות. |
| Run Repo | ריצות שמורות (Backtest / Optimize / Walkforward) מאפשרות להשוות לפני/אחרי אימון מודל חדש. |

### 3. רכיבים במסך (עדכני)
1. טבלת Snapshots – עמודות:
	- Timestamp – מפתח תיקייה (שם snapshot)
	- Model – סוג בסיסי (rf / xgb / lgbm / ensemble אם נוצר)
	- Samples – גודל סט אימון / (לפי מה שנשמר במטא)
	- CV AUC – ממוצע AUC ב-Cross Validation (אם זמין)
	- Dir – הנתיב לתיקיית snapshot (יחסי או מוחלט)
	- Horizons – רשימת אופקי תחזית (למשל: 5,10,20)
2. כפתורים / תפריט Overflow (⋮):
	- Manual Refresh (רענון Index)
	- Set Active (ידני)
	- Open Active Dir
	- Compute Drift Now (סנפשוט חישוב מידי)
	- Refresh Feature Store
3. Train / Update Model Box:
	- Model Select – בחירת בסיס: rf / xgb / lgbm (Ensemble מחושב במקום אחר אם קיים מודל meta).
	- Horizons – רשימת אופקים מופרדת בפסיק. ריק = מודל יחיד.
	- Auto-rescan – אם מסומן: לאחר אימון מוצלח יאופשר טריגר לסריקת SCAN מחדש (מימוש בפועל תלוי בהאזנה לסיגנל). 
	- Train Model – התחלת תהליך אימון (יוזם Worker/Backend – לפי הקוד הקיים שלך).
4. Usage Guide (Panel מתקפל) – הסבר זרימה (כדי לצמצם מעבר לכאן).
5. Feature Store & Drift Box:
	- Refresh – רענון קטלוג features (גיל וקטורי פיצ'רים).
	- Drift – חישוב ידני (אם רוצים לבדוק מיידית).
	- טבלה: Symbol | Age(s) | Feature Count.
	- Drift Label: ערך ממוצע (אם n/a → אין feature_stats במודל הפעיל או חוסר נתונים).
6. Active Model Metrics (חדש):
	- מציג: Model, Val AUC, CV AUC, Samples, Threshold (global), Horizons, Drift אחרון.
	- נטען אוטומטית לאחר אימון / בעת שינוי Active.
7. הודעות אימון: אין יותר Popup; הכל נכנס לסטטוס ול-Info Label.
8. Adaptive Threshold: אם precision חי נמוך לאורך זמן – threshold עולה בהדרגה; אם גבוה מאוד – יורד (בגבולות 0.3–0.9).

### 4. מבנה קבצים חשוב
```
ml/
  registry/
	 index.json                # רשימת Snapshots (מערך של מטא-אובייקטים)
	 ACTIVE.txt                # מצביע לנתיב snapshot פעיל
	 <timestamp>/
		 model.pkl / model.json # ייצוג המודל (בהתאם לסוג)
		 metadata.json          # horizons, feature_stats, thresholds, metrics...
		 thresholds.json        # גבולות המלצות / הפילטר ML Prob (אם קיים)
  feature_store/
		 ... קבצי features per symbol ...
```

### 5. זרימת עבודה כרונולוגית מומלצת (עדכון עם אוטומציה)
1. איסוף נתונים בסיסי / עדכון Feature Store (תהליך חיצוני / Worker).
2. אימון ראשוני בלשונית Model Dashboard – הזן Horizons (אם רוצים multi) → Train.
3. בדיקה: ודא שה-Snapshot מופיע בטבלה. קבע אותו כ-Active (Set Active).
4. עבור ללשונית Scan – הרץ SCAN ובדוק הסתברויות / Score; התאמת Threshold (Suggest Thresh או Min ML Prob).
5. אם יש כמה מודלים (rf/xgb/lgbm), בצע אימונים נוספים בכל אחד → ניתן לחשוב על יצירת ensemble (אם לוגיקה קיימת מאחורי הקלעים).
6. בצע Walkforward (ראה מדריך Walkforward) כדי לבדוק יציבות – אם פער ביצועים גדול בין חלונות → שקול שיפור פיצ'רים / הגדרות.
7. בצע Optimize (פרמטרים אסטרטגיים) → השווה לפני/אחרי ב-Run Repo.
8. ניטור Drift – מתרחש אוטומטית דרך תוצאות סריקה; אם החריגה רציפה (ברירת מחדל: >1.25 חמש פעמים) → התראה + דגל Auto-Retrain (אם מופעל בקונפיג).
9. לאחר Retrain: שמור Snapshot חדש → קבע Active → הרץ Scan שוב → עדכן החלטות מסחר (IBKR / ייצוא).

### 6. מדדי אימון / Thresholds / Adaptive Logic
| פריט | הסבר | שימוש מעשי |
|------|------|-----------|
| CV Mean AUC | הערכת איכות כללית מבוקרת | השוואה בין Snapshots – הפרש קטן לא בהכרח מצדיק החלפה מהר |
| Horizons | אופקים (Bars קדימה) שבהם הוגדר Target | מאפשר לבחור horizon ממוקד בסריקה (אם יש טור `prob_h_X`) |
| Feature Stats | ממוצע / סטיית תקן לכל פיצ'ר | משמש ל-Explain / Drift / נרמול תרומות |
| Thresholds | סף Probability אופטימלי (F1) + היסטוריה ב-thresholds.json | מסנן תוצאות נמוכות ב-SCAN; מתעדכן adaptively לפעמים |
| Adaptive Threshold | העלאה/הורדה קטנה (±0.02) לפי precision חי | משמר דיוק בלי לבנות מודל כל רגע |
| Drift | סטייה ממוצעת בין התפלגות פיצ'רים נוכחית ל-Feature Stats | טריגר לריענון מודל / העלאת ערנות |

### 7. טיפים ובסט-פרקטיס
1. התחלה פשוטה: מודל בודד (rf) + אופק יחיד (למשל 10). לאחר יציבות – הוסף אופקים.
2. אל תרוץ לאנבל (Ensemble) לפני שיש לפחות שני מודלים טובים ורב-אינפורמטיביים.
3. שמור תיעוד חיצוני (Change Log) מה שינית בין Snapshots – קל יותר להסביר הבדלי ביצועים.
4. בדוק Drift אחרי אירועים שוק חריגים (Gapי ענק, FOMC, Earnings Season).
5. אם AUC יורד אבל Drift נמוך – זה יכול להצביע על דליפת מידע שנפתרה / שינוי Target Definition.
6. אל תכוון רק ל-AUC: בדוק גם Precision/Recall בחיתוך הפעלה בפועל.

### 8. קובץ אוטומציה (automation.json) – מפתחות רלוונטיים
```json
{
	"auto_train_on_start": false,
	"default_train_model": "rf",
	"default_train_horizons": "5,10,20",
	"auto_optimize_ensemble": false,
	"auto_scan_on_start": false,
	"auto_retrain_on_drift": true,
	"drift_high_threshold": 1.25,
	"drift_sustain_count": 5,
	"drift_notify_mode": "inline",  // inline | popup | silent
	"retrain_cooldown_hours": 6
}
```
הגדרות שלא קיימות בקובץ – מקבלות ערכי ברירת מחדל.

### 9. תקלות נפוצות (Troubleshooting)
| סימפטום | סיבה אפשרית | פעולה מוצעת |
|---------|--------------|--------------|
| Snapshot לא מופיע | `index.json` לא עודכן | הפעל Refresh או ודא שהקוד המייצר index רץ |
| ACTIVE.txt מצביע לתיקייה חסרה | תיקייה נמחקה ידנית | בחר Snapshot חדש ולחץ Set Active |
| Drift תמיד n/a | אין `feature_stats` במטא | ודא שהאימון שומר סטטיסטיקות (פונקציית אימון) |
| Scan לא מציג הסתברויות חדשות | לא עודכן Active או קאש בזיכרון | לחץ Set Active שוב / הפעל מחדש אפליקציה |
| Horizons ריק למרות שהגדרת | metadata.json לא נכתב נכון | בדוק לוגים אימון / הרשאות כתיבה |

### 10. מתי לאמן מחדש?
שיקולים:
1. Drift > 1.0 (לפי ההיוריסטיקה שלך) לאורך כמה בדיקות עוקבות.
2. ירידה ב-Precision או F1 Live בלוגים.
3. שינוי פרמטרי אסטרטגיה מהותי (Optimize) המשפיע על תכונות מחושבות.
4. הוספת פיצ'רים חדשים (Feature Engineering) – יש צורך ב-Feature Stats חדשים.
5. אירוע שוק מבני (Regime Shift) – ויקס קופץ, שינוי ריבית משמעותי.

### 11. סיכום קצר
Model Dashboard הוא המרכז הסטטי/ניהולי של כל מה שמזין את ה-Scan והחלטות downstream. עבודה מסודרת: (אימון) → (קביעת Active) → (Scan) → (Walkforward/Optimize) → (Monitor Drift) → (ריענון מחזורי) שומרת על מערכת עקבית, ניתנת להסבר ויציבה.

----
רעיונות המשך: גרף היסטוריית Drift/AUC, עריכת thresholds.json מה-UI, תצוגת פקטור Feature Importance דינאמית.

</div>

