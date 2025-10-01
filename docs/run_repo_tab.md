<div dir="rtl" align="right">

## לשונית Run Repo – מאגר ריצות ("Auto Discovery" / ארכיון ניסויים) (מעודכן)

### 1. מטרה
מרכז תצוגה וניהול של ריצות היסטוריות שנשמרו: Backtest, Optimize, Walkforward (ואולי ריצות נוספות: Data Update, Model Train). מאפשר להשוות, לסנן, לטעון קונפיגורציה מחדש, ולזהות “תגליות” (Auto Discovery) – כלומר ריצות שנמצאו כחריגות חיובית במדדים.

### 2. מה נחשב "ריצה" (Run)
אובייקט שמכיל:
1. סוג (type): backtest / optimize / walkforward / train וכו'.  
2. חותמת זמן (timestamp).  
3. פרמטרים (params): המילון שהזין את הריצה (ספים, טווחים, objective, horizons).  
4. תוצאות (metrics): Sharpe, CAGR, MaxDD, WinRate, Trades וכו'.  
5. Metadata נוסף: גירסת קוד / hash, snapshot פעיל, seed, הערות.  

### 3. אינטגרציה עם שאר הלשוניות
| לשונית | שימוש בנתוני Run Repo |
|--------|-----------------------|
| Backtest | טען ריצה טובה ישנה להשוואה מול חדשה לאחר שינוי לוגיקה. |
| Optimize | השוואת רשימת Top Param Sets בין תקופות שונות / גרסאות מודל. |
| Walkforward | בדיקת שיפור יציבות לאחר Retrain / שינוי פרמטרים. |
| Model Dashboard | מזהה אם Snapshot חדש (Active) שיפר/החמיר; רצוי לשמור ציון snapshot בטבלת הריצה. |
| IBKR | אימות לפני הפעלה חיה – ריצה אחודה שמסכמת את הסט הפעיל. |

### 4. רכיבי UI (אפשרי)
1. Filter Bar – סינון לפי סוג / טווח תאריכים / מינימום Sharpe / טקסט חופשי.  
2. Runs Table – עמודות: Type, Timestamp, Sharpe, CAGR, MaxDD, Trades, Tag / Notes.  
3. Details Pane – הצגת JSON מלא של params + metrics.  
4. Load Params To... – כפתור שמטעין סט פרמטרים אל לשונית רלוונטית (למשל Optimize / Backtest).  
5. Diff Runs – בחירת שתי ריצות → הצגת הפרשי מדדים ופרמטרים.  
6. Export / Delete – ניהול קבצים.  
7. Tag / Note – הוספת תווית מילולית ("Baseline", "Post-Drift", "Exp_Seed42").  
8. Auto Discovery Highlight – הדגשת ריצות שעוברות קריטריון (Sharpe > X && MaxDD < Y וכו').  
9. Help – מדריך זה.  

### 5. זרימת עבודה טיפוסית
1. מריץ Optimize → שומר Top 3 פרמטרים כריצות.  
2. מריץ Backtest מלא לפרמטר הטוב ביותר → נשמר.  
3. מריץ Walkforward לאימות → נשמר.  
4. פותח Run Repo: מסנן לפי תאריך היום → בודק עקביות המדדים בין שלוש הריצות.  
5. אם עקביות טובה → מסמן Tag "deploy_candidate".  
6. בהמשך (לאחר Drift) – משווה מול אותה ריצה כדי לראות שחיקה.  

### 6. Auto Discovery – רעיון
מודול פנימי שמסמן ריצות “בעלות עניין” אוטומטית:
1. קריטריונים סטטיים (Sharpe >= 1.5, MaxDD <= 20%).  
2. סינון מינימום Trades.  
3. בדיקת אחידות: סטיית תקן Sharpe בין Walkforward Folds < סף.  
4. שמירה כ-Flag בקובץ JSON של הריצה ("highlight": true).  
5. UI מדגיש בשורה צהובה / אייקון נורה.  

### 7. מבנה קבצים (דוגמה)
```
runs/
	backtest/
		2024-09-18_120500/
			params.json
			metrics.json
			notes.txt (אופציונלי)
	optimize/
		2024-09-18_121100/
			...
	walkforward/
		...
	index.json  # רשימת ריצות (אפשר האצה לטעינה)
```

### 8. Diff / השוואת ריצות
השוואה טובה = לא רק מי Sharpe גבוה יותר אלא:
1. Trade Count דומה?  
2. MaxDD לא הוחמר משמעותית?  
3. שיפור CAGR לא בא על חשבון חשיפה פי כמה.  
4. האם פרמטרים אחרים זזו מעט (L1 distance בפרמטרים).  
5. שינוי בגרסת Snapshot – תיעוד משמעותי (מודל חדש?).  

### 9. Troubleshooting
| בעיה | סיבה | פתרון |
|------|------|--------|
| ריצה לא מופיעה | index.json לא עודכן / שמירה נכשלה | הפעל Re-index / בדוק הרשאות |
| נתוני metrics חסרים | השמירה עצרה באמצע | בדוק לוג Worker, אפשר מחיקת ריצה חלקית |
| Diff לא זמין | בחירת פחות משתי ריצות | סמן 2 שורות בדיוק |
| Highlight לא נדלק | קריטריונים לא מולאו | התאם ספים / בדוק חישוב Auto Discovery |

### 10. בסט-פרקטיס
1. כתוב Notes לריצות מפתח – מקטין בלבול עתידי.  
2. נקה ריצות ישנות/כפולות כדי לשמור על מהירות טעינה.  
3. אל תבצע השוואות רק על Sharpe – בדוק MaxDD ו-Trade Distribution.  
4. בנה Naming Convention אם אין index (למשל type__timestamp__tag).  
5. השתמש ב-Tag "baseline" לבנצ'מרק קבוע מולו בודקים.  

### 11. Mini Glossary
| Term | הסבר |
|------|------|
| Run Repository | מאגר קבצים של ניסויי ביצועים. |
| Index | קובץ מרכזי שמפרט את כל הריצות לטעינה מהירה. |
| Auto Discovery | סימון אוטומטי של ריצות חריגות חיובית. |
| Diff | השוואת שני סטים של פרמטרים / מדדים. |
| Tag | תווית פשוטה למיון ידני. |
| Highlight | דגל חזותי שמציין עמידה בקריטריון. |

### 12. אינטגרציה עם Drift / Adaptive Threshold
כאשר drift מפעיל אימון מחדש אוטומטי – ריצות חדשות צריכות להישמר תחת Tag "post-drift" כדי לא להתבלבל עם baseline. Thresholds שעודכנו adaptively משפיעים על סינון עסקאות ולכן על מדדים – מתעד timestamp + threshold בעת הריצה.

### 13. סיכום קצר
Run Repo הוא הזיכרון ההשוואתי. תהליך מומלץ מחזורי: Generate → Evaluate → Tag (baseline / post-drift / tuned) → Compare → Decide.

---
שדרוגים עתידיים: גרף Equity overlay, מעקב היסטוריית Threshold לכל ריצה, פילוח לפי סוג Drift.

</div>
