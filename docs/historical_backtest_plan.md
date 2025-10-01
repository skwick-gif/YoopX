# 🕰️ Historical Backtesting & Auto-Improvement Pipeline

## 📋 תוכנית מפורטת

### **Phase 1: Multi-Horizon Training System**
```python
# מערכת אימון רב-אופקית
def train_multi_horizon_models(cutoff_date: str):
    """
    אימון 3 מודלים נפרדים לאותו תאריך:
    - 1D: תחזית ליום הבא
    - 5D: תחזית ל-5 ימים
    - 10D: תחזית ל-10 ימים
    """
    horizons = [1, 5, 10]
    trained_models = {}
    
    for horizon in horizons:
        model_path = f"ml/models/model_{horizon}d_{cutoff_date}.pkl"
        model = train_horizon_specific_model(cutoff_date, horizon)
        save_model(model, model_path)
        trained_models[horizon] = model_path
    
    return trained_models
```

### **Phase 2: Historical Scanning Engine**
```python
# מנוע סריקה היסטורית
def run_historical_scan(scan_date: str, models: dict):
    """
    הרצת סריקה עם מודלים היסטוריים
    כאילו אנחנו באותו יום בעבר
    """
    scan_results = []
    
    for symbol in get_symbols_for_date(scan_date):
        # טען נתונים עד אותו תאריך בלבד
        historical_data = load_data_until_date(symbol, scan_date)
        
        # הרץ סריקה עם כל מודל
        predictions = {}
        for horizon, model_path in models.items():
            model = load_model(model_path)
            pred = predict_with_historical_data(model, historical_data)
            predictions[f'{horizon}d'] = pred
        
        scan_results.append({
            'symbol': symbol,
            'scan_date': scan_date,
            'predictions': predictions,
            'price_at_scan': historical_data['Close'].iloc[-1]
        })
    
    return scan_results
```

### **Phase 3: Outcome Validation System**
```python
# מערכת בדיקת תוצאות
def validate_predictions(scan_results: list, validation_date: str):
    """
    בדיקת מה קרה באמת אחרי הסריקה
    """
    validated_results = []
    
    for result in scan_results:
        symbol = result['symbol']
        scan_date = result['scan_date']
        entry_price = result['price_at_scan']
        
        # בדוק תוצאות אמיתיות
        actual_outcomes = {}
        for horizon in [1, 5, 10]:
            target_date = add_business_days(scan_date, horizon)
            if target_date <= validation_date:
                actual_price = get_price_on_date(symbol, target_date)
                success = actual_price >= entry_price * 1.01  # 1%+ profit
                actual_outcomes[f'{horizon}d'] = {
                    'success': success,
                    'actual_price': actual_price,
                    'return_pct': (actual_price - entry_price) / entry_price * 100
                }
        
        result['actual_outcomes'] = actual_outcomes
        validated_results.append(result)
    
    return validated_results
```

### **Phase 4: Performance Analysis & Auto-Tuning**
```python
# ניתוח ביצועים וכיוונון אוטומטי
def analyze_and_improve(validated_results: list):
    """
    ניתוח התוצאות והצעת שיפורים
    """
    analysis = {}
    
    for horizon in [1, 5, 10]:
        horizon_key = f'{horizon}d'
        
        # חישוב מטריקות
        predictions = [r['predictions'][horizon_key] for r in validated_results 
                      if horizon_key in r.get('actual_outcomes', {})]
        outcomes = [r['actual_outcomes'][horizon_key]['success'] 
                   for r in validated_results
                   if horizon_key in r.get('actual_outcomes', {})]
        
        if predictions and outcomes:
            accuracy = sum(outcomes) / len(outcomes)
            
            # ניתוח ביצועים לפי רמות הסתברות
            high_conf_preds = [(p, o) for p, o in zip(predictions, outcomes) if p >= 0.7]
            mid_conf_preds = [(p, o) for p, o in zip(predictions, outcomes) if 0.5 <= p < 0.7]
            
            analysis[horizon_key] = {
                'total_predictions': len(predictions),
                'accuracy': accuracy,
                'high_conf_accuracy': sum(o for p, o in high_conf_preds) / len(high_conf_preds) if high_conf_preds else 0,
                'mid_conf_accuracy': sum(o for p, o in mid_conf_preds) / len(mid_conf_preds) if mid_conf_preds else 0,
                'suggested_threshold': suggest_optimal_threshold(predictions, outcomes)
            }
    
    # הצעת כיוונון
    improvements = suggest_model_improvements(analysis)
    return analysis, improvements

def suggest_optimal_threshold(predictions: list, outcomes: list) -> float:
    """מציאת סף אופטימלי לפי ROC"""
    from sklearn.metrics import roc_curve
    fpr, tpr, thresholds = roc_curve(outcomes, predictions)
    
    # מצא סף שממקסם (TPR - FPR)
    optimal_idx = np.argmax(tpr - fpr)
    return thresholds[optimal_idx]
```

