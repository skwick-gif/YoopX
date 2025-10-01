"""
🎯 Demo: Rigorous Premium Scanner Test
====================================
בדיקה מהירה של הסורק הנוקשה והמסננים החדים
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic.rigorous_scanner import RigorousPremiumScanner, RigorousFilterCriteria
from logic.enhanced_scanner import EnhancedScanResult
import datetime
import json

def create_test_stocks():
    """יצירת מניות בדיקה עם רמות איכות שונות"""
    
    test_stocks = []
    
    # 🏆 Elite Stock - צריך לעבור את כל המסננים
    elite_stock = EnhancedScanResult(
        symbol="ELITE_STOCK",
        timestamp=datetime.datetime.now().isoformat(),
        technical_signal="Buy",
        technical_age=2,
        technical_score=90.0,
        fundamental_score=85.0,
        sector_score=80.0,
        business_quality_score=90.0,
        composite_score=87.5,
        grade="A+",
        risk_level="LOW",
        confidence_level="VERY_HIGH",
        pe_ratio=22.0,
        roe=0.28,
        debt_to_equity=20.0,
        financial_strength="EXCELLENT",
        size_category="MEGA_CAP",
        sector="Technology",
        patterns=["HAMMER", "ENGULFING"],
        rr_ratio=4.2,
        employee_count=50000,
        recommendation="STRONG BUY"
    )
    
    # 🟢 Premium Stock - יעבור Conservative ו-Growth
    premium_stock = EnhancedScanResult(
        symbol="PREMIUM_STOCK", 
        timestamp=datetime.datetime.now().isoformat(),
        technical_signal="Buy",
        technical_age=5,
        technical_score=78.0,
        fundamental_score=75.0,
        sector_score=70.0,
        business_quality_score=80.0,
        composite_score=76.0,
        grade="A-",
        risk_level="LOW",
        confidence_level="HIGH",
        pe_ratio=18.0,
        roe=0.18,
        debt_to_equity=35.0,
        financial_strength="STRONG",
        size_category="LARGE_CAP",
        sector="Healthcare",
        patterns=["DOJI"],
        rr_ratio=2.8,
        employee_count=15000,
        recommendation="BUY"
    )
    
    # 🟡 Good Stock - יעבור רק Conservative
    good_stock = EnhancedScanResult(
        symbol="GOOD_STOCK",
        timestamp=datetime.datetime.now().isoformat(),
        technical_signal="Buy",
        technical_age=6,
        technical_score=72.0,
        fundamental_score=68.0,
        sector_score=65.0,
        business_quality_score=70.0,
        composite_score=69.0,
        grade="B+",
        risk_level="LOW",
        confidence_level="MEDIUM",
        pe_ratio=19.0,
        roe=0.16,
        debt_to_equity=38.0,
        financial_strength="STRONG",
        size_category="LARGE_CAP",
        sector="Financials",
        patterns=["HAMMER"],
        rr_ratio=2.2,
        employee_count=8000,
        recommendation="HOLD"
    )
    
    # 🔴 Average Stock - לא יעבור שום מסנן נוקשה
    average_stock = EnhancedScanResult(
        symbol="AVERAGE_STOCK",
        timestamp=datetime.datetime.now().isoformat(),
        technical_signal="Hold",
        technical_age=15,
        technical_score=55.0,
        fundamental_score=50.0,
        sector_score=45.0,
        business_quality_score=52.0,
        composite_score=51.0,
        grade="C",
        risk_level="MEDIUM",
        confidence_level="LOW",
        pe_ratio=35.0,
        roe=0.08,
        debt_to_equity=70.0,
        financial_strength="AVERAGE",
        size_category="MID_CAP",
        sector="Materials",
        patterns=[],
        rr_ratio=1.5,
        employee_count=2000,
        recommendation="NEUTRAL"
    )
    
    # 🚫 Poor Stock - בעיות בכל המדדים
    poor_stock = EnhancedScanResult(
        symbol="POOR_STOCK",
        timestamp=datetime.datetime.now().isoformat(),
        technical_signal="Sell",
        technical_age=25,
        technical_score=25.0,
        fundamental_score=30.0,
        sector_score=35.0,
        business_quality_score=28.0,
        composite_score=29.0,
        grade="F",
        risk_level="HIGH",
        confidence_level="LOW",
        pe_ratio=55.0,
        roe=0.02,
        debt_to_equity=120.0,
        financial_strength="POOR",
        size_category="SMALL_CAP",
        sector="Energy",
        patterns=[],
        rr_ratio=0.8,
        employee_count=500,
        recommendation="AVOID"
    )
    
    return [elite_stock, premium_stock, good_stock, average_stock, poor_stock]

def test_rigorous_filtering():
    """בדיקת המסננים הנוקשים"""
    
    print("🎯 Testing Rigorous Premium Scanner")
    print("=" * 50)
    
    # יצירת מניות בדיקה
    test_stocks = create_test_stocks()
    
    print(f"\n📊 Input: {len(test_stocks)} test stocks:")
    for stock in test_stocks:
        print(f"  {stock.symbol:15} | {stock.composite_score:5.1f} | {stock.grade:2} | {stock.risk_level:6} | {stock.sector}")
    
    # יצירת סורק נוקשה
    scanner = RigorousPremiumScanner()
    
    # בדיקת כל פרופיל
    for profile in ["conservative", "growth", "elite"]:
        print(f"\n🔍 Testing {profile.upper()} profile:")
        print("-" * 40)
        
        filtered = scanner.apply_rigorous_filters(test_stocks, profile)
        
        print(f"Results: {len(filtered)}/{len(test_stocks)} stocks passed")
        
        for stock in filtered:
            print(f"  ✅ {stock.symbol:15} | Score: {stock.composite_score:5.1f} | Grade: {stock.grade:2} | {stock.recommendation}")
        
        if not filtered:
            print(f"  ❌ No stocks passed {profile} filters")

def test_criteria_details():
    """הצגת פרטי הקריטריונים"""
    
    print("\n\n📋 Rigorous Filtering Criteria Details")
    print("=" * 50)
    
    scanner = RigorousPremiumScanner()
    
    profiles = {
        'conservative': scanner.conservative_criteria,
        'growth': scanner.growth_criteria, 
        'elite': scanner.elite_criteria
    }
    
    for profile_name, criteria in profiles.items():
        print(f"\n🎯 {profile_name.upper()} Profile:")
        print("-" * 30)
        print(f"  Technical Score: >={criteria.min_technical_score}")
        print(f"  Signal Age: <={criteria.max_signal_age} days")
        print(f"  R:R Ratio: >={criteria.min_rr_ratio}")
        print(f"  Required Patterns: >={criteria.required_patterns}")
        print(f"  Fundamental Score: >={criteria.min_fundamental_score}")
        print(f"  Max P/E: <={criteria.max_pe_ratio}")
        print(f"  Min ROE: >={criteria.min_roe*100}%")
        print(f"  Max Debt/Equity: <={criteria.max_debt_to_equity}%")
        print(f"  Composite Score: >={criteria.min_composite_score}")
        print(f"  Required Grades: {criteria.required_grades}")
        print(f"  Max Risk: {criteria.max_risk_level}")
        print(f"  Min Company Size: {criteria.min_size_category}")
        print(f"  Min Employees: {criteria.min_employee_count:,}")
        print(f"  Preferred Sectors: {criteria.preferred_sectors}")
        print(f"  Blacklist Sectors: {criteria.blacklist_sectors}")

def create_demo_config():
    """יצירת קובץ הדגמה עם ההגדרות"""
    
    config = {
        "rigorous_scan_demo": {
            "description": "הגדרות לסריקה נוקשה - רק מניות באיכות יוצאת מן הכלל",
            "profiles": {
                "conservative": {
                    "target_audience": "משקיעים שמרניים",
                    "expected_pass_rate": "5-10%",
                    "focus": "יציבות ואמינות"
                },
                "growth": {
                    "target_audience": "משקיעי צמיחה",
                    "expected_pass_rate": "3-7%", 
                    "focus": "פוטנציאל צמיחה גבוה"
                },
                "elite": {
                    "target_audience": "משקיעי עלית",
                    "expected_pass_rate": "1-3%",
                    "focus": "רק החברות המובילות בעולם"
                }
            },
            "quality_gates": {
                "all_scores_positive": "כל הציונים חייבים להיות חיוביים",
                "consistent_excellence": "איכות עקבית בכל המימדים",
                "no_speculation": "אין מניות ספקולטיביות",
                "established_companies": "רק חברות מבוססות"
            }
        }
    }
    
    with open('rigorous_scan_demo_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Demo config saved to: rigorous_scan_demo_config.json")

if __name__ == "__main__":
    test_rigorous_filtering()
    test_criteria_details()
    create_demo_config()
    
    print(f"\n\n🎉 Demo completed!")
    print("Key insights:")
    print("• Elite profile: Only 1 stock (ELITE_STOCK) passes - extremely selective")
    print("• Growth profile: 2-3 stocks pass - high quality growth focus")
    print("• Conservative profile: 3-4 stocks pass - stable, reliable companies")
    print("• Regular stocks and poor performers are filtered out completely")
    print("\n💡 This ensures only premium quality investments reach the user!")