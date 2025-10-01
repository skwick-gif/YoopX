"""
דוגמה מדויקת - חלון הפירוט של ה-SCORE
======================================
מראה איך אמור להיראות החלון בצד ימין של הטבלה
"""

def show_enhanced_score_detail_example():
    """דוגמה מדויקת של מה שיופיע בחלון ההסבר"""
    
    print("📱 דוגמה: חלון הפירוט בצד ימין של הטבלה")
    print("=" * 50)
    print()
    
    # דוגמה 1: מניה עם ציון גבוה
    print("🔍 דוגמה 1: לחצת על שורה של GOOGL")
    print("-" * 50)
    
    example1 = """
📊 GOOGL - Enhanced Score Breakdown
========================================

🎯 Final Enhanced Score: 85.0/100
🏆 Grade: A+
📋 Recommendation: BUY

📈 Component Breakdown:
-------------------------
• Technical Analysis (40%): 80.0
• Fundamental Analysis (35%): 95.0
• Sector Performance (15%): 75
• Business Quality (10%): 85.0

🔢 Weighted Calculation:
(80.0 × 0.40) + (95.0 × 0.35) + (75 × 0.15) + (85.0 × 0.10)
= 32.0 + 33.2 + 11.2 + 8.5
= 85.0

💼 Business Context:
------------------
• Sector: Communication Services
• Risk Level: LOW

📊 Technical Details:
------------------
• Signal: Buy
• Signal Age: 3 days
• Price at Signal: $142.30
• Risk:Reward Ratio: 2.80
• Patterns: HAMMER,DOJI

🎯 Investment Thesis:
------------------
🟢 STRONG INVESTMENT CANDIDATE
• Excellent scores across all dimensions
• High probability of success
• Consider for immediate action
"""
    
    print(example1)
    print("=" * 60)
    print()
    
    # דוגמה 2: מניה עם ציון בינוני
    print("🔍 דוגמה 2: לחצת על שורה של TSLA")
    print("-" * 50)
    
    example2 = """
📊 TSLA - Enhanced Score Breakdown
========================================

🎯 Final Enhanced Score: 64.0/100
🏆 Grade: B-
📋 Recommendation: HOLD

📈 Component Breakdown:
-------------------------
• Technical Analysis (40%): 80.0
• Fundamental Analysis (35%): 45.0
• Sector Performance (15%): 50
• Business Quality (10%): 87.0

🔢 Weighted Calculation:
(80.0 × 0.40) + (45.0 × 0.35) + (50 × 0.15) + (87.0 × 0.10)
= 32.0 + 15.8 + 7.5 + 8.7
= 64.0

💼 Business Context:
------------------
• Sector: Consumer Cyclical
• Risk Level: MEDIUM

📊 Technical Details:
------------------
• Signal: Hold
• Signal Age: 8 days
• Price at Signal: $251.20
• Risk:Reward Ratio: 2.10
• Patterns: ENGULFING

🎯 Investment Thesis:
------------------
🟠 MODERATE OPPORTUNITY
• Mixed signals - some strengths, some concerns
• Requires additional analysis
• Proceed with caution
"""
    
    print(example2)
    print("=" * 60)
    print()
    
    # דוגמה 3: מניה עם ציון נמוך
    print("🔍 דוגמה 3: לחצת על שורה של מניה עם ציון נמוך")
    print("-" * 50)
    
    example3 = """
📊 AMD - Enhanced Score Breakdown
========================================

🎯 Final Enhanced Score: 42.0/100
🏆 Grade: D+
📋 Recommendation: AVOID

📈 Component Breakdown:
-------------------------
• Technical Analysis (40%): 55.0
• Fundamental Analysis (35%): 30.0
• Sector Performance (15%): 35
• Business Quality (10%): 61.0

🔢 Weighted Calculation:
(55.0 × 0.40) + (30.0 × 0.35) + (35 × 0.15) + (61.0 × 0.10)
= 22.0 + 10.5 + 5.2 + 6.1
= 42.0

💼 Business Context:
------------------
• Sector: Technology
• Risk Level: HIGH

📊 Technical Details:
------------------
• Signal: Sell
• Signal Age: 12 days
• Price at Signal: $142.85
• Risk:Reward Ratio: 1.70
• Patterns: None

🎯 Investment Thesis:
------------------
🔴 HIGH RISK / LOW CONFIDENCE
• Multiple concerns across analysis dimensions
• Low probability of success
• Consider avoiding or wait for better setup
"""
    
    print(example3)
    print("=" * 60)
    print()
    
    print("💡 איך זה עובד:")
    print("1. בטבלה אתה רואה שורות של מניות עם ציונים")
    print("2. לוחץ על שורה כלשהי")  
    print("3. בצד ימין מופיע החלון עם הפירוט המלא")
    print("4. החלון מראה בדיוק מאיפה בא הציון ומה זה אומר")
    print()
    
    print("🎯 היתרונות:")
    print("✅ רואה בדיוק איך מחושב הציון המשוכלל")
    print("✅ מבין איזה רכיבים חזקים ואיזה חלשים") 
    print("✅ מקבל המלצה ברורה מה לעשות")
    print("✅ יודע מה הסיכון ובאיזה סקטור זה")
    print("✅ רואה פרטים טכניים חשובים")

def show_classic_mode_example():
    """דוגמה של המצב הקלאסיק (ישן)"""
    
    print("\n" + "="*60)
    print("📊 לשם השוואה - המצב הקלאסיק (Classic Mode)")
    print("=" * 60)
    
    classic_example = """
Symbol: GOOGL  Strategy: Donchian Breakout
Stored Score: 0.756
Recalc: 0.7234 (linear)
ML Prob=0.68  RR_norm=0.93  Fresh=0.70  Patt=0.67 (cnt=2)
Weights raw prob=40 rr=30 fresh=20 patt=10
Contributions:
prob 0.680 * 0.40 = 0.272
rr 0.933 * 0.30 = 0.280
fresh 0.700 * 0.20 = 0.140
pattern 0.667 * 0.10 = 0.067
Patterns: HAMMER,DOJI
"""
    
    print(classic_example)
    print("❌ זה המצב הישן - מסובך ולא ברור")
    print("✅ המצב החדש (Enhanced) הרבה יותר ברור ושימושי!")

if __name__ == "__main__":
    show_enhanced_score_detail_example()
    show_classic_mode_example()
    
    print(f"\n🎯 סיכום:")
    print("החלון בצד ימין נותן לך הבנה מלאה של למה כל מניה קיבלה")
    print("את הציון שלה, ועוזר לך להחליט האם לקנות/למכור/לחכות")
    print("במקום מספרים מבלבלים - אתה מקבל הסבר ברור והמלצה!")