### **Phase 5: Automated Rolling Backtest**
```python
# בדיקה אוטומטית מתגלגלת
def run_rolling_backtest(start_date: str, end_date: str, step_days: int = 7):
    """
    הרצת בדיקה מתגלגלת על תקופה שלמה
    """
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    results_timeline = []
    
    while current_date <= end_dt:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"🔄 Processing {date_str}...")
        
        # שלב 1: אימון מודלים
        models = train_multi_horizon_models(date_str)
        
        # שלב 2: סריקה היסטורית
        scan_results = run_historical_scan(date_str, models)
        
        # שלב 3: המתנה לתוצאות (דימוי)
        validation_date = (current_date + timedelta(days=14)).strftime('%Y-%m-%d')
        
        # שלב 4: בדיקת תוצאות
        if validation_date <= end_date:
            validated = validate_predictions(scan_results, validation_date)
            
            # שלב 5: ניתוח ושיפור
            analysis, improvements = analyze_and_improve(validated)
            
            results_timeline.append({
                'date': date_str,
                'scan_count': len(scan_results),
                'analysis': analysis,
                'improvements': improvements
            })
        
        # התקדמות
        current_date += timedelta(days=step_days)
    
    return results_timeline
```

## 🎛️ ממשק משתמש מוצע

### **Training & Backtest Control Panel**
```
┌─────────────────────────────────────┐
│  🕰️ Historical Training & Backtest   │
├─────────────────────────────────────┤
│ Start Date: [2024-08-01] 📅         │
│ End Date:   [2024-09-01] 📅         │
│ Step Size:  [7 days] ⏭️             │
│                                     │
│ Horizons: ☑️ 1D ☑️ 5D ☑️ 10D        │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🚀 START BACKTEST              │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Progress: ████████░░ 80%            │
│ Current: 2024-08-25                 │
│ ETA: 3 minutes                      │
│                                     │
│ ┌─── Live Results ────────────────┐ │
│ │ 📊 1D: 67% accuracy (234 preds) │ │
│ │ 📊 5D: 72% accuracy (189 preds) │ │
│ │ 📊 10D: 65% accuracy (145 preds)│ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### **Results Dashboard**
```
┌─────────────────────────────────────┐
│  📈 Backtest Results Timeline       │
├─────────────────────────────────────┤
│     Date    │ 1D Acc│ 5D Acc│10D Acc│
│ 2024-08-01  │  58%   │  63%  │  71%  │
│ 2024-08-08  │  61%   │  67%  │  69%  │
│ 2024-08-15  │  64%   │  71%  │  68%  │
│ 2024-08-22  │  67%   │  72%  │  65%  │
│                                     │
│ 📊 Trend: 📈 Improving Overall      │
│ 🎯 Best: 5D model consistently wins │
│ ⚠️ Issue: 10D degrades over time    │
│                                     │
│ 💡 Auto-Suggestions:               │
│ • Focus on 5D predictions          │
│ • Retrain 10D model weekly         │ 
│ • Increase tech signal weight      │
└─────────────────────────────────────┘
```

## 🔧 Implementation Plan

### **Week 1-2: Core Infrastructure**
- [ ] Multi-horizon training system
- [ ] Historical data management
- [ ] Model versioning & storage

### **Week 3-4: Backtest Engine**
- [ ] Historical scanning simulation
- [ ] Outcome validation system
- [ ] Performance analytics

### **Week 5-6: Auto-Improvement**
- [ ] Threshold optimization
- [ ] Parameter tuning algorithms
- [ ] Rolling backtest framework

### **Week 7-8: UI & Integration**
- [ ] Control panel interface
- [ ] Results visualization
- [ ] Progress monitoring
- [ ] Integration with main app

## 💡 רעיונות נוספים

### **1. Market Regime Detection**
```python
# זיהוי תנאי שוק והתאמה בהתאם
if detect_bull_market(date):
    model_params['aggressive_mode'] = True
elif detect_bear_market(date):
    model_params['conservative_mode'] = True
```

### **2. Feature Engineering Evolution**
```python
# שיפור פיצ'רים בהתבסס על תוצאות
def evolve_features(performance_data):
    # מצא פיצ'רים שתורמים הכי הרבה
    # הוסף פיצ'רים דומים
    # הסר פיצ'רים שלא עוזרים
```

### **3. Ensemble Optimization**
```python
# כיוונון משקלי אנסמבל לפי ביצועים
def optimize_ensemble_weights(backtest_results):
    # מצא שילוב אופטימלי של מודלים
    # עדכן משקלים בזמן אמת
```

### **4. Risk Management Integration**
```python
# שילוב ניהול סיכונים
def adjust_for_risk(predictions, market_volatility):
    # התאם ספים לפי תנודתיות
    # הוסף מסנני סיכון נוספים
```

## 🎯 מטרות ותוצאות צפויות

### **Short-term (1-2 months)**
- ✅ Fully automated backtesting system
- ✅ Historical performance validation
- ✅ Basic auto-improvement loops

### **Medium-term (3-6 months)**
- 📈 15-25% accuracy improvement
- 🎛️ Self-tuning parameters
- 📊 Comprehensive performance tracking

### **Long-term (6-12 months)**
- 🤖 Fully autonomous ML system
- 🎯 Market-adaptive strategies
- 🚀 Consistent outperformance

זה נשמע לך כמו התוכנית הנכונה? איזה חלק תרצה שנתחיל לפתח קודם?