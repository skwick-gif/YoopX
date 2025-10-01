<div dir="rtl" align="right">

# מסמך UI & כפתורי פעולה (מעודכן)

מסמך זה משמש כ"knowledge base" פנימי להסברים תמציתיים על התנהגות ה־UI, כפתורים, דיאלוגים וזרימות לוגיקה. נוסיף סעיפים חדשים בהמשך לפי שאלות שעולות.

---
## תוכן עניינים
1. [כפתורי פעולה בלשונית הסריקה](#כפתורי-פעולה-בלשונית-הסריקה)
2. (פנוי להוספה)

---
## כפתורי פעולה בלשונית הסריקה (כולל אוטומציה)
שישה כפתורים בדיאלוג ההגדרות (Actions):

| כפתור | מופעל מיידית? | תנאים נוספים | מה עושה בפועל | הודעות / תקלות נפוצות |
|-------|---------------|---------------|---------------|-------------------------|
| Train ML | כן | אין | משדר `train_ml_requested` → אימון רקע. אין Popup בסיום – עדכון Inline (Status + Active Metrics). אם `auto_rescan` מסומן תתרחש סריקה אוטומטית. | אין שינוי? בדוק לוג, אולי salvage/load או drift retrain מקביל. |
| Calibrate | כן | מודל קיים בדיסק | משדר `calibrate_requested` → `on_calibrate_ml` שמבצע כיול (התאמת הסתברויות). | אם אין מודל: הודעת מידע או ללא שינוי נראה. |
| Suggest Thresh | כן | קיום מודל טעון עם `val_probs` ו-`val_labels` | טוען מודל (rf/xgb/lgbm לפי בחירה), מחשב סף אופטימלי (F1) ומעדכן `ml_thresh_spin`. | "Model not found" או "No validation probabilities stored" אם חסר מידע. |
| Optimize Weights | לא (Disabled עד תוצאות) | חייב תוצאות סריקה (`_last_scan_results`) | מחשב סט משקולות (w_prob, w_rr, w_fresh, w_pattern) מיטבי לפי מטריקה (corr) ומעדכן ספינרים. | "No optimization result" אם רשימת תוצאות ריקה / חסרות שדות. |
| Explain Row | לא (עד תוצאות) | תוצאות + שורה נבחרת + `rec['_features']` + מודל טעון | מחשב תרומת פיצ'רים (top-k) ומציג דיאלוג טקסטואלי עם z-score * importance. | "No captured feature vector" אם אין `_features`; "Model not loaded" אם לא נמצא מודל. |
| Score Decomp | לא (עד תוצאות) | תוצאות + שורה נבחרת | מחשב ופירוק משקלות / רכיבים (prob, rr, freshness, pattern) לפי נוסחה נוכחית (weighted/geometric) ומראה דיאלוג. | אם ערכים חסרים: רכיב יאופס ל־0; אין הודעת שגיאה אלא תוצאה חלקית. |

### לוגיקת Enable / Disable
מנוהלת בפונקציה `_update_action_buttons` ב-`scan_tab.py`:
- שלושה כפתורים שתלויים בתוצאות: Optimize Weights / Explain Row / Score Decomp → פעילים רק כאשר `self._last_scan_results` לא ריק.
- Train / Calibrate / Suggest Thresh תמיד פעילים (גם לפני סריקה ראשונה).

### סיבות נפוצות לכך שכפתור "לא עובד"
1. אין מודל שמור בתיקיית המודל → Suggest Thresh / Explain Row לא יחזירו תוצאה.  
2. סריקה טרייה לא רצה לאחר אימון → `_features` לא הוטמעו בתוצאות ולכן Explain Row נכשל.  
3. לא נבחרה שורה בטבלה → Explain Row / Score Decomp מציגים הודעת בחירה.  
4. אין מספיק שדות (score / ml_prob) לחישוב קורלציה → Optimize Weights מחזיר None.  
5. כיול/אימון עדיין רץ → עוד לא נוצר קובץ מודל עד סיום.  

### מה כדאי לעשות אחרי אימון (עדכון)
1. לעקוב בסטטוס + Metrics Panel (AUC / Threshold / Samples).  
2. אם `auto_rescan` לא מסומן – להריץ SCAN כדי לייצר `_features` טריים.  
3. Optimize Weights → SCAN חוזר (רק אם רוצים לעדכן Score מיד).  
4. אם התקבלה התראת Drift סמוך לאימון – לשקול השוואה מול snapshot קודם לפני פעולה.  

### הודעות מידע עיקריות
- Model not found: לא נמצא קובץ מודל בקובץ הנתיב הצפוי.  
- No validation probabilities stored: המודל נטען אבל לא כולל `val_probs`/`val_labels`.  
- No captured feature vector: יש תוצאות, אבל רשומה ספציפית חסרה `_features` (נדרש ריצת סריקה לאחר אימון עם לכידת פיצ'רים).  

---
## הוספת סעיפים חדשים
כשעולה שאלה חדשה: 
- נא לתאר בקצרה את המצב ומה ציפית שיקרה. 
- נוסיף סעיף חדש או נרחיב טבלה קיימת.

---
### אוטומציה קצר
| מנגנון | מה עושה | איפה מוגדר |
|--------|---------|-------------|
| Auto-Rescan | מריץ SCAN אחרי אימון אם מסומן | Scan Dialog + Model Dashboard checkbox |
| Adaptive Threshold | מעלה/מוריד global threshold על בסיס Precision חי | `main_content._run_live_evaluation_cycle` |
| Drift Sustained | מזהה רצף DriftAvg גבוה → מסמן רה-אימון | Wrapper ב-Scan worker status |
| Auto-Retrain | מפעיל אימון אם drift דגל + cooldown עבר | automation.json (`auto_retrain_on_drift`) |

</div>
