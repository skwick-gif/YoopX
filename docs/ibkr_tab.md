<div dir="rtl" align="right">

# לשונית IBKR – חיבור וברוקראז' (Paper / Live)

### 1. מטרה
לתאם בין תוצאות הסריקה (Score / ML Prob) לבין הוראות מסחר בפועל (Paper בתחילה). מאפשר בחירת סמלים, תזמון ושליחה עם בקרה על גודל פוזיציה.

### 2. זרימת עבודה טיפוסית
1. הרץ SCAN → קבל רשימת מועמדים מסוננים לפי threshold הנוכחי.
2. סמן סמלים/סינון נוסף (Price, ATR וכו').
3. Preview Orders – חישוב סוג פעולה (לונג), Stop/Target (אם מוגדר לוגית), גודל (Position Sizing Rule).
4. Review → Send (Paper). בעתיד: מעבר לחשבון חי.

### 3. תלות במודל פעיל
המודל הפעיל (Active snapshot) ו-thresholds.json כבר מוטמעים upstream בסריקה; הלשונית מקבלת רשימה נקייה – אין צורך לטעון מודל כאן.

### 4. רכיבי UI (דוגמה)
| רכיב | תפקיד |
|------|--------|
| כפתור Preview | מחשב פקודות מבלי לשלוח |
| כפתור Send | שולח את הפקודות (Paper) |
| Size Mode | קביעה: Fixed / %Equity / ATR Risk |
| Risk per Trade | אחוז הון בסיכון (אם ATR-based) |
| Table Orders | מציג: Symbol, Action, Qty, Entry, Stop, Target, Est Risk |
| Status | הודעות שגיאה / הצלחה |

### 5. אינטגרציה עם Drift / Retrain
אם Drift מפעיל אימון מחדש אוטומטי בין Preview ל-Send: מומלץ לרענן SCAN כדי לוודא שהסינון תואם Threshold החדש (Reduce stale exposure).

### 6. בטיחות
1. אין שליחה לחשבון חי לפני בדיקת Paper ≥ X ימים.
2. תעד תמיד את snapshot timestamp בשדה הערה להזמנה.
3. במקרה של Error בשורה – לא לשלוח שאר ההזמנות “על עיוור”.

### 7. Troubleshooting
| בעיה | סיבה | פתרון |
|------|------|--------|
| טבלה ריקה | לא הרצית SCAN קודם | הרץ SCAN מחדש |
| נתון Risk=0 | ATR לא מחושב / מחיר חסר | בדוק נתוני סימבול בפיצ'רים |
| שגיאת חיבור | API לא מורשה / Session סגור | אשר הגדרות TWS / Gateway |
| הזמנות עם כמות אפס | כלל Position Size לא מחזיר ערך | בדוק נוסחה / פרמטרים |

### 8. סיכום קצר
לשונית IBKR לוקחת את מה שהמערכת כבר מסננת ומשקללת (Active Model + Threshold Adaptive) והופכת אותו לפעולה. שמור עקביות: פקודות מבוססות רק על ריצת SCAN עדכנית.

</div>
